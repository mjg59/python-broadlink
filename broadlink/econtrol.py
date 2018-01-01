#!/usr/bin/python

from __init__ import setup, discover

# -----------------------------------------------------------------
# initi program: 
setup('Chuck_Norris', '8ruceL33+', 3)
devices = discover(timeout=5)
print "Found %d" % len(devices)
#print "device SPMini2: Sp2 class"
if len(devices) > 0:
	#if devices[0].get_type == "SP2Mini2":
	print "device type %s" % devices[0].get_type
	#print "device SPMini2: Sp2 class"
	devices[0].flip_the_switch()