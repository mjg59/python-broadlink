Python control for Broadlink RM2, RM3 and RM4 series controllers
===============================================

A simple Python API for controlling IR/RF controllers from [Broadlink](http://www.ibroadlink.com/rm/). At present, the following devices are currently supported:

* RM Pro (referred to as RM2 in the codebase)
* A1 sensor platform devices are supported
* RM3 mini IR blaster
* RM4 and RM4C mini blasters

There is currently no support for the cloud API.

Example use
-----------

Setup a new device on your local wireless network:

1. Put the device into AP Mode
  1. Long press the reset button until the blue LED is blinking quickly.
  2. Long press again until blue LED is blinking slowly.
  3. Manually connect to the WiFi SSID named BroadlinkProv.
2. Run setup() and provide your ssid, network password (if secured), and set the security mode
  1. Security mode options are (0 = none, 1 = WEP, 2 = WPA1, 3 = WPA2, 4 = WPA1/2)
```
import broadlink

broadlink.setup('myssid', 'mynetworkpass', 3)
```

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

Sweep RF frequencies:
```
devices[0].sweep_frequency()
```

Cancel sweep RF frequencies:
```
devices[0].cancel_sweep_frequency()
```
Check whether a frequency has been found:
```
found = devices[0].check_frequency()
```
(This will return True if the RM has locked onto a frequency, False otherwise)

Attempt to learn an RF packet:
```
found = devices[0].find_rf_packet()
```
(This will return True if a packet has been found, False otherwise)

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

Check energy consumption on a SmartPlug:
```
state = devices[0].get_energy()
```

Set power state for S1 on a SmartPowerStrip MP1:
```
devices[0].set_power(1, True)
```

Check power state on a SmartPowerStrip:
```
state = devices[0].check_power()
```
