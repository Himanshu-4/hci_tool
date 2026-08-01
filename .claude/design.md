# HCI Tool — Design (POC: BR/EDR + LE connection, advertising, scanning)

> Status: proposal, pending your amendments.
> Companion doc: [plan.md](./plan.md) — the phased work breakdown.
> Goal of the POC: from the GUI (and from a headless script), reliably run four flows
> end-to-end against a real controller: **LE advertise**, **LE scan**, **LE connect**,
> **BR/EDR inquiry + connect**.

---

## 1. Where the code actually stands today

I ran the app and exercised the layers. Summary of verified state, not assumptions.

### Works

- App launches. `main.py` → `syscfg.yml` YAML parser → `ui/main/app.py` MDI main window →
  **Tools ▸ HCI** → `ConnectionDialog` → `Transport` (pyserial UART) → `HciMainUI` command tree.
- Opcode tables in `hci/cmd/cmd_opcodes.py` are **complete and correct** through modern LE
  (ext adv, ext scan, periodic adv, CTE, ISO). This is the most valuable asset in the repo.
- Command packet build path works for implemented commands: 21 commands registered,
  22 command UI dialogs registered, `to_bytes()` produces correct H4 framing.
- Support infrastructure (YAML config w/ symbol expansion, async logger, file handler,
  hierarchical shutdown handler) is substantial and functional.

### Broken — these are what block the POC

Verified by execution, with reproductions:

| # | Defect | Evidence | Impact |
|---|---|---|---|
| **B1** | **No RX pump exists.** `UARTTransport.connect()` never starts a reader — `transports/UART/uart.py:212` is `# self._start_read_thread()`. `_read_worker()` fills a buffer nothing drains. The only other caller was commented out at `ui/exts/hci_window.py:136`. | `TransportEvent.READ` is never fired. `evt_factory.py:65` subscribes to it and never runs. | **No event ever reaches the app.** Nothing can complete. |
| **B2** | **23 of 29 registered event classes are abstract and cannot be instantiated.** `HciPacket.__str__` is `@abstractmethod`; event subclasses never implement it. | `TypeError: Can't instantiate abstract class InquiryCompleteEvent without an implementation for abstract method '__str__'` | The event layer is non-functional even if bytes arrived. |
| **B3** | LE meta events define `from_bytes_sub_event()`, but the dispatcher (`hci/evt/__init__.py:138`) calls `from_bytes()`. | All 4 LE events abstract on `from_bytes`. | LE Advertising Report / LE Connection Complete unparseable — kills scan *and* LE connect. |
| **B4** | Generic `CommandCompleteEvent` registration is **commented out** (`hci/evt/base_events/base_events.py:122`). Only 6 per-opcode Command Completes exist. | `hci_evt_parse_from_bytes(<Cmd Complete Read_BD_ADDR>)` → `ValueError: Unknown event with code 0x0E`. | Almost every command's own completion raises. |
| **B5** | `CommandStatusEvent` missing `_validate_params`. | `TypeError: Can't instantiate abstract class CommandStatusEvent`. | Command Status (used by *every* connect command) unparseable. |
| **B6** | `Disconnection_Complete` (0x05) not implemented/registered. | `ValueError: Unknown event with code 0x05`. | Disconnect never observed. |
| **B7** | `evt_from_bytes` rejects any event code not in `HciEventCode` — including vendor-specific `0xFF`; and does a blind `struct.unpack("<BBBB", data[:4])` that fails on 3-byte events. | `ValueError: Invalid event code: 255`. | One vendor event from the controller kills the RX path. |
| **B8** | `hci_create_cmd_packet(opcode, params=...)` **silently drops the parameters.** `to_bytes()` reads `getattr(self.__class__, 'PARAMS')` but `__init__` sets the *instance* attribute. | `hci_create_cmd_packet(0x0C1A, params=b'\x03').to_bytes()` → `011a0c00`, should be `011a0c0103`. | The "no dedicated class → generic packet" fallback in `cmd_factory.deafualt_base_cmd_executor` emits malformed commands. |
| **B9** | `HCICmdBaseUI.on_ok_button_clicked` calls `self.__class__.get_cmd_instance()` — unbound, no `self`. `byte_data` is always `b''` when emitted. | `ui/hci_ui/hci_base_ui.py:316,326` | OK button path is fragile/dead depending on subclass. |
| **B10** | `Transport.is_connected()` calls `transport_instance.is_connected()`, but that is a `@property` → calling a `bool`. Same class/property mismatch on `get_config`, and `Transport.get_stats` calls a non-existent `self.get_status()`. | `transports/transport.py:191,197,212` | Runtime `TypeError` on status paths. |
| **B11** | **Commands required by the POC do not exist.** `hci/cmd/le_cmds/{advertisement,scanning,connection,security,misc}.py` are **0-byte files**. | `wc -c` | No LE_Set_Advertise_Enable (0x200A), LE_Set_Random_Address, LE_Set_Scan_Response_Data, LE_Create_Connection (0x200D), LE_Create_Connection_Cancel. Also no HCI_Reset (0x0C03) or Write_Scan_Enable (0x0C1A) command class. |
| **B12** | **No host/session layer.** Nothing owns connection handles, adv/scan state, the `Num_HCI_Command_Packets` credit, or command↔completion correlation. | — | Multi-step flows ("connect to X") are impossible to express. |

