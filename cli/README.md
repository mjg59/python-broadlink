Command line interface for python-broadlink
===========================================

This is a command line interface for the python-broadlink API.


Requirements
------------
You need to install the module first:
```
pip3 install broadlink
```

Installation
-----------
Download "broadlink_cli" and "broadlink_discovery".


Programs
--------
* broadlink_discovery: Discover Broadlink devices connected to the local network.

* broadlink_cli: Send commands and query the Broadlink device.


Device specification formats
----------------------------

Using separate parameters for each information:
```
broadlink_cli --type 0x2712 --host 1.1.1.1 --mac aaaaaaaaaa --temp
```

Using all parameters as a single argument:
```
broadlink_cli --device "0x2712 1.1.1.1 aaaaaaaaaa" --temp
```

Using file with parameters:
```
broadlink_cli --device @BEDROOM.device --temp
```
This is prefered as the configuration is stored in a file and you can change
it later to point to a different device.

Example usage
-------------

### Common commands

#### Join device to the Wi-Fi network
```
broadlink_cli --joinwifi SSID PASSWORD
```

#### Discover devices connected to the local network
```
broadlink_discovery
```

### Universal remotes

#### Learn IR code and show at console
```
broadlink_cli --device @BEDROOM.device --learn 
```

#### Learn RF code and show at console
```
broadlink_cli --device @BEDROOM.device --rfscanlearn
```

#### Learn IR code and save to file
```
broadlink_cli --device @BEDROOM.device --learnfile LG-TV.power
```

#### Learn RF code and save to file
```
broadlink_cli --device @BEDROOM.device --rfscanlearn --learnfile LG-TV.power
```

#### Send code
```
broadlink_cli --device @BEDROOM.device --send DATA
```

#### Send code from file
```
broadlink_cli --device @BEDROOM.device --send @LG-TV.power
```

#### Check temperature
```
broadlink_cli --device @BEDROOM.device --temperature
```

#### Check humidity
```
broadlink_cli --device @BEDROOM.device --humidity
```

### Smart plugs

#### Turn on
```
broadlink_cli --device @BEDROOM.device --turnon
```

#### Turn off
```
broadlink_cli --device @BEDROOM.device --turnoff
```

#### Turn on nightlight
```
broadlink_cli --device @BEDROOM.device --turnnlon
```

#### Turn off nightlight
```
broadlink_cli --device @BEDROOM.device --turnnloff
```

#### Check power state
```
broadlink_cli --device @BEDROOM.device --check
```

#### Check nightlight state
```
broadlink_cli --device @BEDROOM.device --checknl
```

#### Check power consumption
```
broadlink_cli --device @BEDROOM.device --energy
```
