import broadlink

devices = broadlink.discover(timeout=1)

# Get first device (assume there is only 1)
dev = devices[0]

print(dev.type)

dev.auth()

print(dev.get_temp())

