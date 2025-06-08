import asyncio
import threading
import atexit
import signal
import sys
import weakref
from typing import Any, Callable, Optional, Union, Coroutine, TypeVar, Set
from concurrent.futures import ThreadPoolExecutor, Future
from functools import wraps
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ManagedTask:
    """Wrapper for tasks with lifecycle management"""
    
    def __init__(self, task: asyncio.Task, destroy_callback: Optional[Callable] = None):
        self.task = task
        self.destroy_callback = destroy_callback
        self._destroyed = False
    
    async def destroy(self):
        """Destroy the task gracefully"""
        if self._destroyed:
            return
            
        self._destroyed = True
        
        if self.destroy_callback:
            try:
                if asyncio.iscoroutinefunction(self.destroy_callback):
                    await self.destroy_callback()
                else:
                    self.destroy_callback()
            except Exception as e:
                logger.error(f"Error in task destroy callback: {e}")
        
        if not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass


class EventLoopManager:
    """
    Thread-safe event loop manager that runs in a separate thread.
    
    Usage:
        loop_manager = EventLoopManager()
        loop_manager.start()
        
        # Add tasks
        task = loop_manager.add_task(some_coroutine())
        
        # Run and wait for result
        result = loop_manager.run_and_wait(some_coroutine())
        
        # Cleanup (also called automatically on exit)
        loop_manager.destroy()
    """
    
    _instances = {}
    _lock = threading.Lock()
    
    @classmethod
    def create_instance(cls, name:str ) -> 'EventLoopManager':
        """Create a new instance of EventLoopManager"""
        with cls._lock:
            if name in cls._instances:
                return cls._instances[name]
            instance = cls(name)
            cls._instances[name] = instance
        return instance 

    def __init__(self, name : Optional[str] = None):
        """Initialize the event loop manager"""
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        self._name = name or "EventLoopManager"
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._started = threading.Event()
        self._stopping = False
        self._task_list: Set[ManagedTask] = set()
        self._task_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._destroy_callbacks: list[Callable] = []
        
        # Register cleanup handlers
        atexit.register(self._cleanup)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        self.destroy()
        sys.exit(0)
    
    @property
    def is_running(self) -> bool:
        """Check if the event loop is running"""
        return self._loop is not None and self._loop.is_running()
    
    @property
    def is_stopped(self) -> bool:
        """Check if the event loop is stopped"""
        return self._loop is None or not self._loop.is_running()
    
    def _run_loop(self):
        """Run the event loop in a separate thread"""
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._started.set()
            self._loop.run_forever()
        except Exception as e:
            logger.error(f"Event loop error: {e}")
        finally:
            self._loop.close()
            self._loop = None
    
    def start(self):
        """Start the event loop in a separate thread"""
        if self._thread and self._thread.is_alive():
            return
        
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._started.wait()  # Wait for loop to be ready
        logger.info("Event loop started")
    
    def create(self):
        """Alias for start() to match requested API"""
        self.start()
    
    def _ensure_started(self):
        """Ensure the event loop is running"""
        if self._stopping:
            raise RuntimeError("Event loop manager is stopping, cannot add tasks")
        if self._loop and not self._loop.is_running():
            raise RuntimeError("Event loop is not running, call start() first")
        # If the thread is not alive, restart it
        if self._thread and not self._thread.is_alive():
            self.start()
    
    def add_task(self, coro: Coroutine[Any, Any, T], 
                 destroy_callback: Optional[Callable] = None) -> asyncio.Task[T]:
        """
        Add a coroutine to event loop and track it
        
        Args:
            coro: Coroutine to run
            destroy_callback: Optional callback to run when task is destroyed
            
        Returns:
            Coro future that will contain the result of the coroutine
        """
        self._ensure_started()
        # Ensure the coroutine is a valid asyncio coroutine
        fut=  asyncio.run_coroutine_threadsafe(
            self._create_managed_task(coro, destroy_callback),
            self._loop
        )
        return fut.result()  # Wait for task to be created and return the task object
        
    
    async def _create_managed_task(self, coro: Coroutine[Any, Any, T], 
                                   destroy_callback: Optional[Callable] = None) -> asyncio.Task[T]:
        """Create and track a managed task"""
        if not asyncio.iscoroutine(coro):
            raise ValueError("Provided object is not a coroutine")
        
        task = asyncio.create_task(coro)
        managed_task = ManagedTask(task, destroy_callback)
        
        with self._task_lock:
            self._task_list.add(managed_task)
        
        # Remove from tracking when done
        def cleanup(_):
            with self._task_lock:
                self._task_list.discard(managed_task)
        
        task.add_done_callback(cleanup)
        return task
    
    def add_coroutine(self, coro: Coroutine[Any, Any, T]) -> asyncio.Task[T]:
        """Alias for add_task() to match requested API"""
        self._ensure_started()
        return asyncio.run_coroutine_threadsafe(
            coro, 
            self._loop)
    
    def run_task(self, coro: Coroutine[Any, Any, T]) -> Future[T]:
        """
        Run a coroutine and return a Future
        
        Args:
            coro: Coroutine to run
            
        Returns:
            concurrent.futures.Future that will contain the result
        """
        self._ensure_started()
        return asyncio.run_coroutine_threadsafe(coro, self._loop)
    
    def run_and_wait(self, coro: Coroutine[Any, Any, T], timeout: Optional[float] = None) -> T:
        """
        Run a coroutine and wait for its result
        
        Args:
            coro: Coroutine to run
            timeout: Optional timeout in seconds
            
        Returns:
            The result of the coroutine
        """
        future = self.run_task(coro)
        return future.result(timeout=timeout)
    
    def w4_result(self, coro: Coroutine[Any, Any, T], timeout: Optional[float] = None) -> T:
        """Alias for run_and_wait() to match requested API"""
        return self.run_and_wait(coro, timeout)
    
    def run_in_executor(self, func: Callable[..., T], *args, **kwargs) -> Future[T]:
        """
        Run a synchronous function in the thread pool executor
        
        Args:
            func: Function to run
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            concurrent.futures.Future that will contain the result
        """
        self._ensure_started()
        
        async def executor_wrapper():
            return await self._loop.run_in_executor(
                self._executor, func, *args
            )
        
        return self.run_task(executor_wrapper())
    
    def add_callback(self, callback: Callable, *args, **kwargs):
        """
        Schedule a callback to run in the event loop
        
        Args:
            callback: Function to call
            *args, **kwargs: Arguments to pass to the callback
        """
        self._ensure_started()
        self._loop.call_soon_threadsafe(callback, *args)
    
    def add_task_destroy_callback(self, callback: Callable):
        """
        Add a callback to be called when destroying all tasks
        
        Args:
            callback: Function to call during task destruction
        """
        self._destroy_callbacks.append(callback)
    
    def stop(self):
        """Stop the event loop (can be restarted)"""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
            logger.info("Event loop stopped")
    
    def close(self):
        """Close the event loop (cannot be restarted without creating new loop)"""
        self.stop()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("Event loop closed")
    
    async def _destroy_all_tasks(self):
        """Destroy all managed tasks gracefully"""
        # Call destroy callbacks
        for callback in self._destroy_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Error in destroy callback: {e}")
        
        # Destroy all tasks
        with self._task_lock:
            tasks = list(self._task_list)
        
        if tasks:
            logger.info(f"Destroying {len(tasks)} tasks...")
            destroy_tasks = [task.destroy() for task in tasks]
            await asyncio.gather(*destroy_tasks, return_exceptions=True)
        
        # Cancel any remaining tasks
        pending = [t for t in asyncio.all_tasks(self._loop) 
                  if not t.done() and t != asyncio.current_task()]
        
        if pending:
            logger.info(f"Cancelling {len(pending)} remaining tasks...")
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
    
    def destroy(self):
        """
        Gracefully destroy the event loop manager
        
        This will:
        1. Call destroy callbacks
        2. Destroy all managed tasks
        3. Stop and close the event loop
        """
        if self._stopping:
            return
            
        self._stopping = True
        logger.info("Destroying event loop manager...")
        
        if self._loop and self._loop.is_running():
            # Schedule task destruction in the event loop
            future = asyncio.run_coroutine_threadsafe(
                self._destroy_all_tasks(),
                self._loop
            )
            
            try:
                future.result(timeout=10)
            except Exception as e:
                logger.error(f"Error during task destruction: {e}")
        
        # Close executor
        self._executor.shutdown(wait=True)
        
        # Stop and close loop
        self.close()
        
        logger.info("Event loop manager destroyed")
    
    def _cleanup(self):
        """Cleanup handler for atexit"""
        if not self._stopping:
            self.destroy()
    
    @property
    def is_running(self) -> bool:
        """Check if the event loop is running"""
        return (self._loop is not None and 
                self._loop.is_running() and 
                self._thread is not None and 
                self._thread.is_alive())
    
    @property
    def loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """Get the event loop (use with caution)"""
        return self._loop


