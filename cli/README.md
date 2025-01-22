# Command line interface for python-broadlink

This is a command line interface for the python-broadlink API.

## Requirements

You need to install the module first:

```shell
pip3 install broadlink
```

broadlink_cli should then be in your path

## Programs

* broadlink_cli: Send commands and query the Broadlink device.

## Device specification formats

Using separate parameters for each information:

```shell
broadlink_cli --type 0x2712 --host 1.1.1.1 --mac aaaaaaaaaa --temp
```

Using all parameters as a single argument:

```shell
broadlink_cli --device "0x2712 1.1.1.1 aaaaaaaaaa" --temp
```

Using file with parameters:

```shell
broadlink_cli --device @BEDROOM.device --temp
```

This is prefered as the configuration is stored in a file and you can change
it later to point to a different device.

## Example usage

### Common commands

#### Join device to the Wi-Fi network

```shell
broadlink_cli --joinwifi SSID PASSWORD
```

#### Discover devices connected to the local network

```shell
broadlink_discovery
```

### Universal remotes

#### Learn IR code and show at console

```shell
broadlink_cli --device @BEDROOM.device --irlearn 
```

#### Learn RF code and show at console

```shell
broadlink_cli --device @BEDROOM.device --rflearn
```

#### Learn IR code and save to file

```shell
broadlink_cli --device @BEDROOM.device --learnfile LG-TV.power
```

#### Learn RF code and save to file

```shell
broadlink_cli --device @BEDROOM.device --rflearn --learnfile LG-TV.power
```

#### Send code

```shell
broadlink_cli --device @BEDROOM.device --send DATA
```

#### Send code from file

```shell
broadlink_cli --device @BEDROOM.device --send @LG-TV.power
```

#### Check temperature

```shell
broadlink_cli --device @BEDROOM.device --temperature
```

#### Check humidity

```shell
broadlink_cli --device @BEDROOM.device --humidity
```

### Smart plugs

#### Turn on

```shell
broadlink_cli --device @BEDROOM.device --turnon
```

#### Turn off

```shell
broadlink_cli --device @BEDROOM.device --turnoff
```

#### Turn on nightlight

```shell
broadlink_cli --device @BEDROOM.device --turnnlon
```

#### Turn off nightlight

```shell
broadlink_cli --device @BEDROOM.device --turnnloff
```

#### Check power state

```shell
broadlink_cli --device @BEDROOM.device --check
```

#### Check nightlight state

```shell
broadlink_cli --device @BEDROOM.device --checknl
```

#### Check power consumption

```shell
broadlink_cli --device @BEDROOM.device --energy
```
