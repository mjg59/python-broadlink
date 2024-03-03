import os
import pickle

from lib.broadlink_controller import BroadlinkController


class CustomDevice:
    def __init__(self, broadlink_controller: BroadlinkController, config_file_path):
        self.config = pickle.load(open(config_file_path, "rb"))
        self.controller = broadlink_controller

    def get_commands(self):
        return self.config.keys()

    def send_command(self, command_name):
        packet = self.config.get(command_name)
        if not packet:
            print(f"invalid command: {command_name}")
            return

        print(f"sending command for {command_name}")

        self.controller.send_command(packet)


class CustomDeviceCreator:
    def __init__(self, broadlink_controller: BroadlinkController, device_name=None, modify_existing_path=None):
        self.controller = broadlink_controller
        self.config = {}

        if modify_existing_path:
            self.name = os.path.basename(modify_existing_path).replace(".device", "")
            try:
                with open(modify_existing_path, "rb") as file:
                    self.config = pickle.load(file)
                    existing_commands = self.config.keys()
                    print(f"loaded device {self.name}.device with commands: {', '.join(existing_commands)}")
            except:
                print(f"failed to load device {self.name}.device, creating new device")
                self.config = {}
        else:
            self.name = device_name

    def save(self, directory=""):
        file_name = f"{self.name}.device"
        file_path = os.path.join(directory, file_name)
        print(f"saving device to {file_path}")
        with open(file_path, "wb") as file:
            pickle.dump(self.config, file)

    def __add_command(self, command_name, packet):
        self.config[command_name] = packet
        print(f"added command for {command_name}")

    def remove_command(self, command_name):
        if command_name in self.config:
            del self.config[command_name]
            print(f"removed command for {command_name}")
        else:
            print(f"command {command_name} not found")

    def train_rf(self, command_name):
        print(f"training rf for {command_name}")
        packet = self.controller.train_rf()
        if packet:
            self.__add_command(command_name, packet)
            return True
        return False

    def train_ir(self, command_name):
        print(f"training ir for {command_name}")
        packet = self.controller.train_ir()
        if packet:
            self.__add_command(command_name, packet)
            return True
        return False

    def test_command(self, command_name):
        print(f"testing command for {command_name}")
        self.controller.send_command(self.config.get(command_name))
