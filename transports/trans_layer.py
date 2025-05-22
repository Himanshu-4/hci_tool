"""
    tranport_layer.py
    This module provides functionality for transport layer operations.
    It includes:
    handling all the transport layer operations of different transport types (UART, SDIO).
    It includes:
    - Transport layer classes for different transport types (UART, SDIO).
    - Functions for sending and receiving data.
    - Error handling for file operations.
    - Logging for debugging and monitoring.
    - Utility functions for managing transport connections.
    - calling the handler functions of the transport layer.
    
    
    
"""

import asyncio
import threading

from transports.uart.uart_xfr import uart_transfer
from transports.SDIO.sdio import sdio_transfer
from transports.usb.usb_xfr import usb_transfer

from utils.logger import LoggerManager as logger
from utils.logger import LogLevel

from trans_lib import Transport


class TransportLayer:
    """
    A class to handle different transport types (UART, SDIO, USB) for data transfer.
    It provides a unified interface for sending and receiving data, as well as managing
    connection settings such as timeouts, baud rates, and SDIO speeds.
    """
    _instance = None
    _lock = threading.Lock()
    
    
    @classmethod
    def get_instance(cls, transport_type: str, **kwargs) -> 'TransportLayer':
        """
        Get the singleton instance of the TransportLayer class for the specified transport type.
        """
        return cls._instance
        
    def create_instance(cls, transport_type: str, **kwargs) -> 'TransportLayer':
        """
        crearte the singleton instance of the TransportLayer class for the specified transport type.
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = TransportLayer(transport_type, **kwargs)
            return cls._instance
        

    
    def __init__(self, transport_type: str, **kwargs):
        self.transport_type = transport_type
        self.transport = None

        if transport_type == 'UART':
            self.transport = uart_transfer.create_instance(**kwargs)
        elif transport_type == 'SDIO':
            self.transport = sdio_transfer.create_instance(**kwargs)
        elif transport_type == 'USB':
            self.transport = usb_transfer.create_instance(**kwargs)
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")
        
        
        # self._logger = logger.get_logger(__name__, level=LogLevel.DEBUG,
        #                                   to_console=True, to_file=True,
        #                                   description=True, prepend="Transport Layer: ",
        #                                   append="", log_file=None, enable=True)
        # self._logger.debug(f"Transport layer instance created for transport type: {transport_type}")
        # self._logger.debug(f"Transport layer instance created for transport type: {transport_type}")
        
        
        
        def __del__(self):
            """
            Destructor to clean up the transport layer instance.
            """
            if self.transport:
                self.transport.disconnect()
                self.transport = None
                TransportLayer._instance = None
                self._logger.debug(f"Transport layer instance destroyed for transport type: {self.transport_type}")
                
        
        def worker_thread(self):
            """
            Worker thread to handle transport layer operations.
            """
            while True:
                # Perform transport layer operations here
                pass
                # Check for exit condition
                if self._exit_event.is_set():
                    break
            self._logger.debug("Worker thread exiting.")
            self._exit_event.set()
            self._worker_thread.join()
            self._logger.debug("Worker thread joined.")
            self._logger.debug("Worker thread started.")
            
            
            
            
import asyncio
import serial_asyncio
from serial.serialutil import SerialException
import threading
import functools
import inspect # For checking if a callback is async

# --- Helper to run callbacks ---
async def _execute_callback(cb, *args):
    if cb:
        if inspect.iscoroutinefunction(cb):
            await cb(*args)
        elif callable(cb):
            # For synchronous callbacks, run in executor to avoid blocking asyncio loop
            # Note: This doesn't make it UI-thread-safe, UI marshalling is still user's job
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, functools.partial(cb, *args))
        else:
            print(f"Warning: Provided callback {cb} is not callable or awaitable.")

class AsyncSerialPort:
    def __init__(self, port_id, port_url, baudrate, loop,
                 start_byte=None, stop_byte=None, include_delimiters=False,
                 max_frame_length=4096, read_buffer_size=1024, **kwargs):
        self.port_id = port_id
        self.port_url = port_url
        self.baudrate = baudrate
        self.serial_kwargs = kwargs
        self._loop = loop
        
        self.start_byte = start_byte
        self.stop_byte = stop_byte
        self.include_delimiters = include_delimiters
        self.max_frame_length = max_frame_length
        self._internal_read_buffer = bytearray()

        self.read_queue = asyncio.Queue() # Stores complete frames
        self.write_queue = asyncio.Queue()
        
        self._reader = None
        self._writer = None
        self._read_task = None
        self._write_task = None
        self._connection_lock = asyncio.Lock() # Async lock for async operations
        self.is_connected = False
        self._read_buffer_size = read_buffer_size
        self._disconnect_requested = asyncio.Event()

        # Callbacks
        self.on_connect_cb = None
        self.on_disconnect_cb = None
        self.on_data_received_cb = None
        self.on_data_sent_cb = None

    def set_callbacks(self, on_connect=None, on_disconnect=None, on_data_received=None, on_data_sent=None):
        if on_connect: self.on_connect_cb = on_connect
        if on_disconnect: self.on_disconnect_cb = on_disconnect
        if on_data_received: self.on_data_received_cb = on_data_received
        if on_data_sent: self.on_data_sent_cb = on_data_sent
        print(f"[{self.port_id}] Callbacks updated.")

    async def _connect_async(self):
        async with self._connection_lock:
            if self.is_connected:
                msg = f"Already connected to {self.port_url}"
                print(f"[{self.port_id}] {msg}")
                await _execute_callback(self.on_connect_cb, self.port_id, True, msg)
                return True
            
            print(f"[{self.port_id}] Attempting to connect to {self.port_url} at {self.baudrate} baud...")
            try:
                self._reader, self._writer = await serial_asyncio.open_serial_connection(
                    url=self.port_url, baudrate=self.baudrate, **self.serial_kwargs
                )
                self.is_connected = True
                self._disconnect_requested.clear()
                self._internal_read_buffer.clear() # Clear buffer on new connection
                self._read_task = self._loop.create_task(self._read_loop())
                self._write_task = self._loop.create_task(self._write_loop())
                msg = f"Successfully connected to {self.port_url}"
                print(f"[{self.port_id}] {msg}")
                await _execute_callback(self.on_connect_cb, self.port_id, True, msg)
                return True
            except SerialException as e:
                msg = f"Failed to connect to {self.port_url}: {e}"
                print(f"[{self.port_id}] {msg}")
                self.is_connected = False
                await _execute_callback(self.on_connect_cb, self.port_id, False, msg)
                return False
            except Exception as e:
                msg = f"An unexpected error occurred during connection to {self.port_url}: {e}"
                print(f"[{self.port_id}] {msg}")
                self.is_connected = False
                await _execute_callback(self.on_connect_cb, self.port_id, False, msg)
                return False

    async def _disconnect_async(self, reason="User initiated"):
        async with self._connection_lock:
            if not self.is_connected and not (self._read_task or self._write_task):
                print(f"[{self.port_id}] {self.port_url} is already disconnected.")
                # Optionally call on_disconnect_cb again if needed, or ensure it's only called once
                return

            print(f"[{self.port_id}] Disconnecting from {self.port_url} (Reason: {reason})...")
            self._disconnect_requested.set()

            if self._write_task: # Signal writer to finish
                await self.write_queue.put(None) 
            
            tasks_to_wait_for = []
            if self._read_task: tasks_to_wait_for.append(self._read_task)
            if self._write_task: tasks_to_wait_for.append(self._write_task)

            if tasks_to_wait_for:
                done, pending = await asyncio.wait(tasks_to_wait_for, timeout=2.0, return_when=asyncio.ALL_COMPLETED)
                for task in pending:
                    print(f"[{self.port_id}] Cancelling pending task {task.get_name()} during disconnect.")
                    task.cancel()
                    try:
                        await task # Allow cancellation to process
                    except asyncio.CancelledError:
                        pass 
                    except Exception as e:
                        print(f"[{self.port_id}] Error in task {task.get_name()} during cancellation: {e}")
            
            self._read_task = None
            self._write_task = None

            if self._writer:
                try:
                    if not self._writer.is_closing():
                        self._writer.close()
                        await self._writer.wait_closed()
                except Exception as e:
                    print(f"[{self.port_id}] Error closing writer for {self.port_url}: {e}")
                finally:
                    self._writer = None
            
            self._reader = None
            self.is_connected = False
            print(f"[{self.port_id}] Disconnected from {self.port_url}")
            await _execute_callback(self.on_disconnect_cb, self.port_id, reason)

    def _process_buffer(self):
        """Processes _internal_read_buffer for frames."""
        processed_frame = False
        # No delimiters: treat all data as a single frame chunk (or stream if desired)
        if self.start_byte is None and self.stop_byte is None:
            if len(self._internal_read_buffer) > 0:
                frame = bytes(self._internal_read_buffer)
                self._internal_read_buffer.clear()
                self.read_queue.put_nowait(frame)
                self._loop.create_task(_execute_callback(self.on_data_received_cb, self.port_id, frame))
                processed_frame = True
            return processed_frame

        # Framing logic
        while True:
            start_index = -1
            if self.start_byte:
                start_index = self._internal_read_buffer.find(self.start_byte)
                if start_index == -1: # No start byte found yet
                    # If stop_byte is also defined, we might want to discard until start_byte.
                    # If only start_byte is defined, we wait.
                    # For now, just wait for more data if start_byte is expected.
                    if self.stop_byte is not None: 
                        #print(f"[{self.port_id}] No start byte, buffer: {self._internal_read_buffer}")
                        pass # Keep data for now, maybe it's a partial frame end
                    break 
                # Discard data before the first start_byte if we are strictly framing
                # Or, if !self.include_delimiters, we'd start search for stop_byte after start_byte
                if start_index > 0:
                     #print(f"[{self.port_id}] Discarding prefix: {self._internal_read_buffer[:start_index]}")
                     self._internal_read_buffer = self._internal_read_buffer[start_index:]
                     start_index = 0 # Relative index is now 0
            else: # No start byte defined, effectively start_index is 0
                start_index = 0

            stop_index = -1
            if self.stop_byte:
                search_offset = start_index + (len(self.start_byte) if self.start_byte else 0)
                stop_index = self._internal_read_buffer.find(self.stop_byte, search_offset)
                if stop_index == -1: # No stop byte found yet after start
                    if len(self._internal_read_buffer) > self.max_frame_length :
                        print(f"[{self.port_id}] Max frame length exceeded. Buffer flushed.")
                        self._internal_read_buffer.clear() # Avoid overflow
                    break # Wait for more data
            else: # No stop byte defined, frame is up to current data end or max_frame_length
                if self.start_byte and start_index == 0: # Frame starts with start_byte and ends with available data
                    # This logic might need refinement based on desired behavior without stop_byte
                    frame_end_index = min(len(self._internal_read_buffer), start_index + (len(self.start_byte) if self.start_byte else 0) + self.max_frame_length)
                    # For simplicity now, if no stop byte, we'll assume the data after start byte (if any) is the frame for now
                    # A more robust way would be fixed length or other protocol rule
                    if len(self._internal_read_buffer) > search_offset : # if there is data after start_byte
                        stop_index = len(self._internal_read_buffer) # Treat end of buffer as stop
                    else:
                        break # No data after start_byte yet

            # If we have a potential frame
            if start_index != -1 and stop_index != -1:
                frame_start_extract = start_index
                frame_end_extract = stop_index + len(self.stop_byte if self.stop_byte else b'')

                if not self.include_delimiters:
                    if self.start_byte: frame_start_extract += len(self.start_byte)
                    if self.stop_byte: frame_end_extract -= len(self.stop_byte)
                
                # Ensure extracted indices are valid
                if frame_start_extract < frame_end_extract :
                    frame = bytes(self._internal_read_buffer[frame_start_extract:frame_end_extract])
                    
                    # Check max frame length if delimiters are not included in this check (could be stricter)
                    if len(frame) > self.max_frame_length:
                        print(f"[{self.port_id}] Frame exceeded max length after extraction. Discarded.")
                        # Consume the oversized frame from buffer to allow parsing next
                        self._internal_read_buffer = self._internal_read_buffer[stop_index + len(self.stop_byte if self.stop_byte else b''):]
                        continue # try to process rest of buffer

                    self.read_queue.put_nowait(frame)
                    self._loop.create_task(_execute_callback(self.on_data_received_cb, self.port_id, frame))
                    processed_frame = True
                else: # Frame is empty or invalid after stripping delimiters
                    print(f"[{self.port_id}] Empty or invalid frame after stripping delimiters.")
                    pass

                # Remove the processed part (including delimiters for consumption)
                self._internal_read_buffer = self._internal_read_buffer[stop_index + len(self.stop_byte if self.stop_byte else b''):]
            else: # No complete frame found in this pass
                break
        return processed_frame

    async def _read_loop(self):
        print(f"[{self.port_id}] Read loop started.")
        connection_lost_reason = "Read loop ended"
        try:
            while not self._disconnect_requested.is_set() and self._reader:
                try:
                    data = await asyncio.wait_for(self._reader.read(self._read_buffer_size), timeout=0.1)
                    if data:
                        self._internal_read_buffer.extend(data)
                        self._process_buffer()
                    elif not data and self.is_connected: # EOF
                        print(f"[{self.port_id}] Read EOF, port closed by other end.")
                        connection_lost_reason = "EOF received"
                        self._disconnect_requested.set()
                        break
                except asyncio.TimeoutError:
                    continue 
                except SerialException as e:
                    print(f"[{self.port_id}] SerialException in read loop: {e}")
                    connection_lost_reason = f"SerialException: {e}"
                    self._disconnect_requested.set()
                    break
                except asyncio.CancelledError:
                    connection_lost_reason = "Read loop cancelled"
                    print(f"[{self.port_id}] {connection_lost_reason}")
                    break
                except Exception as e:
                    print(f"[{self.port_id}] Unexpected error in read loop: {e}")
                    connection_lost_reason = f"Unexpected error: {e}"
                    self._disconnect_requested.set()
                    break
        finally:
            print(f"[{self.port_id}] Read loop stopped.")
            if self._disconnect_requested.is_set() and self.is_connected:
                # Ensure disconnect procedure runs if loop exited due to error/EOF
                self._loop.create_task(self._disconnect_async(reason=connection_lost_reason))


    async def _write_loop(self):
        print(f"[{self.port_id}] Write loop started.")
        try:
            while True:
                data_to_write = None
                try:
                    # Wait for data, but with a timeout to check disconnect_requested
                    data_to_write = await asyncio.wait_for(self.write_queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    if self._disconnect_requested.is_set() and self.write_queue.empty():
                        break # Exit if disconnect requested and queue is now empty
                    continue

                if data_to_write is None: # Sentinel value from disconnect
                    self.write_queue.task_done()
                    break 
                
                if not self.is_connected or not self._writer:
                    print(f"[{self.port_id}] Cannot write: Not connected or writer unavailable.")
                    await _execute_callback(self.on_data_sent_cb, self.port_id, data_to_write, False, "Not connected")
                    self.write_queue.task_done()
                    continue

                try:
                    self._writer.write(data_to_write)
                    await self._writer.drain()
                    await _execute_callback(self.on_data_sent_cb, self.port_id, data_to_write, True, None)
                except SerialException as e:
                    print(f"[{self.port_id}] SerialException in write loop: {e}")
                    await _execute_callback(self.on_data_sent_cb, self.port_id, data_to_write, False, str(e))
                    self._disconnect_requested.set() # Trigger disconnect on serial write error
                    # Do not break immediately, let disconnect_async handle cleanup
                except asyncio.CancelledError:
                    print(f"[{self.port_id}] Write loop cancelled.")
                    await _execute_callback(self.on_data_sent_cb, self.port_id, data_to_write, False, "Write cancelled")
                    break
                except Exception as e:
                    print(f"[{self.port_id}] Unexpected error in write loop: {e}")
                    await _execute_callback(self.on_data_sent_cb, self.port_id, data_to_write, False, str(e))
                    self._disconnect_requested.set()
                finally:
                    if not self.write_queue.empty(): # Ensure task_done is called if an error happened mid-write
                         self.write_queue.task_done()

        finally:
            print(f"[{self.port_id}] Write loop stopped.")
            # Clear any remaining items from the queue if disconnect was abrupt
            while not self.write_queue.empty():
                try:
                    item = self.write_queue.get_nowait()
                    print(f"[{self.port_id}] Discarding unsent item: {item}")
                    await _execute_callback(self.on_data_sent_cb, self.port_id, item, False, "Discarded on disconnect")
                    self.write_queue.task_done()
                except asyncio.QueueEmpty:
                    break
            if self._disconnect_requested.is_set() and self.is_connected:
                 self._loop.create_task(self._disconnect_async(reason="Write loop ended"))


    def get_queued_frame(self, timeout=0):
        """Synchronously tries to get a frame. Returns None if empty or timeout."""
        try:
            if timeout <= 0:
                return self.read_queue.get_nowait()
            else: # This part is tricky to make truly sync with timeout without blocking asyncio thread.
                  # For now, this will still raise QueueEmpty if not immediately available.
                  # A better approach for sync get with timeout would involve futures from asyncio thread.
                  # Simplification: use get_nowait and rely on callbacks for data arrival.
                print("Warning: Synchronous get_queued_frame with timeout > 0 is not truly blocking; effectively get_nowait.")
                return self.read_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None
        finally:
            if not self.read_queue.empty(): # Check if an item was indeed retrieved
                try: self.read_queue.task_done() # Must be called if get_nowait succeeded
                except ValueError: pass # If already marked done or queue became empty

    def send_data(self, data: bytes):
        """Puts data onto the write queue. Returns True if successful, False otherwise."""
        if not self.is_connected and not self._writer: # Check if we think we can write
             print(f"[{self.port_id}] Cannot queue data for sending: Not connected or writer not available.")
             # Call on_data_sent_cb from the calling thread's context if not connected?
             # For consistency, callbacks are from asyncio thread. This will be reported by write_loop.
             # self._loop.call_soon_threadsafe(_execute_callback, self.on_data_sent_cb, self.port_id, data, False, "Not connected before queuing")
             return False
        try:
            self.write_queue.put_nowait(data)
            return True
        except asyncio.QueueFull:
            print(f"[{self.port_id}] Write queue full for {self.port_url}")
            # self._loop.call_soon_threadsafe(_execute_callback, self.on_data_sent_cb, self.port_id, data, False, "Write queue full")
            return False


    def get_status(self):
        return {
            "port_id": self.port_id,
            "port_url": self.port_url,
            "baudrate": self.baudrate,
            "is_connected": self.is_connected,
            "read_queue_size": self.read_queue.qsize(),
            "write_queue_size": self.write_queue.qsize(),
            "start_byte": self.start_byte,
            "stop_byte": self.stop_byte
        }

class SerialManager:
    def __init__(self, loop=None):
        self._is_loop_externally_managed = loop is not None
        self._loop = loop or asyncio.new_event_loop()
        self._loop_thread = None
        self.serial_ports = {} # port_id: AsyncSerialPort

        if not self._is_loop_externally_managed:
            print("SerialManager: Managing internal asyncio event loop.")
        else:
            print("SerialManager: Using externally provided asyncio event loop.")

    def start_event_loop(self):
        """Starts the asyncio event loop in a background thread if managed internally."""
        if self._is_loop_externally_managed:
            print("SerialManager: Event loop is externally managed, cannot start/stop from here.")
            return False
        if self._loop_thread and self._loop_thread.is_alive():
            print("SerialManager: Event loop thread already running.")
            return True
        
        self._loop_thread = threading.Thread(target=self._run_loop, daemon=True, name="SerialAsyncioLoop")
        self._loop_thread.start()
        # Add a small delay or a mechanism to ensure the loop is running before returning
        # For simplicity, we assume it starts quickly. A future/event could be used.
        print("SerialManager: Event loop thread started.")
        return True

    def _run_loop(self):
        print("SerialManager: Asyncio event loop starting in background thread.")
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_forever()
        finally:
            print("SerialManager: Asyncio event loop in background thread has stopped.")
            # Ensure cleanup of pending tasks if loop stops unexpectedly
            if self._loop.is_running(): # Should not happen if run_forever exited normally
                self._loop.call_soon_threadsafe(self._loop.stop) 
            # Gather remaining tasks
            pending = asyncio.all_tasks(loop=self._loop)
            if pending:
                print(f"SerialManager: Gathering {len(pending)} pending tasks before closing loop...")
                self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            print("SerialManager: Closing asyncio loop.")
            self._loop.close()


    def stop_event_loop(self, timeout=5):
        """Stops the internally managed asyncio event loop and associated serial ports."""
        if self._is_loop_externally_managed:
            print("SerialManager: Event loop is externally managed, cannot start/stop from here.")
            return
        if not self._loop_thread or not self._loop_thread.is_alive() or not self._loop.is_running():
            print("SerialManager: Event loop thread not running or loop not active.")
            return

        print("SerialManager: Initiating shutdown of all serial ports...")
        # Disconnect all ports
        futs = []
        for port_id in list(self.serial_ports.keys()): # list keys because dict might change if disconnect removes port
            port = self.serial_ports.get(port_id)
            if port and port.is_connected:
                # Schedule disconnect on the loop
                fut = asyncio.run_coroutine_threadsafe(port._disconnect_async(reason="Manager shutdown"), self._loop)
                futs.append(fut)
        
        # Wait for disconnect futures to complete
        if futs:
            print(f"SerialManager: Waiting for {len(futs)} ports to disconnect...")
            for fut in futs:
                try:
                    fut.result(timeout=timeout/len(futs) if len(futs)>0 else timeout) 
                except Exception as e:
                    print(f"SerialManager: Error waiting for port disconnect future: {e}")
        
        print("SerialManager: Stopping event loop...")
        if self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        
        self._loop_thread.join(timeout=timeout)
        if self._loop_thread.is_alive():
            print("SerialManager: Event loop thread did not terminate gracefully.")
        else:
            print("SerialManager: Event loop thread stopped.")
        self._loop_thread = None


    def add_port(self, port_id, port_url, baudrate, 
                 start_byte=None, stop_byte=None, include_delimiters=False,
                 max_frame_length=4096, read_buffer_size=1024, **kwargs):
        if not self._loop.is_running() and not self._is_loop_externally_managed and (not self._loop_thread or not self._loop_thread.is_alive()):
             print("Warning: Adding port but internal event loop is not running. Call start_event_loop().")

        if port_id in self.serial_ports:
            print(f"SerialManager: Port ID {port_id} already exists.")
            return self.serial_ports[port_id]
        
        port = AsyncSerialPort(port_id, port_url, baudrate, self._loop,
                               start_byte, stop_byte, include_delimiters,
                               max_frame_length, read_buffer_size, **kwargs)
        self.serial_ports[port_id] = port
        print(f"SerialManager: Added port {port_id} for {port_url}")
        return port

    def connect_port(self, port_id: str):
        """Initiates connection for a port. Non-blocking. Result via callback."""
        if not self._loop.is_running():
            print(f"SerialManager: Cannot connect port {port_id}, event loop not running.")
            # Optionally, directly call the on_connect_cb with failure here if desired for sync feedback
            port = self.serial_ports.get(port_id)
            if port and port.on_connect_cb:
                # This direct call would be from the calling thread, not asyncio thread.
                # Consider consistency vs immediate feedback.
                # For now, let the async path handle it if loop starts later.
                pass
            return None 

        port = self.serial_ports.get(port_id)
        if not port:
            print(f"SerialManager: Port ID {port_id} not found.")
            return None
        
        future = asyncio.run_coroutine_threadsafe(port._connect_async(), self._loop)
        return future # Caller can optionally wait on this future, but UI shouldn't.

    def disconnect_port(self, port_id: str, reason="User initiated"):
        """Initiates disconnection for a port. Non-blocking. Result via callback."""
        if not self._loop.is_running():
            print(f"SerialManager: Cannot disconnect port {port_id}, event loop not running.")
            return None

        port = self.serial_ports.get(port_id)
        if not port:
            print(f"SerialManager: Port ID {port_id} not found.")
            return None
        
        future = asyncio.run_coroutine_threadsafe(port._disconnect_async(reason=reason), self._loop)
        return future

    def set_port_callbacks(self, port_id, on_connect=None, on_disconnect=None, on_data_received=None, on_data_sent=None):
        port = self.serial_ports.get(port_id)
        if port:
            port.set_callbacks(on_connect, on_disconnect, on_data_received, on_data_sent)
        else:
            print(f"SerialManager: Port ID {port_id} not found for setting callbacks.")

    def get_received_frame(self, port_id: str, timeout:float =0):
        port = self.serial_ports.get(port_id)
        if port:
            return port.get_queued_frame(timeout) # timeout currently not fully supported for >0
        print(f"SerialManager: Port ID {port_id} not found for reading frame.")
        return None

    def send_data_to_port(self, port_id: str, data: bytes):
        port = self.serial_ports.get(port_id)
        if port:
            return port.send_data(data)
        print(f"SerialManager: Port ID {port_id} not found for sending data.")
        return False

    def get_port_status(self, port_id: str):
        port = self.serial_ports.get(port_id)
        if port:
            return port.get_status()
        return None
    
    def get_all_statuses(self):
        return {pid: p.get_status() for pid, p in self.serial_ports.items()}

# --- Example Usage (Illustrative - UI marshalling not shown) ---
if __name__ == "__main__":
    import time

    # --- Define Callbacks (these would interact with UI in a real app) ---
    # IMPORTANT: If these callbacks update UI, they MUST marshal the call to the UI thread.
    # Example: For Tkinter, you'd use root.after(0, lambda: actual_ui_update_func(args))

    def handle_connect(port_id, success, message):
        print(f"[CALLBACK] Connect: Port {port_id}, Success: {success}, Msg: {message}")
        if success:
            # Example: manager.send_data_to_port(port_id, b"<HELLO>\n")
            pass

    def handle_disconnect(port_id, reason):
        print(f"[CALLBACK] Disconnect: Port {port_id}, Reason: {reason}")

    def handle_data_received(port_id, frame):
        # Frame is bytes. Decode if it's text.
        try:
            print(f"[CALLBACK] Data Received on {port_id}: {frame.decode(errors='replace')} (raw: {frame})")
        except UnicodeDecodeError:
            print(f"[CALLBACK] Data Received on {port_id} (binary): {frame}")

    def handle_data_sent(port_id, original_data, success, error_message):
        if success:
            print(f"[CALLBACK] Data Sent on {port_id}: {original_data}")
        else:
            print(f"[CALLBACK] Data Send Failed on {port_id}: {original_data}, Error: {error_message}")

    # --- Main Application Logic ---
    manager = SerialManager() # Manages its own loop
    manager.start_event_loop() # Start the background asyncio thread

    # For testing without real hardware, you can use socat to create virtual serial port pairs:
    # socat -d -d pty,raw,echo=0,link=/tmp/vsp1_tx pty,raw,echo=0,link=/tmp/vsp1_rx
    # socat -d -d pty,raw,echo=0,link=/tmp/vsp2_tx pty,raw,echo=0,link=/tmp/vsp2_rx
    # Use /tmp/vsp1_tx and /tmp/vsp2_tx as port_url. Connect to _rx with a serial terminal.
    
    PORT1_ID = "GPS_Device"
    PORT1_URL = "/tmp/vsp1_tx" # Change to your actual port
    # Example framing: NMEA sentences like $GPGGA,...,*CS\r\n
    # For this, start_byte=b'$', stop_byte=b'\n', include_delimiters=True
    
    PORT2_ID = "Sensor_Device"
    PORT2_URL = "/tmp/vsp2_tx" # Change to your actual port
    # Example framing: <data>\r
    # start_byte=b'<', stop_byte=b'>', include_delimiters=True (or False if you want content only)


    # Add ports
    manager.add_port(PORT1_ID, PORT1_URL, 9600,
                     start_byte=b'$', stop_byte=b'\n', include_delimiters=True)
    manager.add_port(PORT2_ID, PORT2_URL, 115200,
                     start_byte=b'<', stop_byte=b'>', include_delimiters=False)

    # Set callbacks
    manager.set_port_callbacks(PORT1_ID, 
                               on_connect=handle_connect, 
                               on_disconnect=handle_disconnect,
                               on_data_received=handle_data_received,
                               on_data_sent=handle_data_sent)
    manager.set_port_callbacks(PORT2_ID,
                               on_connect=handle_connect,
                               on_disconnect=handle_disconnect,
                               on_data_received=handle_data_received,
                               on_data_sent=handle_data_sent)

    print("Attempting to connect to ports (non-blocking)...")
    manager.connect_port(PORT1_ID)
    conn_future_p2 = manager.connect_port(PORT2_ID)
    
    # You could optionally wait for a specific connection for non-UI setup
    if conn_future_p2:
        try:
            # This is blocking, avoid in UI thread for long periods
            # conn_future_p2.result(timeout=5) 
            # print("Port 2 connect future completed (or timed out if blocking)")
            pass
        except Exception as e:
            print(f"Error waiting on Port 2 connect future: {e}")


    print("Main thread continues to run...")
    # Simulate application running and sending data periodically
    try:
        count = 0
        while count < 20: # Run for 20 seconds
            if manager.get_port_status(PORT1_ID) and manager.get_port_status(PORT1_ID)['is_connected']:
                manager.send_data_to_port(PORT1_ID, f"$TEST,{count}*\r\n".encode())
            
            if manager.get_port_status(PORT2_ID) and manager.get_port_status(PORT2_ID)['is_connected']:
                 manager.send_data_to_port(PORT2_ID, f"<SENSOR_DATA_{count}>".encode())
            
            # Example of synchronously trying to get data (not recommended for primary data handling)
            # frame1 = manager.get_received_frame(PORT1_ID)
            # if frame1:
            #     print(f"[MAIN THREAD SYNC READ] Port 1: {frame1.decode(errors='replace')}")

            time.sleep(1)
            count += 1
            print(f"Main thread heartbeat {count}s. Statuses: {manager.get_all_statuses()}")
            if not manager._loop.is_running() and not manager._is_loop_externally_managed:
                print("Main thread: Loop seems to have stopped unexpectedly.")
                break


    except KeyboardInterrupt:
        print("Main thread: Keyboard interrupt received.")
    finally:
        print("Main thread: Shutting down...")
        manager.disconnect_port(PORT1_ID) # Initiate disconnect
        manager.disconnect_port(PORT2_ID)
        
        # Give some time for disconnect operations scheduled on the loop
        time.sleep(1) 
        
        manager.stop_event_loop() # Stops the loop and thread
        print("Main thread: Exited.")