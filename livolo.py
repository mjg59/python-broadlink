#!/usr/bin/env python
# -*- coding: utf-8 -*-
#livolo compatible plugin

import re

#class livolo:
def get_name_hex(name):
	name_int = int(name)
	name_str = ("{0:b}".format(name_int)).rjust(16,'0')
	name_str = re.sub(r"0", "0606", name_str)
	name_str = re.sub(r"1", "0c", name_str)
	return name_str

def get_btn_hex(btnOnOff):
	btn_choices = {
					'btn1' : 0,
					'btn2' : 96,
					'btn3' : 120,
					'btn4' : 24,
					'btn5' : 108,
					'btn6' : 80,
					'btn7' : 48,
					'btn8' : 12,
					'btn9' : 72,  #second btn 5
					'btn10': 40, #default pairing
					'scn1' : 90,
					'on'   : 90, #Use scene 1 to send on
					'off'  : 106 #All off. Use all off send off
					
	}
	btn_int = btn_choices.get(btnOnOff, 0)
	btn_str = ("{0:b}".format(btn_int)).rjust(7,'0')   #padding 0 infront of binary
	btn_str = re.sub(r"0", "0606", btn_str)            #replace binary to broadlink code
	btn_str = re.sub(r"1", "0c", btn_str)			   #replace binary to broadlink code
	return  btn_str
	
def btnhex(name,btnOnOff):

	# keycodes #1: 0, #2: 96, #3: 120, #4: 24, #5: 80, #6: 48, #7: 108, #8: 12, #9: 72; #10: 40, #OFF: 106
	# real remote IDs: 6400; 19303; 23783
	# tested "virtual" remote IDs: 10550; 8500; 7400
	btnOnOff = btnOnOff.lower()
	header = "b280260013"
	
	hex_data = header + get_name_hex(name) + get_btn_hex(btnOnOff)
	pad_len = 32 - (len(hex_data) - 24) % 32
	hex_data = hex_data + ''.ljust(pad_len, '0')
	return hex_data
