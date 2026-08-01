# HCI Tool — POC Implementation Plan

> Companion doc: [design.md](./design.md) — architecture and the verified defect list (B1–B12).
> Status: proposal, pending your amendments. Nothing has been implemented yet.
>
> **Definition of done for the POC:** from the GUI, against a real controller, I can
> (1) advertise, (2) scan and see devices, (3) make an LE connection and disconnect,
> (4) run a BR/EDR inquiry and make an ACL connection and disconnect — with every step
> and every event visible in the log.

---

## Phase ordering rationale

Phases 1–3 are strictly sequential: nothing can be tested until bytes flow (P1) and events
parse (P2). Phase 4 (commands) can be developed in parallel with P2 if you want to split work.
Phase 5 is where the POC becomes real. Phases 6+ are explicitly deferred.

| Phase | Theme | Blocking? |
|---|---|---|
| 0 | Environment + test harness | prerequisite |
| 1 | Make bytes flow (RX pump + H4 framing) | **blocks everything** |
| 2 | Make events parse (fix B2–B7) | **blocks everything** |
| 3 | `HciSession` host layer | blocks P5 |
| 4 | Missing commands for the four flows | blocks P5 |
| 5 | Procedures + UI + hardware bring-up | **the POC** |
| 6 | Deferred / follow-on | no |

---

## Phase 0 — Environment and test harness

Small, but it is what stops the next regression from going unnoticed for months.

