#!/usr/bin/python

from __init__ import setup, discover
import time

# Notice:
# The divices have to be pre-configured and associated 
# to the local Wlan before running this test

# usage:
# python sp2mini2_test.py

print "Call discovery..."
devices = discover(timeout=5)
print "Found %d" % len(devices)

if len(devices) > 0:
	print "device type %s" % devices[0].get_type

	print "Call Auth"
	devices[0].auth()

	print "Call set power"
	devices[0].set_power(1)

	print "Call check power"
	devices[0].check_power()

	print "sleep 5 s..."
	time.sleep(5)
	
	print "Call set power"
	devices[0].set_power(0)
	
	print "Call check power"
	devices[0].check_power()
