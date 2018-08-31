Command line interface for python-broadlink
===========================================

This is a command line interface for broadlink python library

Tested with BroadLink RMPRO / RM2


Requirements
------------
You should have the broadlink python installed, this can be made in many linux distributions using :
```
sudo pip install broadlink
```

Installation
-----------
Just copy this files


Programs
--------


* broadlink_discovery 
used to run the discovery in the network
this program withh show the command line parameters to be used with
broadlink_cli to select broadlink device

* broadlink_cli 
used to send commands and query the broadlink device


device specification formats
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
This is prefered as the configuration is stored in file and you can change
just a file to point to a different hardware 

Sample usage
------------

Learn commands :
```
# Learn and save to file
broadlink_cli --device @BEDROOM.device --learnfile LG-TV.power
# LEard and show at console
broadlink_cli --device @BEDROOM.device --learn 
```


Send command :
```
broadlink_cli --device @BEDROOM.device --send @LG-TV.power
broadlink_cli --device @BEDROOM.device --send ....datafromlearncommand...
```

Get Temperature :
```
broadlink_cli --device @BEDROOM.device --temperature
```

Get Energy Consumption (For a SmartPlug) :
```
broadlink_cli --device @BEDROOM.device --energy
```