- [ ] **0.1** Add `requirements.txt`: `pyserial>=3.5`, `PyQt5>=5.15`, `PyYAML>=6.0`, `pytest>=8`.
      *(Open decision #6: project-local `.venv` vs. keep `../my_env`.)*
- [ ] **0.2** Add `pytest.ini` / `pyproject.toml` test config; `tests/` package with the
      `sys._BASE_PATH` / `sys._APP_CONFIG_PATH` bootstrap that `main.py` does, as a fixture
      (`tests/conftest.py`). Without it, importing `utils.logger` raises `AppRuntimeError`.
- [ ] **0.3** Smoke test: launch `MainWindow` under `QT_QPA_PLATFORM=offscreen`, open the HCI
      window, assert no exception. *(Already verified this works manually — lock it in.)*
- [ ] **0.4** Registry test: assert **every** class in `hci.cmd._cmd_registry`,
      `hci.evt._evt_registry`, `_sub_evt_registry`, `_cmd_complete_evt_registery` has an empty
      `__abstractmethods__`. This one test catches B2/B3/B5 permanently.
      *Expect it to fail 23 times on first run — that is the point.*

**Exit:** `pytest` runs; 0.4 fails loudly with the 23 known-broken classes.

---

## Phase 1 — Make bytes flow  ⟵ *the single highest-value change*

Fixes **B1**. Today no received byte ever reaches the application.

- [ ] **1.1** New `transports/h4_framer.py` — pure byte state machine, no I/O, no Qt.
      `feed(chunk: bytes) -> list[bytes]` yielding complete H4 packets. Handles all 5 packet
      types (design.md §2.2), partial headers, coalesced packets, and resync on garbage.
- [ ] **1.2** Unit-test the framer: byte-at-a-time feed, 3 packets in one chunk, truncated
      tail, unknown type byte → resync not raise, 255-byte max event, 2-byte-length ACL.
- [ ] **1.3** Rewrite `UARTTransport` RX (`transports/UART/uart.py`):
      - `connect()` starts the reader thread (uncomment + fix line 212).
      - `_read_worker()` → blocking `read(1)` + `read(in_waiting)`, feed the framer, emit each
        complete packet via `TransportEvent.READ`. Remove the current `read()` implementation
        (lines 255–336) that reads one event and discards every other packet type.
      - Clean thread shutdown on `disconnect()` and on app exit (hook the existing
        `utils/shutdown_handler`).
- [ ] **1.4** Fix **B10**: `TransportInterface.is_connected` / `get_config` are properties but
      `Transport` calls them as methods (`transports/transport.py:191,197`); `get_stats` calls a
      non-existent `self.get_status()` (line 212). Pick one convention — I propose methods on
      `Transport`, properties on the interface, with `Transport` adapting — and fix
      `ui/hci_ui/hci_main_ui.py:510` which currently uses the property form.
- [ ] **1.5** Marshal RX to the Qt thread: a `QObject` shim emitting a `pyqtSignal(bytes)` with
      `Qt.QueuedConnection`. Parsing must not happen on the serial thread.
- [ ] **1.6** New `transports/virtual/` mock controller implementing `TransportInterface`
      (design.md §2.5). *(Open decision #2 — drop this and P1/P2/P3 lose their hardware-free tests.)*

**Exit:** with the virtual controller (or a real dongle), sending `HCI_Reset` produces a
logged, framed Command Complete packet in the app. **First time the tool has ever received anything.**

---

## Phase 2 — Make events parse

Fixes **B2–B7**. See design.md §3 for the root-cause analysis — one base-class change
un-breaks 22 of 23 classes.

- [ ] **2.1** `hci/evt/evt_base_packet.py`: give `HciEvtBasePacket` concrete defaults for
      `__str__`, `_validate_params`, `_serialize_params`, and a `from_bytes` that dispatches to
      `from_bytes_sub_event` when present. Fixes **B2** and **B3** wholesale.
- [ ] **2.2** `CommandStatusEvent`: add `_validate_params` (**B5**).
- [ ] **2.3** Register generic `CommandCompleteEvent` as the 0x0E **fallback** when no
      per-opcode class is registered — `hci/evt/base_events/base_events.py:122` (**B4**), and
      make `get_event_class` fall back rather than return `None`.
- [ ] **2.4** Add `DisconnectionCompleteEvent` (0x05) (**B6**).
- [ ] **2.5** Make `evt_from_bytes` total (**B7**): no `struct.unpack` on `data[:4]` before
      length is known; accept unknown and vendor (0xFF) codes; return a `GenericEventPacket`
      with the raw payload instead of raising. **Design rule: the RX path never raises.**
- [ ] **2.6** Add the events the four flows need, if missing: Inquiry Result with RSSI (0x22),
      Extended Inquiry Result (0x2F), LE Enhanced Connection Complete (0x3E/0x0A),
      LE Data Length Change, LE PHY Update Complete, Encryption Change (0x08).
- [ ] **2.7** AD-structure decoder (`hci/evt/le/adv_data.py`): parse the adv payload into
      flags / short + complete local name / 16- and 128-bit service UUIDs / TX power /
      manufacturer data. Without this the scan list shows only MAC addresses.
- [ ] **2.8** Round-trip tests for every registered event class + the specific byte vectors
      from design.md §1 that currently raise. Test 0.4 now passes.

**Exit:** every registered event parses; unknown input degrades to a hex dump; test 0.4 green.

---

## Phase 3 — `HciSession` host layer

Fixes **B12**. New package `hci/session/`. See design.md §2.3.

- [ ] **3.1** `hci/session/session.py` — `HciSession(QObject)`: `send()`, `send_and_wait()`,
      the Qt signals listed in design.md §2.3.
- [ ] **3.2** **Command credit accounting**: honour `Num_HCI_Command_Packets` from Command
      Complete / Command Status; queue when credits are 0. *Not optional — the top cause of
      controllers wedging, and there is no notion of it in the code today.*
- [ ] **3.3** Command↔completion correlation by opcode, with per-command timeout producing a
      clear error rather than a hang.
- [ ] **3.4** `ConnectionTable` + `ConnectionInfo{handle, bd_addr, addr_type, transport, role,
      encrypted}`; updated from Connection Complete / LE Connection Complete /
      Disconnection Complete.
- [ ] **3.5** Adv / scan / inquiry state flags, so the UI can grey out illegal actions (e.g.
      `LE_Create_Connection` while scanning is enabled — a very common controller error).
- [ ] **3.6** Fix **B8**: `hci_create_cmd_packet` silently drops `params`
      (`hci/cmd/cmd_base_packet.py` — `to_bytes` reads the *class* attr, `__init__` sets the
      *instance* attr). Also give `_serialize_params` a concrete `return b''` default.
- [ ] **3.7** Tests against the virtual controller: credits, correlation, timeout, table updates.

**Exit:** `session.send_and_wait(Reset())` returns a parsed Command Complete; credits and the
connection table behave under the virtual controller.

---

## Phase 4 — Missing commands

Fixes **B11**. The five LE command files are 0-byte. Follow the existing pattern in
`hci/cmd/le_cmds/controller_config.py` (class + `_serialize_params` + `register_command`).

- [ ] **4.1** `controller_baseband_cmds.py`: **`Reset` (0x0C03)**, `Write_Scan_Enable` (0x0C1A),
      `Write_Class_Of_Device`, `Read_Buffer_Size`. *(`HCI_Reset` genuinely does not exist today.)*
- [ ] **4.2** `le_cmds/advertisement.py`: `LE_Set_Advertise_Enable` (0x200A),
      `LE_Set_Scan_Response_Data` (0x2009), `LE_Set_Random_Address` (0x2005),
      `LE_Read_Advertising_Channel_Tx_Power` (0x2007).
- [ ] **4.3** `le_cmds/scanning.py`: re-home / extend the existing `LeSetScanParameters` and
      `LeSetScanEnable` (currently in `controller_config.py`), adding filter-policy and
      filter-duplicates handling.
- [ ] **4.4** `le_cmds/connection.py`: `LE_Create_Connection` (0x200D),
      `LE_Create_Connection_Cancel` (0x200E), `LE_Connection_Update` (0x2013),
      `LE_Read_Remote_Features` (0x2016).
- [ ] **4.5** `le_cmds/misc.py`: `LE_Set_Event_Mask` (0x2001), `LE_Read_Buffer_Size` (0x2002),
      `LE_Read_Local_Supported_Features` (0x2003), `LE_Read_Supported_States` (0x201C).
- [ ] **4.6** Restore `Inquiry_Cancel` (0x0402) — removed in the current working tree;
      the inquiry flow needs a way to abort.
- [ ] **4.7** AD-structure **builder** (counterpart to 2.7) so advertising data can be composed
      from flags + name + UUIDs instead of hand-typed hex.
- [ ] **4.8** Command UIs (`ui/hci_ui/cmds/le/le_cmdui.py` etc.) for the new commands, and fix
      **B9**: `HCICmdBaseUI.on_ok_button_clicked` calls `self.__class__.get_cmd_instance()`
      unbound, and emits an always-empty `byte_data` (`ui/hci_ui/hci_base_ui.py:316,326`).
- [ ] **4.9** Byte-vector tests for every new command against the spec.

**Exit:** every command in the four flows exists, serializes correctly, and has a UI.

---

## Phase 5 — Procedures, UI, and hardware bring-up  ⟵ *the actual POC*

- [ ] **5.1** `hci/session/procedures/init.py` — controller init sequence (design.md §2.4),
      run automatically on transport connect. Everything else depends on it.
- [ ] **5.2** `procedures/le_advertise.py`
- [ ] **5.3** `procedures/le_scan.py` — with a discovered-device table (addr, addr type, RSSI,
      name, last-seen), deduplicated.
- [ ] **5.4** `procedures/le_connect.py` — including cancel-on-timeout and disconnect.
- [ ] **5.5** `procedures/bredr_inquiry_connect.py` — inquiry → optional remote name →
      create connection → disconnect.
- [ ] **5.6** New **Procedures panel** in the HCI window: four buttons, a live device table,
      a connection list with a Disconnect action, and a status line.
      *(Open decision #5.)* Existing per-command dialogs stay for expert use.
- [ ] **5.7** Wire `evt_factory` / the log window to `HciSession` signals so every TX and RX
      packet is logged decoded, with direction and timestamp.
- [ ] **5.8** Headless CLI (`tools/hci_cli.py`): `--port /dev/tty.X --baud 115200 scan|advertise
      |connect <addr>|inquiry`. Makes the flows scriptable and debuggable without the GUI —
      and much faster to iterate on during bring-up.
- [ ] **5.9** All four procedures tested against the virtual controller.
- [ ] **5.10** **Hardware bring-up.** Blocked on open decision #3 (which controller, baud, flow
      control, vendor init). Expect real-world fixes here: vendor init commands, baud-rate
      change sequences, controllers that are extended-adv-only (open decision #4).

**Exit — the POC is done when, on real hardware:**
1. Advertise → a phone sees the device.
2. Scan → nearby devices appear with names and RSSI.
3. LE connect → handle allocated, connection shown, clean disconnect.
4. BR/EDR inquiry → devices found; create connection → handle; clean disconnect.
5. Every step visible and decoded in the log.

---

## Phase 6 — Deferred (explicitly out of POC scope)

Listed so they are not forgotten and not silently pulled in.

- SSP / pairing: IO Capability Request/Response (0x31/0x32), User Confirmation Request (0x33),
  Simple Pairing Complete (0x36), Link Key Request/Notification (0x17/0x18), Encryption Change.
- ACL data path + flow control (`transports/flow_control.py` is a 6-line stub), L2CAP.
- Extended advertising / extended scanning / periodic sync (opcodes already exist).
- `ui/exts/` stubs: throughput, A2DP, HID, SCO, LE ISO, diagnostics, firmware download,
  config chip, util screen — all currently 0-byte.
- asyncio transport rework; retire the three dead implementations (`uart_async.py`,
  `uart_temp.py`, `AsyncUARTPort`/`AsyncUARTManager` in `uart.py:468-1045`) and the `.temp/` tree.
- USB and SDIO transports.

---

## Risks

| Risk | Mitigation |
|---|---|
| Controller needs vendor init before responding to standard HCI | Identify the part early (open decision #3); vendor init hook in the init procedure |
| Controller is extended-adv-only (no legacy 0x2006/0x200A) | Detect via `Read_Local_Supported_Commands`; extended path is Phase 6, would need pulling forward |
| PyQt5 + threads: touching widgets off the main thread | Framer emits via `QueuedConnection` only; no widget access off-thread (design.md §2.1) |
| Scope creep into the logger/YAML/shutdown infrastructure | Explicit non-goal (design.md §5) — it works, leave it |
| The 23 abstract event classes hide further bugs once instantiable | Phase 2 round-trip tests over *every* registered class, not a sample |

---

## Amend below — notes / changes from Himanshu

<!-- Your changes here. In particular the six open decisions in design.md §6:
     1. threaded vs asyncio   2. build the virtual controller?   3. which controller/dongle?
     4. legacy vs extended LE 5. procedures panel?                6. requirements.txt / venv
-->

1. **Threaded vs asyncio.** I propose threads + Qt signals for the POC (§2.1). If you want the
   asyncio path now, that is Phase 0 work and shifts the schedule materially.
   --> use whatever is faster and efficient. 

2. **Virtual controller.** I propose building it (§2.5) so the flows are testable without
   hardware. Drop it if you always have a dongle attached and want to move faster.
   --> don't write any Virtual event layer. i will test the APP on my own and let you know the bugs and chnages 

3. **Target controller.** Which dongle/chip and which UART settings (baud, flow control,
   vendor init sequence)? Some parts need `HCI_Reset` + a vendor command before they respond.
   This affects Phase 5 only, but I need it to verify anything for real.
   --> No init sequence is required just create a dummy sequence and will implement later if needed 

4. **Legacy vs extended LE.** POC uses legacy adv/scan (0x2006/0x2008/0x200A/0x200B/0x200C).
   Confirm your controller supports legacy — some newer ones are extended-only.
   ---> both should be implemented legacy and extended adv 

5. **UI shape for procedures.** New "Procedures" panel with four buttons + a device table,
   vs. driving the existing per-command dialogs manually. I propose the panel — the
   per-command dialogs stay for expert use.
   whatever you just, make sure the UI should be good and suitable for getting the user input 


6. **Where deps live.** Add `requirements.txt` + a project-local `.venv`, or keep using
   `../my_env`? I propose adding `requirements.txt` either way.
   --> create the requirements.txt and i use ../my_env only.
   
7. there are some event like in BREDR for connection,encryption  where accept cmd is required from user. so bind that events with directly the cmd or event UI that immediately proposed to user  for getting user input.