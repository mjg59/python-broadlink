from flask import Flask
from flask import request
import json
import broadlink

device = None
sub_devices = None

def create_resp(state,gang):
    key = None
    if gang == 1:
        key = 'pwr1'
    elif gang == 2:
        key = 'pwr2'
    elif gang == 3:
        key = 'pwr3'
    
    if state[key] == 1:
        return '{"is_active": "true"}'
    else:
        return '{"is_active": "false"}'

def handle_request(request,did,gang):
    if request.method == 'POST':     
        data = json.loads(request.data)
        pwr = [None,None,None,None]
        
        if data['active'] == "true":
            pwr[gang] = 1
        else:
            pwr[gang] = 0
            
        return create_resp(device.set_state(did,pwr[1],pwr[2],pwr[3]),gang)
        
    else:
        return create_resp(device.get_state(did),gang)

def request_did(request,did):
        return device.get_state(did)

app = Flask(__name__)

@app.route("/",methods = ['GET'])
def hello():
    global device
    global sub_devices
    global app
    hub_ip = request.args.get('hub')
    
    if hub_ip is not  None:
        
        try:
            device = broadlink.hello(hub_ip)
            device.auth()
            sub_devices = device.get_subdevices()
            
        except Exception as err:
            return str(err)
            
        return str(sub_devices)
    else:
        return str(sub_devices)
    # http://127.0.0.1:5000/?hub=192.168.1.99
    # http://127.0.0.1:5000/00000000000000000000a043b0d0783a/1

@app.route("/<did>/<gang>",methods = ['POST', 'GET'])
def dynamic(did,gang):
    return handle_request(request,did,int(gang))

@app.route("/<did>",methods = ['GET'])
def get_did(did):
    return request_did(request,did)
