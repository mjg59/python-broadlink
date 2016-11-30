import time
import sys
import livolo
import broadlink


def get_rm2():
	myrm2 = broadlink.discover(1)
	myrm2 = devices[0]
	return myrm2


def livolo_send(name, btnOnOff):
	senddatahex(livolo.btnhex( name , btnOnOff))
	return
	
def senddatahex( hex_data ):
	pad_len = 32 - (len(hex_data) - 24) % 32
	hex_data = hex_data + "".ljust(pad_len, '0')
	myrm2.send_data(hex_data.decode('hex'))
	return
  
  
myrm2 = get_rm2()


livolo_send( 6500  , "btn1") #use this to teach the device for toggle and off use
livolo_send( 6500 , "On")    #use this to emulate scene
livolo_send( 6500  , "Off")
