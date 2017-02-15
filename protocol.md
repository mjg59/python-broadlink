Broadlink RM2 network protocol
==============================

Encryption
----------

Packets include AES-based encryption in CBC mode. The initial key is 0x09, 0x76, 0x28, 0x34, 0x3f, 0xe9, 0x9e, 0x23, 0x76, 0x5c, 0x15, 0x13, 0xac, 0xcf, 0x8b, 0x02. The IV is 0x56, 0x2e, 0x17, 0x99, 0x6d, 0x09, 0x3d, 0x28, 0xdd, 0xb3, 0xba, 0x69, 0x5a, 0x2e, 0x6f, 0x58.

Network discovery
-----------------

To discover Broadlink devices on the local network, send a 48 byte packet with the following contents:

| Offset  | Contents |
|---------|----------|
|0x00-0x07|00|
|0x08-0x0b|Current offset from GMT as a little-endian 32 bit integer|
|0x0c-0x0d|Current year as a little-endian 16 bit integer|
|0x0e|Current number of minutes past the hour|
|0x0f|Current number of hours past midnight|
|0x10|Current number of years past the century|
|0x11|Current day of the week (Monday = 0, Tuesday = 1, etc)|
|0x12|Current day in month|
|0x13|Current month|
|0x19-0x1b|Local IP address|
|0x1c-0x1d|Source port as a little-endian 16 bit integer|
|0x1e-0x1f|00|
|0x20-0x21|Checksum as a little-endian 16 bit integer|
|0x22-0x25|00|
|0x26|06|
|0x27-0x2f|00|

Send this packet as a UDP broadcast to 255.255.255.255 on port 80. Bytes 0x3a-0x40 of any unicast response will contain the MAC address of the target device.

Checksum
--------

Construct the packet and set checksum bytes to zero. Add each byte to the starting value of 0xbeaf, wrapping after 0xffff.

Command packet format
---------------------

The command packet header is 56 bytes long with the following format:

|Offset|Contents|
|------|--------|
|0x00|0x5a|
|0x01|0xa5|
|0x02|0xaa|
|0x03|0x55|
|0x04|0x5a|
|0x05|0xa5|
|0x06|0xaa|
|0x07|0x55|
|0x08-0x1f|00|
|0x20-0x21|Checksum of full packet as a little-endian 16 bit integer|
|0x22-0x23|00|
|0x24|0x2a|
|0x25|0x27|
|0x26-0x27|Command code as a little-endian 16 bit integer|
|0x28-0x29|Packet count as a little-endian 16 bit integer|
|0x2a-0x2f|Local MAC address|
|0x30-0x33|Local device ID (obtained during authentication, 00 before authentication)|
|0x34-0x35|Checksum of packet header as a little-endian 16 bit integer
|0x36-0x37|00|

The payload is appended immediately after this. The checksum at 0x34 is calculated *before* the payload is appended, and covers only the header. The checksum at 0x20 is calculated *after* the payload is appended, and covers the entire packet (including the checksum at 0x34). Therefore:

1. Generate packet header with checksum values set to 0
2. Set the checksum initialisation value to 0xbeaf and calculate the checksum of the packet header. Set 0x34-0x35 to this value.
3. Append the payload
4. Set the checksum initialisation value to 0xbeaf and calculate the checksum of the entire packet. Set 0x20-0x21 to this value.

Authorisation
-------------

You must obtain an authorisation key from the device before you can communicate. To do so, generate an 80 byte packet with the following contents:

|Offset|Contents|
|------|--------|
|0x00-0x03|00|
|0x04-0x12|A 15-digit value that represents this device. Broadlink's implementation uses the IMEI.|
|0x13|01|
|0x14-0x2c|00|
|0x2d|0x01|
|0x30-0x7f|NULL-terminated ASCII string containing the device name|

Send this payload with a command value of 0x0065. The response packet will contain an encrypted payload from byte 0x38 onwards. Decrypt this using the default key and IV. The format of the decrypted payload is:

|Offset|Contents|
|------|--------|
|0x00-0x03|Device ID|
|0x04-0x13|Device encryption key|

All further command packets must use this encryption key and device ID.

Entering learning mode
----------------------

Send the following 16 byte payload with a command value of 0x006a:

|Offset|Contents|
|------|--------|
|0x00|0x03|
|0x01-0x0f|0x00|

Reading back data from learning mode
------------------------------------

Send the following 16 byte payload with a command value of 0x006a:

|Offset|Contents|
|------|--------|
|0x00|0x04|
|0x01-0x0f|0x00|

Byte 0x22 of the response contains a little-endian 16 bit error code. If this is 0, a code has been obtained. Bytes 0x38 and onward of the response are encrypted. Decrypt them. Bytes 0x04 and onward of the decrypted payload contain the captured data.

Sending data
------------

Send the following payload with a command byte of 0x006a

|Offset|Contents|
|------|--------|
|0x00|0x02|
|0x01-0x03|0x00|
|0x04|0x26 = IR, 0xb2 for RF 433Mhz, 0xd7 for RF 315Mhz|
|0x05|repeat count, (0 = no repeat, 1 send twice, .....)|
|0x06-0x07|Length of the following data in little endian|
|0x08 ....|Pulse lengths in 32,84ms units (ms * 269 / 8192 works very well)|
|....|0x0d 0x05 at the end for IR only|

Each value is represented by one byte. If the length exceeds one byte
then it is stored big endian with a leading 0.

Example: The header for my Optoma projector is 8920 4450  
8920 * 269 / 8192 = 0x124  
4450 * 269 / 8192 = 0x92  

So the data starts with `0x00 0x1 0x24 0x92 ....`


Todo
----

* Support for other devices using the Broadlink protocol (various smart home devices)
* Figure out what the format of the data packets actually is.