### Also noted (not POC-blocking)

- Three parallel unused transport implementations: `uart_async.py` (556 L), `uart_temp.py` (672 L),
  and `AsyncUARTPort`/`AsyncUARTManager` inside `uart.py` (lines 468–1045). Plus a `.temp/` mirror tree.
- No `requirements.txt` / no in-repo venv; deps live in `../my_env` (PyQt5 5.15.11, pyserial 3.5, PyYAML 6.0.2).
- No test suite. `test/` holds scratch scripts.
- `_initialize_modules()` in `hci/cmd/__init__.py:73` filters on `module_name.startswith('hci.cmd.')`,
  but `pkgutil.walk_packages` yields bare names — the dynamic import is a no-op. Registration
  happens only via the explicit `from . import ...` lines below it. Harmless but misleading.

**Bottom line:** the packet *definitions* are in reasonable shape; the *plumbing* between
serial bytes and the UI has never been connected, and the event layer has never been executed.

---

## 2. Target architecture

Five layers, one new. The new `hci/session/` layer is the missing piece.

```
┌──────────────────────────────────────────────────────────────┐
│  ui/  — Qt widgets                                            │
│    hci_main_ui · cmd_factory · evt_factory · procedure panel   │
└───────────────▲──────────────────────────┬───────────────────┘
                │ Qt signals (main thread)  │ high-level calls
┌───────────────┴──────────────────────────▼───────────────────┐
│  hci/session/  ★ NEW                                          │
│    HciSession      — cmd queue, credits, cmd↔evt correlation   │
│    ConnectionTable — handles, roles, BR/EDR vs LE              │
│    Procedures      — advertise / scan / connect / inquiry      │
└───────────────▲──────────────────────────┬───────────────────┘
                │ parsed packets            │ .to_bytes()
┌───────────────┴──────────────────────────▼───────────────────┐
│  hci/cmd/ · hci/evt/ · hci/acl/  — packet codecs (exists)      │
└───────────────▲──────────────────────────┬───────────────────┘
                │ framed H4 packets         │ raw bytes
┌───────────────┴──────────────────────────▼───────────────────┐
│  transports/  — H4Framer ★NEW + RX pump ★NEW + UARTTransport   │
└───────────────▲──────────────────────────┬───────────────────┘
                │                           │
         ┌──────┴──────┐            ┌───────▼────────┐
         │ real UART   │            │ VirtualCtrl ★  │  (test double)
         └─────────────┘            └────────────────┘
```

### 2.1 Threading model

The app is Qt-driven, and the existing code is synchronous. **The POC stays threaded, not
asyncio.** Rationale: the Qt event loop is already the application loop; bridging asyncio into
it (qasync or a second loop in a thread) is a real project on its own, and the three existing
half-finished async transports are evidence of that cost. Threads + Qt queued signals give a
correct, debuggable POC now, and `HciSession` is written so an asyncio transport can be
swapped underneath later without touching the UI.

```
serial RX thread ──► H4Framer ──► complete packet bytes
                                        │
                                        ▼
                        QueuedConnection signal (thread-safe)
                                        │
                                        ▼
                     Qt main thread: HciSession.on_packet()
                          ├─ resolve pending command → callback/future
                          ├─ update ConnectionTable / adv / scan state
                          └─ emit typed Qt signals to UI
```

All parsing and all state mutation happen on the Qt main thread. The RX thread does exactly
one job: read bytes, frame them, emit. No locks in the session layer.

### 2.2 H4 framing (`transports/h4_framer.py`, new)

A pure, byte-oriented state machine — **no I/O, no Qt** — so it is trivially unit-testable.
Feed it arbitrary chunks; it yields complete packets. This replaces the current
"read exactly one event, discard everything else" logic in `uart.py:255`.

| Type | Header after type byte | Length field |
|---|---|---|
| `0x01` CMD | opcode(2) + len(1) | 1 byte |
| `0x02` ACL | handle+flags(2) + len(2) | 2 bytes LE |
| `0x03` SCO | handle+flags(2) + len(1) | 1 byte |
| `0x04` EVT | code(1) + len(1) | 1 byte |
| `0x05` ISO | handle+flags(2) + len(2) | 2 bytes LE (12-bit) |

