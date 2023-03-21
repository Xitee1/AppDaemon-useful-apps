import hassapi as hass
from enum import Enum

class ButtonAction(Enum):
    SHORT = 1
    LONG = 2


class DuschController(hass.Hass):
    def initialize(self):
        print("Initializing DuschController")

        # TODO execute button press

    def handleButtonPress(self, action=ButtonAction.SHORT, kwargs=None):
        if action == ButtonAction.SHORT:
            print("Dusch-Button pressed shortly")

        if action == ButtonAction.LONG:
            print("Dusch-Button pressed long")
