import os
import time
import broadlink
import pickle


class BroadlinkController:
    def __init__(self, local_ip=None, rf_frequency=None, file_path=None, select_if_multiple_func=None):
        if file_path:
            print(f"loading controller from {file_path}")
            with open(file_path, "rb") as file:
                self = pickle.load(file)
        else:
            self.device = None
            self.local_ip = local_ip
            self.rf_frequency = rf_frequency

        self._select_if_multiple = select_if_multiple_func

        self.__get_device()
        self.__auth_device()
        self.__test_comms()

    def __get_device(self):
        print("attempting device discovery")

        if self.local_ip:
            print(f"searching for device at {self.local_ip}")
            try:
                self.device = broadlink.hello(self.local_ip)
            except:
                print(f"failed to find device at {self.local_ip}")

        if not self.device:
            print("doing broad device search")
            device_list = broadlink.discover()
            if len(device_list) > 0 and self._select_if_multiple:
                print("multiple devices found, calling select_if_multiple_func for device selection")
                self.device = self._select_if_multiple(device_list)
            else:
                if len(device_list) > 1:
                    print("multiple devices found, no select_if_multiple_func provided. Selecting first device found.")
                else:
                    print("found one device, selecting")
                self.device = device_list[0] if len(device_list) > 0 else None

        if self.device:
            print("found device")
            self.local_ip = self.device.host[0]
        else:
            print("device discovery failed")

    def __auth_device(self):
        if self.device:
            print("authenticating with device")
            self.device.auth()

    def __test_comms(self):
        if self.device:
            print("checking device connection")

            try:
                self.device.hello()
                print(f"connected to device at {self.local_ip}")
            except Exception as e:
                print("failed to connect to device")

    def train_rf(self):
        print("starting rf training")
        packet = None

        if self.device:
            if not self.rf_frequency:
                self.device.sweep_frequency()
                time.sleep(31)

            self.device.find_rf_packet(frequency=self.rf_frequency)
            time.sleep(15)

            attempt_ct = 0
            while attempt_ct < 3:
                try:
                    packet = self.device.check_data()
                    break
                except:
                    attempt_ct += 1

        if packet:
            print(f"found rf packet: {packet}")
        else:
            print(f"no rf packet found")

        return packet

    def train_ir(self):
        print("starting ir training")
        packet = None

        if self.device:
            self.device.enter_learning()
            time.sleep(15)

            attempt_ct = 0
            while attempt_ct < 3:
                try:
                    packet = self.device.check_data()
                    break
                except:
                    attempt_ct += 1

        if packet:
            print(f"found ir packet: {packet}")
        else:
            print(f"no ir packet found")

        return packet

    def send_command(self, packet):
        self.device.send_data(packet)

    def save(self, directory=""):
        file_name = f"{self.local_ip}.controller"
        file_path = os.path.join(directory, file_name)
        print(f"saving controller to {file_path}")
        with open(file_path, "wb") as file:
            pickle.dump(self, file)