# Global instance for convenience
_default_manager: Optional[EventLoopManager] = None


def get_event_loop_manager() -> EventLoopManager:
    """Get or create the default event loop manager"""
    global _default_manager
    if _default_manager is None:
        _default_manager = EventLoopManager()
        _default_manager.start()
    return _default_manager


# Decorator for async functions to run in the event loop
def run_async(func: Callable[..., Coroutine[Any, Any, T]] = None, *, manager: Optional[EventLoopManager] = None) -> Callable[..., T]:
    """
    Decorator to automatically run async functions in the event loop

    Usage:
        @run_async
        async def my_async_function():
            await asyncio.sleep(1)
            return "done"

        # Or with a specific manager:
        @run_async(manager=my_manager)
        async def my_async_function():
            ...

        # Can now call directly without await
        result = my_async_function()
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            mgr = manager or get_event_loop_manager()
            return mgr.run_and_wait(f(*args, **kwargs))
        return wrapper

    if func is not None:
        return decorator(func)
    return decorator

# Example usage and testing
if __name__ == "__main__":
    import time
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create manager
    manager = EventLoopManager()
    manager.start()
    
    # Example coroutine
    async def example_task(name: str, duration: float):
        print(f"Task {name} started")
        await asyncio.sleep(duration)
        print(f"Task {name} completed")
        return f"Result from {name}"
    
    # Example destroy callback
    def task_destroy_callback():
        print("Task is being destroyed!")
    
    # Add tasks
    task1 = manager.add_task(example_task("Task1", 2), task_destroy_callback)
    task2 = manager.add_task(example_task("Task2", 3))
    
    # Run and wait for result
    result = manager.run_and_wait(example_task("Task3", 1))
    print(f"Task3 result: {result}")
    
    # Run in executor
    @run_async(manager= manager)
    async def sync_function(x, y):
        await asyncio.sleep(2.5)
        return x + y
    
    res = sync_function(5, 10)
    print(f"Executor result: {res}")
    
    # Wait a bit
    time.sleep(1)
    
    # Destroy manager (also happens automatically on exit)
    manager.destroy()