@critical

-------------- main in hci library 
----> evt handler have different codes like LE_META event and they have subcode after that 
----> status complete event should be handled in all the status complete and command complete event

1. async file handler, run this handler in event loop, file handler should have minmal latency in fileIO and be very responsive
2. event loop library of  creating new event loop and handle async codes, handle callbacks, stop, close, destroy evt loop with destroy callbacks of all task are running on the event loop
3. async transport layer that will handle the serial api or other transport api in async manner to make ui responsive 
4. async logger library the library will be used to handle the modules logging 
5. app.conf file for handling the app related configuration and that also we can enable, disable, configure logger objects of other module
6. creating a throughput_test.py, HID, A2DP, SCO, tests
7. checking if all the module logging on terminal, files are proper


===================== application run time analysis is pending, what impact it put on system in terms on memory and CPU utilistation




@Exceptions

1. when closing the HCI subwindow the delte instance not getting called so have to check why it's not deleted properly or delete called properly

2. make sure that all the objects that deleted should free the memory or aka memeory while running the app should not increase gracefully or beyond a threshold
