import threading
import asyncio
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor  # For running blocking callbacks


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


class EventLoop:
    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self.__run_loop, daemon=True)
        self._tasks = {}  # Store tasks by name
        self._callbacks_soon = deque()
        self._executor = ThreadPoolExecutor() # For running callbacks in a thread
        self._is_running = False
        self._thread.start()

    def __del__(self):
        print("Stopping event loop...")
        # if self._is_running:
        #     self.stop()
        # if self._thread.is_alive():
        #     self._thread.join()
        if self._loop.is_running():
            self._loop.stop()
        self._executor.shutdown(wait=True)
        print("Event loop stopped.")

    def __run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._is_running = True
        self._loop.run_forever()
        self._is_running = False

    def create_task(self, task_name, coro):
        if task_name in self._tasks:
            raise ValueError(f"Task with name '{task_name}' already exists.")
        if not asyncio.iscoroutine(coro):
            raise TypeError("Expected a coroutine for create_task.")
        task = self._loop.create_task(coro)
        self._tasks[task_name] = task
        return task

    def run_callback_soon(self, callback, *args, **kwargs):
        if not callable(callback):
            raise TypeError("Expected a callable for run_callback_soon.")
        self._loop.call_soon_threadsafe(self._invoke_callback, callback, *args, **kwargs)

    def run_callback_in_thread(self, callback, *args, **kwargs):
        if not callable(callback):
            raise TypeError("Expected a callable for run_callback_in_thread.")
        return asyncio.run_coroutine_threadsafe(self._run_in_executor(callback, *args, **kwargs), self._loop)

    async def _run_in_executor(self, func, *args, **kwargs):
        return await self._loop.run_in_executor(self._executor, func, *args, **kwargs)

    def call_soon(self, callback, *args, **kwargs):
        if not callable(callback):
            raise TypeError("Expected a callable for call_soon.")
        self._loop.call_soon(callback, *args, **kwargs)

    def call_later(self, delay, callback, *args, **kwargs):
        if not callable(callback):
            raise TypeError("Expected a callable for call_later.")
        return self._loop.call_later(delay, callback, *args, **kwargs)

    def get_task(self, task_name):
        return self._tasks.get(task_name)

    def cancel_task(self, task_name):
        task = self.get_task(task_name)
        if task:
            task.cancel()
            return True
        return False

    def stop(self):
        if self._is_running:
            # for task in self._tasks.values():
            #     if not task.done():
            #         task.cancel()
            # Gather all pending tasks and wait for them to finish (or be cancelled)
            pending = asyncio.all_tasks(loop=self._loop)
            for task in pending:
                if not task.done():
                    task.cancel()
            # asyncio.run_coroutine_threadsafe(asyncio.gather(*pending), self._loop)
            self._loop.call_soon(*pending)
            self._loop.stop()

    def is_running(self):
        return self._is_running

    def _invoke_callback(self, callback, *args, **kwargs):
        try:
            callback(*args, **kwargs)
        except Exception as e:
            print(f"Error in callback: {e}")


def test_executor():
    """
    Test the ThreadPoolExecutor functionality.
    """
    def blocking_io():
        print("Starting blocking IO...")
        time.sleep(5)
        print("Blocking IO finished.")
        return "IO Result"

    loop = EventLoop()
    future = loop.run_callback_in_thread(blocking_io)
    result = future.result()  # Wait for the result
    print(f"Result from blocking IO: {result}")
    
    
    
    
    async def my_coroutine():
        print("Coroutine started...")
        await asyncio.sleep(5)
        print("Coroutine finished!")
        return "Coroutine result"

    def my_callback(message):
        print(f"Callback executed: {message}")

    def blocking_io():
        print("Starting blocking IO...")
        time.sleep(5)
        print("Blocking IO finished.")
        return "IO Result"

    loop = EventLoop()

    task1 = loop.create_task("my_task", my_coroutine())
    loop.run_callback_soon(my_callback, "Hello from run_callback_soon!")
    future = loop.run_callback_in_thread(blocking_io)
    loop.call_later(1, my_callback, "Hello from call_later!")
    loop.call_soon(my_callback, "Hello from call_soon!")

    time.sleep(3)
    print(f"Is loop running? {loop.is_running()}")
    loop.cancel_task("my_task")
    loop.__del__()
    # Keep the main thread alive for a bit to see the loop in action
    try:
        time.sleep(5)
    except KeyboardInterrupt:
        pass

    # The __del__ method will be called when the 'loop' object is garbage collected
    del loop
    
    

    
# Example usage:
if __name__ == "__main__":
    test_executor()