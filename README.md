Python control for Broadlink RM2 IR controllers
===============================================

A simple Python API for controlling IR controllers from [Broadlink](http://www.ibroadlink.com/rm/). At present, only RM Pro (referred to as RM2 in the codebase) devices are supported and only one device per network will be used. There is currently no support for the cloud API.

Example use
-----------

Discover an available device on the local network:
```
import broadlink

device = broadlink.rm2()
device.discover()
```

Obtain the authentication key required for further communication:
```
device.auth()
```

Enter learning mode:
```
device.enter_learning()
```

Obtain an IR packet while in learning mode:
```
ir_packet = device.check_data()
```
(This will return None if the device does not have a packet to return)

Send an IR packet:
```
device.send_data(ir_packet)
```
