"""
FileIO Integration Example
This example demonstrates how to integrate the enhanced FileIO system
with the logger and use it in a real application.
"""

import time
import threading
from datetime import datetime
from typing import Dict, Any

# Import the enhanced file handler and logger modules
from ..utils.file_handler import (
    FileIO, AsyncFileHandler, FileIOLogger, FileIOEvent, 
    FileIOCallbackData, FileIOMode, init as init_filehandler,
    register_file, get_handler, cleanup
)
from ..utils.logger import (
    LoggerManager, FileIOLogHandler, initLogger, shutdownLogger
)


class ApplicationWithFileIO:
    """
    Example application that demonstrates FileIO usage with callbacks
    and non-blocking operations.
    """
    
    def __init__(self):
        self.running = False
        self.stats = {
            'files_written': 0,
            'bytes_written': 0,
            'errors': 0,
            'flushes': 0
        }
        
        # Initialize file handling
        init_filehandler()
        
        # Setup application logger with FileIO
        self.logger = LoggerManager.get_logger(
            "Application",
            level="INFO",
            to_console=True,
            to_file=True,
            log_file="logs/application.log",
            prepend="[APP]",
            use_fileio=True,
            max_buffer_size=20,
            auto_flush_interval=1.0
        )
        
        # Register file handlers for different purposes
        self.setup_file_handlers()
        
        self.logger.info("Application initialized with FileIO")
    
    def setup_file_handlers(self):
        """Setup various file handlers for the application"""
        
        # Data logger
        self.data_handler = register_file(
            "data_log", 
            "logs/data.log",
            max_size_bytes=1024*1024,  # 1MB
            max_files_limit=5,
            buffer_size=100
        )
        
        # Error logger
        self.error_handler = register_file(
            "error_log",
            "logs/errors.log", 
            max_size_bytes=512*1024,  # 512KB
            max_files_limit=3,
            buffer_size=50
        )
        
        # Performance metrics logger
        self.metrics_handler = register_file(
            "metrics_log",
            "logs/metrics.log",
            buffer_size=25
        )
        
        # Setup callbacks for monitoring
        self.data_handler.add_callback('write', self.on_data_write)
        self.data_handler.add_callback('error', self.on_file_error)
        self.data_handler.add_callback('flush', self.on_flush)
        self.data_handler.add_callback('rotate', self.on_file_rotate)
        
        self.error_handler.add_callback('error', self.on_file_error)
        self.metrics_handler.add_callback('error', self.on_file_error)
        
        self.logger.info("File handlers setup completed")
    
    def on_data_write(self, bytes_written: int):
        """Callback for successful data writes"""
        self.stats['files_written'] += 1
        self.stats['bytes_written'] += bytes_written
        
        # Log every 100 writes
        if self.stats['files_written'] % 100 == 0:
            self.logger.debug(f"Written {self.stats['files_written']} entries, "
                            f"{self.stats['bytes_written']} bytes total")
    
    def on_file_error(self, error: Exception):
        """Callback for file operation errors"""
        self.stats['errors'] += 1
        self.logger.error(f"FileIO error occurred: {error}")
        
        # Write to error log (non-blocking)
        error_msg = f"{datetime.now()}: {str(error)}"
        self.error_handler.write(error_msg)
    
    def on_flush(self):
        """Callback for file flushes"""
        self.stats['flushes'] += 1
    
    def on_file_rotate(self, file_path: str):
        """Callback for file rotation"""
        self.logger.info(f"File rotated: {file_path}")
        
        # Log rotation event
        rotation_msg = f"{datetime.now()}: File rotated - {file_path}"
        self.metrics_handler.write(rotation_msg)
    
    def simulate_data_processing(self):
        """Simulate data processing with file operations"""
        self.logger.info("Starting data processing simulation")
        
        # Simulate processing 1000 data items
        for i in range(1000):
            # Simulate some processing time
            time.sleep(0.01)
            
            # Log data entry (non-blocking)
            data_entry = f"Data item {i}: processed at {datetime.now()}"
            self.data_handler.write(data_entry)
            
            # Log metrics every 50 items
            if i % 50 == 0:
                metrics_entry = f"Processed {i} items, memory usage: {i*100}KB"
                self.metrics_handler.write(metrics_entry)
                
                # Application log
                self.logger.info(f"Processed {i}/1000 items")
            
            # Simulate occasional errors
            if i % 150 == 0 and i > 0:
                error_msg = f"Simulated error at item {i}"
                self.error_handler.write(f"{datetime.now()}: {error_msg}")
        
        self.logger.info("Data processing simulation completed")
    
    def demonstrate_blocking_vs_nonblocking(self):
        """Demonstrate the difference between blocking and non-blocking operations"""
        self.logger.info("Demonstrating blocking vs non-blocking operations")
        
        # Create a dedicated FileIO instance for this demo
        demo_file = FileIO("demo_operations.txt", FileIOMode.WRITE)
        
        # Setup callback to track completion
        completion_events = []
        
        def on_write_complete(callback_data: FileIOCallbackData):
            completion_events.append(f"Write completed: {len(callback_data.data)} chars")
        
        demo_file.add_callback(FileIOEvent.WRITE, on_write_complete)
        demo_file.add_callback(FileIOEvent.ERROR, lambda cb: print(f"Error: {cb.error}"))
        
        # Open the file
        demo_file.open_wait()
        
        # Non-blocking operations
        start_time = time.time()
        self.logger.info("Starting non-blocking writes...")
        
        # Queue up multiple writes (non-blocking)
        for i in range(10):
            demo_file.write(f"Non-blocking write {i}\n")
        
        non_blocking_time = time.time() - start_time
        self.logger.info(f"Non-blocking writes queued in {non_blocking_time:.4f} seconds")
        
        # Wait a bit for async operations to complete
        time.sleep(0.5)
        
        # Blocking operations for comparison
        start_time = time.time()
        self.logger.info("Starting blocking writes...")
        
        for i in range(10):
            demo_file.write_wait(f"Blocking write {i}\n")
        
        blocking_time = time.time() - start_time
        self.logger.info(f"Blocking writes completed in {blocking_time:.4f} seconds")
        
        # Close the demo file
        demo_file.close_wait()
        
        self.logger.info(f"Completion events received: {len(completion_events)}")
    
    def run(self):
        """Run the application"""
        self.running = True
        self.logger.info("Application started")
        
        try:
            # Demonstrate non-blocking vs blocking operations
            self.demonstrate_blocking_vs_nonblocking()
            
            # Run data processing simulation
            self.simulate_data_processing()
            
            # Wait for any pending operations
            time.sleep(2)
            
            # Flush all handlers
            self.logger.info("Flushing all file handlers...")
            self.data_handler.flush_wait()
            self.error_handler.flush_wait()
            self.metrics_handler.flush_wait()
            
            # Print final statistics
            self.print_statistics()
            
        except Exception as e:
            self.logger.error(f"Application error: {e}", exc_info=True)
        finally:
            self.shutdown()
    
    def print_statistics(self):
        """Print application statistics"""
        self.logger.info("=== Application Statistics ===")
        self.logger.info(f"Files written: {self.stats['files_written']}")
        self.logger.info(f"Total bytes written: {self.stats['bytes_written']}")
        self.logger.info(f"Errors encountered: {self.stats['errors']}")
        self.logger.info(f"Flushes performed: {self.stats['flushes']}")
    
    def shutdown(self):
        """Shutdown the application"""
        if not self.running:
            return
        
        self.logger.info("Shutting down application...")
        self.running = False
        
        # Shutdown loggers
        LoggerManager.shutdown_all()
        
        # Cleanup file handlers
        cleanup()
        
        print("Application shutdown completed")


