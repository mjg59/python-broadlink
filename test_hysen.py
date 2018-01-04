import broadlink
import time

dev = broadlink.discover()
dev.auth()


print('Device: ' + dev.type)
print('Current temperature: '+ str(dev.get_temp()) + 'C')

print('Set temperature: ' + str(dev.set_temp(22.0)) )

time.sleep(10)

print('Test switch to auto mode: ' + str(dev.switch_to_auto()) )



