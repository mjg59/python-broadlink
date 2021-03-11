Python control for Broadlink devices
===============================================

A simple Python API for controlling Broadlink devices. At present, the following devices are supported:

- **Universal remotes**: RM home, RM mini 3, RM plus, RM pro, RM pro+, RM4 mini, RM4 pro, RM4C mini, RM4S
- **Smart plugs**: SP mini, SP mini 3, SP mini+, SP1, SP2, SP2-BR, SP2-CL, SP2-IN, SP2-UK, SP3, SP3-EU, SP3S-EU, SP3S-US, SP4L-AU, SP4L-EU, SP4L-UK, SP4M, SP4M-US
- **Power strips**: MP1-1K3S2U, MP1-1K4S, MP2
- **Wi-Fi controlled switches**: MCB1, SC1, SCB1E
- **Environment sensors**: A1
- **Alarm kits**: S2KIT
- **Light bulbs**: LB1, SB800TD

Other devices with Broadlink DNA:
- **Smart plugs**: Ankuoo NEO, Ankuoo NEO PRO, BG AHC/U-01, Efergy Ego
- **Outlets**: BG 800, BG 900
- **Curtain motors**: Dooya DT360E-45/20
- **Thermostats**: Hysen HY02B05H

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

You may need to specify `local_ip_address` or `discover_ip_address` if discovery does not return any devices.


Using your machine's IP address with `local_ip_address`
```
import broadlink

devices = broadlink.discover(timeout=5, local_ip_address='192.168.0.100')
```

Using your subnet's broadcast address with `discover_ip_address`

```
import broadlink

devices = broadlink.discover(timeout=5, discover_ip_address='192.168.0.255')
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

Set power state on a SmartPlug SP2/SP3/SP4:
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

Get state on a bulb
```
state=devices[0].get_state()
```

Set a state on a bulb
```
devices[0].set_state(pwr=0)
devices[0].set_state(pwr=1)
devices[0].set_state(brightness=75)
devices[0].set_state(bulb_colormode=0)
devices[0].set_state(blue=255)
devices[0].set_state(red=0)
devices[0].set_state(green=128)
devices[0].set_state(bulb_colormode=1)
```