class PerformanceMonitor:
    """
    A simple performance monitoring class that uses FileIO
    to log performance metrics without blocking the main application.
    """
    
    def __init__(self):
        self.metrics_file = FileIO("logs/performance.log", FileIOMode.APPEND)
        self.metrics_file.open_wait()
        
        # Setup callbacks
        self.metrics_file.add_callback(FileIOEvent.ERROR, self.on_error)
        
        self.start_time = time.time()
        self.last_log_time = self.start_time
        
    def on_error(self, callback_data: FileIOCallbackData):
        """Handle performance logging errors"""
        print(f"Performance monitor error: {callback_data.error}")
    
    def log_metric(self, metric_name: str, value: Any):
        """Log a performance metric asynchronously"""
        current_time = time.time()
        elapsed = current_time - self.start_time
        interval = current_time - self.last_log_time
        
        log_entry = f"{datetime.now()}: {metric_name}={value}, elapsed={elapsed:.2f}s, interval={interval:.2f}s\n"
        
        # Non-blocking write
        self.metrics_file.write(log_entry)
        self.last_log_time = current_time
    
    def close(self):
        """Close the performance monitor"""
        self.metrics_file.flush_wait()
        self.metrics_file.close_wait()


def demonstrate_concurrent_fileio():
    """Demonstrate concurrent FileIO operations with multiple threads"""
    print("\n=== Demonstrating Concurrent FileIO ===")
    
    # Create multiple FileIO instances for different threads
    file_handlers = []
    threads = []
    
    def worker_thread(thread_id: int, num_operations: int):
        """Worker thread that performs file operations"""
        file_io = FileIO(f"logs/thread_{thread_id}.log", FileIOMode.WRITE)
        file_handlers.append(file_io)
        
        try:
            file_io.open_wait()
            
            for i in range(num_operations):
                message = f"Thread {thread_id}, Operation {i}, Time: {datetime.now()}\n"
                file_io.write(message)  # Non-blocking
                time.sleep(0.01)  # Simulate some work
            
            file_io.flush_wait()  # Ensure all writes complete
            
        except Exception as e:
            print(f"Thread {thread_id} error: {e}")
        finally:
            file_io.close_wait()
    
    # Start multiple worker threads
    num_threads = 5
    operations_per_thread = 20
    
    for i in range(num_threads):
        thread = threading.Thread(
            target=worker_thread, 
            args=(i, operations_per_thread)
        )
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    print(f"Concurrent FileIO demonstration completed with {num_threads} threads")


def main():
    """Main function to run the examples"""
    print("FileIO Integration Example")
    print("=" * 50)
    
    try:
        # Create and run the application
        app = ApplicationWithFileIO()
        app.run()
        
        # Demonstrate concurrent operations
        demonstrate_concurrent_fileio()
        
        # Demonstrate performance monitoring
        print("\n=== Performance Monitoring Demo ===")
        monitor = PerformanceMonitor()
        
        for i in range(10):
            monitor.log_metric("cpu_usage", f"{50 + i * 2}%")
            monitor.log_metric("memory_usage", f"{1000 + i * 100}MB")
            monitor.log_metric("disk_io", f"{i * 50}KB/s")
            time.sleep(0.1)
        
        monitor.close()
        
        print("\nAll examples completed successfully!")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()