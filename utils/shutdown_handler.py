"""
Hierarchical Shutdown Handler for Graceful Application Termination

This module provides a priority-based shutdown system that ensures resources
are cleaned up in the correct order, preventing:
- Use-after-free errors
- Resource leaks
- Race conditions during shutdown
- Deadlocks

#Priority levels (lower number = earlier execution):
#    0-99:   Critical infrastructure (event loops, signal handlers)
#    100-199: High-level services (logging, monitoring)
#    200-299: Application resources (file handlers, network connections)
#    300-399: User-level resources (caches, temporary files)
#    400+:    Low priority cleanup (statistics, debug info)
"""

import atexit
import signal
import sys
import threading
import weakref
import time
from typing import Callable, Optional, Dict, List, Any, Tuple
from enum import Enum, auto, unique
from dataclasses import dataclass, field
from collections import defaultdict
import traceback


@unique
class ShutdownState(Enum):
    """Shutdown handler states"""
    IDLE = auto()
    INITIATED = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()

@unique
class ShutdownPriority(Enum):
    """Standard priority levels for common resources"""
    # Critical infrastructure (destroy last, as others depend on it)
    MIN_PRIORITY = 2
    EVENT_LOOP = 50
    SIGNAL_HANDLER = 40

    # High-level services
    LOGGING = 150
    MONITORING = 160
    
    # Application resources
    FILE_HANDLERS = 250
    FILE_LOG_HANDLERS = 255
    
    
    NETWORK_CONNECTIONS = 260
    DATABASE_CONNECTIONS = 270
    
    DEFAULT_PRIORITY = 300
    
    # logger impleemtnation 
    LOGGER_MAIN = 301

    
    
    # User-level resources
    CACHE = 350
    TEMP_FILES = 360
    
    # Informational
    STATISTICS = 450
    DEBUG_INFO = 460
    
    # MAX priority 
    MAX_PRIORITY = 500


# we reire order to true as priority used by sorted function 
@dataclass(order=True)
class ShutdownTask:
    """A task to execute during shutdown"""
    priority: int = field(compare=True)
    name: str = field(compare=False)
    callback: Callable = field(compare=False)
    timeout: float = field(default=5.0, compare=False)
    args: tuple = field(default_factory=tuple, compare=False)
    kwargs: dict = field(default_factory=dict, compare=False)
    critical: bool = field(default=False, compare=False)  # If True, failure blocks shutdown
    
    def __post_init__(self):
        self.result: Optional[Any] = None
        self.error: Optional[Exception] = None
        self.completed: bool = False
        self.execution_time: float = 0.0

