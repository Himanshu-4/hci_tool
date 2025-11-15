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




@ ============ Feature for Alpha 1.0 build

1. reietrate the logger stuff as the handler everytime we have to create new handlers for the module whoever is using it 
2. reiterate the logger.py stuff as logger has to register new _handler every time created, also to check the multi level logger like a.b.c  (handles by logging library internally )
- but we have to define that thing in YML configuration under parent name 

3. go through the file_handler again as to check if we are increasing CPU intervention or not as for files we want it to make IO based system so thread can do other things 

4. 1. same thing for the transport library as transport we have IO operations and we want to maximise the thread effieciency by scheduling multiple IO task 
4. 2. the tranport layer also consits of the flow control mechanism for both task and ACL data so as to manage the controller efficently and Host based flow is disabled always.
4. 3. transport layer will argue if from user we are getting too much data but due to flow restrictions we are not able to send it to controller 
4. 4. at last transport also has to trigger the callbacks, control the UI elements or can also also execute some code for other modules also like logger, etc.
4. 5. we need to make things like what callbacks or flow to executed 
        - when connected to the device 
        - diconnected from the device
        - got error from the device 
        - BUS error or something 
        - app exit or need to free up resources


5. at last we will check the system performance and efficiency [how_much_cpu_usage_is_there]


