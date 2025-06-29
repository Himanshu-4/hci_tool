@critical

-------------- main in hci library 
----> evt handler have different codes like LE_META event and they have subcode after that 
----> status complete event should be handled in all the status complete and command complete event

1. async file handler, run this handler in event loop, file handler should have minmal latency in fileIO and be very responsive, the file handler should run in the evt loop
2. event loop library of  creating new event loop and handle async codes, handle callbacks, stop, close, destroy evt loop with destroy callbacks of all task are running on the event loop, destroying task, loop manager
3. async transport layer that will handle the serial api or other transport api in async manner to make ui responsive, the higher level layer will schedule all the transport api of UART, USB, SDIO to evt loop and manages it 
3.1. tran lib for handling all the transport stuff and callbacks and run properly [after that integration testing should be done to see if connect, disconnects callbacks are working properly or not ]
4. async logger library the library will be used to handle the modules logging 
5. app.conf file for handling the app related configuration and that also we can enable, disable, configure logger objects of other module, for module level logging we need to first allow the module, and then max_log level, streams like file, console , log window, submodule, parent-child relationship, dependencies
6. creating a throughput_test.py, HID, A2DP, SCO, tests
7. checking if all the module logging on terminal, files are proper


===================== application run time analysis is pending, what impact it put on system in terms on memory and CPU utilistation ========================




@Exceptions

1. when closing the HCI subwindow the delte instance not getting called so have to check why it's not deleted properly or delete called properly
- Resolved --> the Qt objects are automatically deleted by the Qt manager and handled by the delete_later to free mem and resources. so we not have to manually handle the delete process. but we can add cleanup methods to clean the instances and acquired resources after object is closed or delete.

2. make sure that all the objects that deleted should free the memory or aka memeory while running the app should not increase gracefully or beyond a threshold
- we are not sure that the Objects deleted or not 



@Feature implementation & pending 
2. implement more event UI and regisgter the event UI with respoect to the Evt_class as a object 




@pending things in  v1.0-alpha (date -> 30 June)
1. Yaml config parser include and inheritance not working have to check at last should create a final config based on all files
2. File logger have to check and FileIO logger should work properly, means have to check file io ops and rate(multiple io reqs handle properly)
3. Log_window logger should work perfectly with rate limiter and _handlers of loggers 
4. logger module check thoroughly and also logging  againts diffrent configurations and rate's 
5. transport layer should be completed with respect to async support with reader and writer asyncally and transport handles all method with a bounded latency.
6. check the transport auto disconnect feature and handling of connection, disconnect, read, write, etc.
7. transport connection and UI window handling read callback should emit evt_factory signal for handling of UI events with respect to evt application thread.
8. File saver and logger with respect to events, commands, logs, etc.
9. make throughput window UI with respect to TX/RX
10. complete the throughput test feature  with HCI/acl module and integrate with the throughput window 