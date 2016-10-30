Python control for Broadlink RM2 IR controllers
===============================================

A simple Python API for controlling IR controllers from [Broadlink](http://www.ibroadlink.com/rm/). At present, only RM Pro (referred to as RM2 in the codebase) and A1 sensor platform devices are supported. There is currently no support for the cloud API.

Example use
-----------

Discover available devices on the local network:
```
import broadlink

devices = broadlink.discover(timeout=5)
```

Obtain the authentication key required for further communication:
```
devices[0].auth()
```

Enter learning mode:
```
devices[0].enter_learning()
```

Obtain an IR or RF packet while in learning mode:
```
ir_packet = devices[0].check_data()
```
(This will return None if the device does not have a packet to return)

Send an IR or RF packet:
```
devices[0].send_data(ir_packet)
```

Obtain temperature data from an RM2:
```
devices[0].check_temperature()
```

Obtain sensor data from an A1:
```
data = devices[0].check_sensors()
```
