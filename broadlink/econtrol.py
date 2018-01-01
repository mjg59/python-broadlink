from __init__ import setup, discover

# -----------------------------------------------------------------
# initi program: 
setup('Chuck_Norris', '8ruceL33+', 3)
devices = discover(timeout=5)
print "Found %d" % len(devices)
#print "device SPMini2: Sp2 class"
#if len(devices) > 0:
#  # devices[0].check_power()
#  devices[0].flip_the_switch(1)