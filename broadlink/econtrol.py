#!/usr/bin/python

from __init__ import setup, discover
import time

# -----------------------------------------------------------------
# initi program: 

print "Call discovery..."
devices = discover(timeout=5)
print "Found %d" % len(devices)
#print "device SPMini2: Sp2 class"

if len(devices) > 0:
	#if devices[0].get_type == "SP2Mini2":
	print "device type %s" % devices[0].get_type
	#print "device SPMini2: Sp2 class"
	print "Call Auth"
	devices[0].auth()
#	print "Call Learning"
#	devices[0].enter_learning()
#	ir_packet = devices[0].check_data()
#	devices[0].send_data(ir_packet)
	print "Call set power"
	devices[0].set_power(1)
	print "Call check power"
	devices[0].check_power()

	print "sleep..."
	time.sleep(5)
	print "Call set power"
	devices[0].set_power(0)
	print "Call check power"
	devices[0].check_power()
