import os

from flask import Flask, request
from lib.broadlink_controller import BroadlinkController
from lib.custom_device import CustomDevice

app = Flask(__name__)

controllers = dict()
custom_devices = dict()


@app.route('/send_command', methods=['GET'])
def send_command():
    command = request.args.get('command')
    custom_device_name = f"{request.args.get('custom_device_name')}.device"

    custom_device_list = custom_devices.keys()

    if custom_device_name not in custom_device_list:
        return f"custom device '{request.args.get('custom_device_name')}' not found", 404

    selected_custom_device: CustomDevice = custom_devices.get(custom_device_name)

    if command and command in selected_custom_device.get_commands():
        selected_custom_device.send_command(command)
        return "Command sent successfully", 200
    elif command:
        return f"Invalid command: {command}", 400
    else:
        return "Missing 'command' parameter", 400


@app.route("/register_controller", methods=["GET"])
def register_controller():
    local_ip = request.args.get("local_ip")
    rf_frequency = float(request.args.get("rf_frequency"))
    name = request.args.get("name")

    if not name and len(controllers) > 1:
        return "'name' parameter required when registering more than one controller",  400
    elif not name:
        name = "primary"

    controller = BroadlinkController(local_ip=local_ip, rf_frequency=rf_frequency)
    controllers[name] = controller

    return f"controller '{name}' registered successfully", 200


@app.route("/list_controllers", methods=["GET"])
def list_controllers():
    controller_names = controllers.keys()
    if len(controller_names) == 0:
        return "No controllers registered", 404

    return ",".join(controller_names)


@app.route("/list_custom_devices", methods=["GET"])
def list_custom_devices():
    custom_device_list = []

    try:
        custom_device_list = [device.split(".device")[0] for device in os.listdir("../local/custom_devices/")]
        no_devices = len(custom_device_list) == 0
    except Exception as e:
        no_devices = True

    if no_devices:
        return "No custom devices found, use the custom device creator cli to create a new device", 404

    return ",".join(custom_device_list), 200


@app.route("/list_custom_device_commands", methods=["GET"])
def list_custom_device_commands():
    custom_device_name = f"{request.args.get('custom_device_name')}.device"

    custom_device_list = custom_devices.keys()

    if custom_device_name not in custom_device_list:
        return f"custom device '{custom_device_name}' not found", 404

    selected_custom_device: CustomDevice = custom_devices.get(custom_device_name)
    device_commands = selected_custom_device.get_commands()

    if len(device_commands):
        return ",".join(device_commands), 200

    return "No commands found", 200


@app.route("/register_custom_device", methods=["GET"])
def register_custom_device():
    custom_device_name = f"{request.args.get('custom_device_name')}.device"
    controller_name = request.args.get("controller_name")

    custom_device_list = os.listdir("../local/custom_devices/")

    if custom_device_name not in custom_device_list:
        return f"custom device '{request.args.get('custom_device_name')}' not found", 404

    if controller_name not in controllers.keys():
        return f"controller '{request.args.get('custom_device_name')}' not found", 404

    selected_controller: BroadlinkController = controllers.get(controller_name)
    custom_device = CustomDevice(selected_controller, f"../local/custom_devices/{custom_device_name}")
    custom_devices[custom_device_name] = custom_device

    return f"registered custom device '{request.args.get('custom_device_name')}' with controller '{controller_name}'", 200


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5050)
