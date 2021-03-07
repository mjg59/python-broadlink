"""Support for lights."""
import enum

from . import device
from .common import State


class lb27(device.device):
    """Controls a Broadlink LB27."""

    TYPE = "LB27"

    @enum.unique
    class ColorMode(enum.IntEnum):
        """Enumerates color modes."""

        RGB = 0
        WHITE = 1
        SCENE = 2

    def get_state(self) -> dict:
        """Return the power state of the device.

        Example: `{'red': 128, 'blue': 255, 'green': 128, 'pwr': 1, 'brightness': 75, 'colortemp': 2700, 'hue': 240, 'saturation': 50, 'transitionduration': 1500, 'maxworktime': 0, 'bulb_colormode': 1, 'bulb_scenes': '["@01686464,0,0,0", "#ffffff,10,0,#000000,190,0,0", "2700+100,0,0,0", "#ff0000,500,2500,#00FF00,500,2500,#0000FF,500,2500,0", "@01686464,100,2400,@01686401,100,2400,0", "@01686464,100,2400,@01686401,100,2400,@005a6464,100,2400,@005a6401,100,2400,0", "@01686464,10,0,@00000000,190,0,0", "@01686464,200,0,@005a6464,200,0,0"]', 'bulb_scene': '', 'bulb_sceneidx': 255}`
        """
        data = State.pack(State.READ, {})
        resp = self.send_cmd(0x5A5AA5A5, data)
        return State.unpack(resp)[1]

    def set_state(
        self,
        pwr: bool = None,
        red: int = None,
        blue: int = None,
        green: int = None,
        brightness: int = None,
        colortemp: int = None,
        hue: int = None,
        saturation: int = None,
        transitionduration: int = None,
        maxworktime: int = None,
        bulb_colormode: int = None,
        bulb_scenes: str = None,
        bulb_scene: str = None,
        bulb_sceneidx: int = None,
    ) -> dict:
        """Set the power state of the device."""
        state = {}
        if pwr is not None:
            state["pwr"] = int(bool(pwr))
        if red is not None:
            state["red"] = int(red)
        if blue is not None:
            state["blue"] = int(blue)
        if green is not None:
            state["green"] = int(green)
        if brightness is not None:
            state["brightness"] = brightness
        if colortemp is not None:
            state["colortemp"] = colortemp
        if hue is not None:
            state["hue"] = hue
        if saturation is not None:
            state["saturation"] = saturation
        if transitionduration is not None:
            state["transitionduration"] = transitionduration
        if maxworktime is not None:
            state["maxworktime"] = maxworktime
        if bulb_colormode is not None:
            state["bulb_colormode"] = bulb_colormode
        if bulb_scenes is not None:
            state["bulb_scenes"] = bulb_scenes
        if bulb_scene is not None:
            state["bulb_scene"] = bulb_scene
        if bulb_sceneidx is not None:
            state["bulb_sceneidx"] = bulb_sceneidx

        data = State.pack(State.WRITE, state)
        resp = self.send_cmd(0x5A5AA5A5, data)
        return State.unpack(resp)[1]


class lb1(lb27, metaclass=device.V4Meta):
    """Controls a Broadlink LB1."""

    TYPE = "LB1"