Must survive: partial reads mid-header, several packets in one read, a resync on an
unknown type byte (log + drop to next plausible boundary rather than raising).

### 2.3 `HciSession` — the host layer

```python
class HciSession(QObject):
    # --- outbound
    def send(self, cmd, *, on_complete=None, timeout=2.0) -> CmdToken
    def send_and_wait(self, cmd, timeout=2.0) -> HciEvtBasePacket   # headless/script use

    # --- inbound signals (Qt, main thread)
    packet_received  = pyqtSignal(object)   # every parsed packet, for the log window
    event_received   = pyqtSignal(object)
    adv_report       = pyqtSignal(object)   # LE Advertising Report (+ ext)
    inquiry_result   = pyqtSignal(object)   # BR/EDR Inquiry Result (+ RSSI/extended)
    connection_up    = pyqtSignal(object)   # ConnectionInfo
    connection_down  = pyqtSignal(int, int) # handle, reason
    state_changed    = pyqtSignal(str)
```

Responsibilities, in order of importance:

1. **Command flow control.** Track `Num_HCI_Command_Packets` from Command Complete /
   Command Status. Start at 1. Never have more outstanding commands than credits — this is
   the single most common cause of controllers wedging, and the current code has no notion of it.
2. **Correlation.** Match Command Complete / Command Status by opcode to the pending command;
   resolve its callback. Time out with a clear error rather than hanging.
3. **State.** `ConnectionTable` (handle → `ConnectionInfo{handle, bd_addr, addr_type, transport:
   BR_EDR|LE, role, encrypted}`), plus adv/scan/inquiry enabled flags. Updated from
   Connection Complete / LE Connection Complete / Disconnection Complete.
4. **Fan-out.** Emit typed signals so the UI never parses bytes.

`CmdToken` carries the opcode, a deadline, and the callback — deliberately not a `Future`,
so the same object works in both the Qt-signal and the blocking-script styles.

### 2.4 Procedures — the four POC flows

Each is a small explicit state machine in `hci/session/procedures/`, driven by session
signals. They are the thing that makes the tool *do* something rather than just send bytes.
Every step is logged, every failure surfaces the HCI status code by name.

**Init (run once on connect, all flows depend on it)**
```
HCI_Reset
  → Read_Local_Version_Information
  → Read_BD_ADDR
  → Set_Event_Mask (enable all classic events incl. 0x05, 0x0E, 0x0F)
  → LE_Set_Event_Mask
  → LE_Read_Buffer_Size
  → Read_Buffer_Size
```

**LE advertise**
```
LE_Set_Random_Address (if random addr chosen)
  → LE_Set_Advertising_Parameters (type, interval, own/peer addr, channel map, filter policy)
  → LE_Set_Advertising_Data (built from a small AD-structure helper: flags, name, UUIDs)
  → LE_Set_Scan_Response_Data (optional)
  → LE_Set_Advertise_Enable(0x01)
[connectable adv] ⇒ await LE Connection Complete → connection_up
```

**LE scan**
```
LE_Set_Scan_Parameters (active/passive, interval, window, filter policy)
  → LE_Set_Scan_Enable(enable=1, filter_duplicates)
  ⇒ stream of LE Advertising Report → adv_report → device table
     (AD payload decoded: flags, complete/short local name, tx power, service UUIDs, mfr data)
  → LE_Set_Scan_Enable(0)
```

**LE connect**
```
[scan must be off]
LE_Create_Connection(peer_addr, peer_addr_type, own_addr_type, scan itv/win,
                     conn itv min/max, latency, supervision timeout)
  ⇒ Command Status (0x00 = accepted; anything else = fail fast)
  ⇒ LE Connection Complete (0x3E/0x01) or Enhanced (0x3E/0x0A)
       success → ConnectionTable.add() → connection_up
       timeout → LE_Create_Connection_Cancel
  → HCI_Disconnect(handle, 0x13) ⇒ Disconnection Complete → connection_down
```

**BR/EDR inquiry + connect**
```
Write_Scan_Enable(0x03)            # inquiry + page scan, so we are discoverable too
  → Inquiry(LAP=0x9E8B33, length, num_responses)
  ⇒ Inquiry Result (0x02) / with RSSI (0x22) / Extended (0x2F) → inquiry_result
  ⇒ Inquiry Complete (0x01)
  → [optional] Remote_Name_Request
  → Create_Connection(bd_addr, packet_type=0xCC18, PSRM, clock_offset, allow_role_switch)
  ⇒ Command Status ⇒ Connection Complete (0x03) → connection_up
  → HCI_Disconnect ⇒ Disconnection Complete → connection_down
```

