import broadlink

dev = broadlink.discover()
dev.auth()


print('Device: ' + dev.type)
print('Temperature: '+ str(dev.get_temp()) + 'C')
print('Test switch to auto mode: ' + str(dev.switch_to_auto()) )