#MARK:Shutdownhandler
class ShutdownHandler:
    """
    Singleton shutdown handler with hierarchical resource management
    
    Features:
    - Priority-based execution order
    - Timeout protection per task
    - Thread-safe registration
    - Signal handling integration
    - Detailed error reporting
    - Circular dependency detection
    """
    
    _instance: Optional['ShutdownHandler'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._state = ShutdownState.IDLE
        self._state_lock = threading.Lock()
        
        # Task management
        self._tasks: List[ShutdownTask] = []
        self._tasks_lock = threading.Lock()
        self._task_groups: Dict[str, List[ShutdownTask]] = defaultdict(list)
        
        # Execution tracking
        self._executed_tasks: List[Tuple[ShutdownTask, bool]] = []
        self._failed_tasks: List[Tuple[ShutdownTask, Exception]] = []
        
        # Signal handling
        self._original_handlers: Dict[int, Any] = {}
        self._shutdown_requested = threading.Event()
        self._force_shutdown = threading.Event()
        
        # Configuration
        self._verbose = True
        self._max_total_time = 30.0  # Maximum time for entire shutdown
        self._emergency_exit_delay = 2.0  # Grace period before force exit
        
        # Register built-in cleanup
        self._register_builtin_handlers()
        
        # Install signal handlers
        self._install_signal_handlers()
        
        # Register with atexit
        atexit.register(self._atexit_handler)
    
    def _register_builtin_handlers(self):
        """Register built-in cleanup handlers"""
        # These are placeholders - actual implementations should register themselves
        pass
    
    def _install_signal_handlers(self):
        """Install signal handlers for graceful shutdown"""
        signals_to_handle = [signal.SIGINT, signal.SIGTERM]
        
        if sys.platform != 'win32':
            signals_to_handle.append(signal.SIGHUP)
        
        for sig in signals_to_handle:
            try:
                self._original_handlers[sig] = signal.signal(sig, self._signal_handler)
            except (OSError, ValueError) as e:
                self._log(f"Cannot install handler for signal {sig}: {e}")
    
    def _signal_handler(self, signum: int, frame):
        """Handle shutdown signals"""
        sig_name = signal.Signals(signum).name
        self._log(f"Received signal {sig_name} ({signum})")
        
        if not self._shutdown_requested.is_set():
            self._shutdown_requested.set()
            # Start shutdown in a separate thread to avoid blocking signal handler
            shutdown_thread = threading.Thread(
                target=self.shutdown,
                name="ShutdownThread",
                daemon=False
            )
            shutdown_thread.start()
        else:
            # Second signal = force shutdown
            self._log("Force shutdown requested!")
            self._force_shutdown.set()
        
    
    def _atexit_handler(self):
        """Called by atexit - ensures cleanup happens"""
        if self._state == ShutdownState.IDLE:
            self._log("atexit triggered, initiating shutdown...")
            self.shutdown()
    
    def _emergency_shutdown(self):
        """Emergency shutdown when normal shutdown fails"""
        self._log("=" * 60)
        self._log("EMERGENCY SHUTDOWN INITIATED")
        self._log("=" * 60)
        
        # Give threads a moment to finish
        time.sleep(self._emergency_exit_delay)
        
        # Force exit
        self._log("Force exiting...")
        os._exit(1)
    
    def _report_shutdown_results(self, total_time: float):
        """Report shutdown execution results"""
        self._log("")
        self._log("Shutdown Results:")
        self._log(f"  Total time: {total_time:.3f}s")
        self._log(f"  Tasks executed: {len(self._executed_tasks)}")
        self._log(f"  Tasks failed: {len(self._failed_tasks)}")
        
        if self._failed_tasks:
            self._log("")
            self._log("Failed Tasks:")
            for task, error in self._failed_tasks:
                self._log(f"  - {task.name}: {error}")
    
    def _log(self, message: str):
        """Internal logging"""
        if self._verbose:
            print(f"[ShutdownHandler] {message}", file=sys.stderr)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current shutdown handler status"""
        with self._tasks_lock:
            return {
                'state': self._state.name,
                'registered_tasks': len(self._tasks),
                'executed_tasks': len(self._executed_tasks),
                'failed_tasks': len(self._failed_tasks),
                'groups': {name: len(tasks) for name, tasks in self._task_groups.items()},
                'shutdown_requested': self._shutdown_requested.is_set(),
                'force_shutdown': self._force_shutdown.is_set()
            }
    
    def set_verbose(self, verbose: bool):
        """Enable/disable verbose logging"""
        self._verbose = verbose
    
    def set_max_shutdown_time(self, seconds: float):
        """Set maximum total shutdown time"""
        self._max_total_time = seconds


    #MARK: register handlers
    def register(
        self,
        callback: Callable,
        name: str,
        priority: int = ShutdownPriority.DEFAULT_PRIORITY.value,
        timeout: float = 5.0,
        critical: bool = False,
        group: Optional[str] = None,
        *args,
        **kwargs
    ) -> ShutdownTask:
        """
        Register a shutdown callback
        
        Args:
            callback: Function to call during shutdown
            name: Descriptive name for logging
            priority: Execution priority (lower = earlier)
            timeout: Maximum execution time in seconds
            critical: If True, shutdown fails if this task fails
            group: Optional group name for bulk operations
            *args, **kwargs: Arguments to pass to callback
            
        Returns:
            ShutdownTask object for tracking
        """
        with self._tasks_lock:
            if self._state != ShutdownState.IDLE:
                raise RuntimeError(f"Cannot register during shutdown (state: {self._state})")
            
            if priority < ShutdownPriority.MIN_PRIORITY.value or priority > ShutdownPriority.MAX_PRIORITY.value:
                raise ValueError(f"Invalid priority: {priority}")
            
            task = ShutdownTask(
                priority=priority,
                name=name,
                callback=callback,
                timeout=timeout,
                critical=critical,
                args=args,
                kwargs=kwargs
            )
            
            self._tasks.append(task)
            
            if group:
                self._task_groups[group].append(task)
            
            self._log(f"Registered: {name} (priority={priority}, group={group})")
            return task
    
    def unregister(self, task: ShutdownTask) -> bool:
        """
        Unregister a shutdown task
        
        Args:
            task: Task to remove
            
        Returns:
            True if task was found and removed
        """
        with self._tasks_lock:
            try:
                self._tasks.remove(task)
                # Remove from groups
                for group_tasks in self._task_groups.values():
                    if task in group_tasks:
                        group_tasks.remove(task)
                self._log(f"Unregistered: {task.name}")
                return True
            except ValueError:
                return False
    
    def unregister_group(self, group: str) -> int:
        """
        Unregister all tasks in a group
        
        Args:
            group: Group name
            
        Returns:
            Number of tasks removed
        """
        with self._tasks_lock:
            if group not in self._task_groups:
                return 0
            
            tasks = self._task_groups[group]
            count = 0
            for task in tasks:
                if task in self._tasks:
                    self._tasks.remove(task)
                    count += 1
            
            del self._task_groups[group]
            self._log(f"Unregistered group '{group}': {count} tasks")
            return count
    
    def shutdown(self, timeout: Optional[float] = None):
        """
        Execute shutdown sequence
        
        Args:
            timeout: Override default maximum shutdown time
            
        exit:
            exit from the application onces the shutdown completes 
        """
        with self._state_lock:
            if self._state != ShutdownState.IDLE:
                self._log(f"Shutdown already in progress (state: {self._state})")
                return self._state == ShutdownState.COMPLETED
            
            self._state = ShutdownState.INITIATED
        
        self._log("=" * 60)
        self._log("INITIATING SHUTDOWN SEQUENCE")
        self._log("=" * 60)
        
        start_time = time.time()
        max_time = timeout or self._max_total_time
        
        try:
            with self._state_lock:
                self._state = ShutdownState.IN_PROGRESS
            
            # Sort tasks by priority (lower = earlier)
            with self._tasks_lock:
                sorted_tasks = sorted(self._tasks)
            
            self._log(f"Executing {len(sorted_tasks)} shutdown tasks...")
            
            # Execute tasks
            for task in sorted_tasks:
                # Check if we've exceeded total time
                elapsed = time.time() - start_time
                if elapsed >= max_time:
                    self._log(f"WARNING: Shutdown timeout ({max_time}s) exceeded!")
                    break
                
                # Check for force shutdown
                if self._force_shutdown.is_set():
                    self._log("Force shutdown requested, aborting remaining tasks!")
                    break
                
                # Execute task
                success = self._execute_task(task)
                self._executed_tasks.append((task, success))
                
                if not success and task.critical:
                    self._log(f"CRITICAL TASK FAILED: {task.name}")
                    raise RuntimeError(f"Critical shutdown task failed: {task.name}")
            
            # Report results
            self._report_shutdown_results(time.time() - start_time)
            
            with self._state_lock:
                self._state = ShutdownState.COMPLETED
            
            self._log("=" * 60)
            self._log("SHUTDOWN COMPLETED SUCCESSFULLY")
            self._log("=" * 60)
            
            return True
            
        except Exception as e:
            with self._state_lock:
                self._state = ShutdownState.FAILED
            
            self._log(f"SHUTDOWN FAILED: {e}")
            # will exit from application
            # Emergency cleanup
            self._emergency_shutdown()
        
    #MARK: task executor
    def _execute_task(self, task: ShutdownTask) -> bool:
        """
        Execute a single shutdown task with timeout protection
        
        Args:
            task: Task to execute
            
        Returns:
            True if task completed successfully
        """
        self._log(f"Executing: {task.name} (priority={task.priority}, timeout={task.timeout}s)")
        
        start_time = time.time()
        result_container = {'result': None, 'error': None, 'completed': False}
        
        def task_wrapper():
            try:
                result = task.callback(*task.args, **task.kwargs)
                result_container['result'] = result
                result_container['completed'] = True
            except Exception as e:
                traceback.print_exc()
                result_container['error'] = e
                result_container['completed'] = False
        
        # Execute in separate thread with timeout
        thread = threading.Thread(target=task_wrapper, name=f"Shutdown-{task.name}")
        thread.daemon = False  # Don't make daemon - we want to wait
        thread.start()
        thread.join(timeout=task.timeout)
        
        task.execution_time = time.time() - start_time
        
        if thread.is_alive():
            # Task timed out
            self._log(f"  TIMEOUT: {task.name} exceeded {task.timeout}s")
            task.error = TimeoutError(f"Task exceeded {task.timeout}s timeout")
            self._failed_tasks.append((task, task.error))
            return False
        
        if result_container['error']:
            # Task raised exception
            self._log(f"  ERROR: {task.name}: {result_container['error']}")
            task.error = result_container['error']
            self._failed_tasks.append((task, task.error))
            return False
        
        if result_container['completed']:
            # Task completed successfully
            self._log(f"  SUCCESS: {task.name} ({task.execution_time:.3f}s)")
            task.completed = True
            task.result = result_container['result']
            return True
        
        return False
    


# Global instance
_shutdown_handler = ShutdownHandler()


# Convenience functions
def register_shutdown(
    callback: Callable,
    name: str,
    priority: ShutdownPriority = ShutdownPriority.DEFAULT_PRIORITY,
    timeout: float = 5.0,
    critical: bool = False,
    group: Optional[str] = None,
    *args,
    **kwargs
) -> ShutdownTask:
    """Register a shutdown callback (convenience function)"""
    return _shutdown_handler.register(
        callback, name, priority.value, timeout, critical, group, *args, **kwargs
    )


def unregister_shutdown(task: ShutdownTask) -> bool:
    """Unregister a shutdown task"""
    return _shutdown_handler.unregister(task)


def unregister_group(group: str) -> int:
    """Unregister all tasks in a group"""
    return _shutdown_handler.unregister_group(group)


def trigger_shutdown(timeout: Optional[float] = None) -> bool:
    """Manually trigger shutdown"""
    return _shutdown_handler.shutdown(timeout)


def get_shutdown_status() -> Dict[str, Any]:
    """Get shutdown handler status"""
    return _shutdown_handler.get_status()


# Example integration with your existing modules
if __name__ == "__main__":
    import os
    
    # Example: Register cleanup functions with proper priorities
    
    def cleanup_event_loops():
        print("Destroying event loop managers...")
        # from async_exec import EventLoopManager
        # EventLoopManager.destroy_loop_mangers()
        time.sleep(0.5)
    
    def cleanup_file_handlers():
        print("Flushing and closing file handlers...")
        # from file_handler import flush_all, close_all
        # flush_all()
        # close_all()
        time.sleep(0.3)
    
    def cleanup_logging():
        print("Shutting down logging system...")
        # from logger import shutdown_logging
        # shutdown_logging()
        time.sleep(0.2)
    
    def cleanup_temp_files():
        print("Removing temporary files...")
        time.sleep(0.1)
    
    # Register in priority order
    register_shutdown(
        cleanup_logging,
        name="LoggingSystem",
        priority=ShutdownPriority.LOGGING.value,
        timeout=5.0,
        critical=False,
        group="infrastructure"
    )
    
    register_shutdown(
        cleanup_file_handlers,
        name="FileHandlers",
        priority=ShutdownPriority.FILE_HANDLERS.value,
        timeout=10.0,
        critical=True,
        group="resources"
    )
    
    register_shutdown(
        cleanup_event_loops,
        name="EventLoops",
        priority=ShutdownPriority.EVENT_LOOP.value,
        timeout=15.0,
        critical=True,
        group="infrastructure"
    )
    
    register_shutdown(
        cleanup_temp_files,
        name="TempFiles",
        priority=ShutdownPriority.TEMP_FILES.value,
        timeout=2.0,
        group="cleanup"
    )
    
    print("Shutdown handler initialized with 4 tasks")
    print("Status:", get_shutdown_status())
    print("\nPress Ctrl+C to trigger shutdown, or wait 3 seconds...")
    
    time.sleep(3)
    
    print("\nTriggering shutdown...")
    success = trigger_shutdown()
    
    print(f"\nShutdown {'succeeded' if success else 'failed'}")
    print("Final status:", get_shutdown_status())