> **Scope note:** SSP pairing (IO Capability Request/Response, User Confirmation, Link Key
> Notification) is *not* in the POC. It is only needed once you go past ACL link
> establishment. The event classes are cheap to add later; see plan.md Phase 6.

### 2.5 Virtual controller (`transports/virtual/`)

A `TransportInterface` implementation that answers commands with plausible events:
Command Complete for configuration commands, synthetic LE Advertising Reports on scan enable,
LE Connection Complete on create-connection, Inquiry Results + Inquiry Complete on inquiry.

This is not gold-plating — it is what lets the four flows be tested in CI and lets you
develop the UI without a dongle plugged in. It also pins down the RX/framing/session
contract precisely.

---

## 3. Fix strategy for the event layer (B2–B7)

The 23 abstract classes share one root cause. Rather than editing 23 classes, fix the base:

```python
class HciEvtBasePacket(HciEventPacket):
    def __str__(self):                      # concrete default: name + params
        ...                                 # subclasses may still override
    def _validate_params(self): pass        # concrete no-op default
    def _serialize_params(self): return b'' # concrete default

    @classmethod
    def from_bytes(cls, data, sub_event_code=None):
        # default dispatch: if the subclass defines from_bytes_sub_event, call it
```

That single change makes 22 of 23 classes instantiable. Then:

- Register the generic `CommandCompleteEvent` as the **fallback** for opcode 0x0E when no
  per-opcode class exists (uncomment `base_events.py:122` and make lookup fall back).
- Add `_validate_params` to `CommandStatusEvent`.
- Add `DisconnectionCompleteEvent` (0x05).
- Make `evt_from_bytes` **total**: never raise on unknown/vendor/short input. Return a
  `GenericEventPacket` carrying `(code, subcode, raw_params)` and log it. A parser that
  raises on the RX thread takes down the link; an unknown event must degrade to a hex dump.

**Design rule going forward:** *the receive path never raises.* Malformed input produces a
generic packet and a warning, never an exception.

---

## 4. Testing strategy

No test suite exists today, which is why 23 broken classes went unnoticed. Minimum for the POC:

| Layer | Test | Needs hardware |
|---|---|---|
| `H4Framer` | split/merged/garbage byte streams | no |
| Command codecs | every implemented command → expected hex (spec vectors) | no |
| Event codecs | **every registered event class round-trips and instantiates** | no |
| `evt_from_bytes` | unknown code, vendor 0xFF, truncated → generic, no raise | no |
| `HciSession` | credit accounting, correlation, timeout, connection table | no (virtual ctrl) |
| Procedures | all four flows against the virtual controller | no |
| Smoke | GUI launches offscreen, opens HCI window, sends Reset | no |
| Bring-up | four flows against a real dongle | **yes** |

`pytest`, run headless via `QT_QPA_PLATFORM=offscreen`.

---

## 5. Non-goals for this POC

Called out so the plan does not quietly grow:

- SSP / pairing / encryption, LE privacy, resolving list.
- ACL data transfer, L2CAP, throughput/A2DP/HID/SCO/ISO tests (`ui/exts/*` stubs stay stubs).
- Extended advertising / extended scanning / periodic sync (opcodes exist; legacy first).
- USB and SDIO transports (stubs stay stubs).
- asyncio rework of the transport layer; deleting `uart_async.py` / `uart_temp.py` / `.temp/`.
- Rewriting the logger / YAML / shutdown infrastructure.

---

## 6. Open decisions — please amend

1. **Threaded vs asyncio.** I propose threads + Qt signals for the POC (§2.1). If you want the
   asyncio path now, that is Phase 0 work and shifts the schedule materially.
2. **Virtual controller.** I propose building it (§2.5) so the flows are testable without
   hardware. Drop it if you always have a dongle attached and want to move faster.
3. **Target controller.** Which dongle/chip and which UART settings (baud, flow control,
   vendor init sequence)? Some parts need `HCI_Reset` + a vendor command before they respond.
   This affects Phase 5 only, but I need it to verify anything for real.
4. **Legacy vs extended LE.** POC uses legacy adv/scan (0x2006/0x2008/0x200A/0x200B/0x200C).
   Confirm your controller supports legacy — some newer ones are extended-only.
5. **UI shape for procedures.** New "Procedures" panel with four buttons + a device table,
   vs. driving the existing per-command dialogs manually. I propose the panel — the
   per-command dialogs stay for expert use.
6. **Where deps live.** Add `requirements.txt` + a project-local `.venv`, or keep using
   `../my_env`? I propose adding `requirements.txt` either way.


