Import from mjg59/python-broadlink

Added support for livolo switch to send livolo signal via broadlink.

Example use(include python broadlink below)
```
import livolo
livolo_send( 6500  , "Off")
livolo_send( 6500 , "On")
```
How to use
Assume 6500 is your remote id 

You need to set livolo switch to learn mode then send btn1 and hear a beep on the device
```
livolo_send( 6500  , "btn1")
```
send again your light should toggle

You need to set livolo switch to learn mode then send On and hear a beep on the device
```
livolo_send( 6500  , "on")
```
send again your switch should turn on if off. Nothing happen if already on

Now you can try turn off the switch by sending

```
livolo_send( 6500  , "off")
```

See demo file for sample.


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

Set power state on a SmartPlug SP2/SP3:
```
devices[0].set_power(True)
```

Check power state on a SmartPlug:
```
state = devices[0].check_power()
```
