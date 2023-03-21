import hassapi as hass
from enum import Enum


WATER_HEATER_SWITCH    = "switch.warmwasserpumpe"
LIGHT_DEFAULT_MODE_SCRIPT   = "script.led_band_bad_default_mode"
LIGHT_EFFECT_WATER_WARMING  = "blinkred"
LIGHT_EFFECT_WATER_WARM     = "green_effect"
LIGHT_PLAYLIST_SHOWERING    = "duschen"
LIGHT_EFFECT_SHOWERING_LONG = "langduschen"


class ButtonAction(Enum):
    SHORT = 1
    LONG = 2


class State(Enum):
    IDLE = 1
    WATER_WARMING = 2
    WATER_WARM = 3
    SHOWERING = 4
    SHOWERING_LONG = 5


class ShowerController(hass.Hass):
    def __init__(self):
        self.currentState = None

    def initialize(self):
        print("Initializing ShowerController")

        self.currentState = State.IDLE

        # TODO execute button press

    def handleButtonPress(self, action=ButtonAction.SHORT, kwargs=None):
        if action == ButtonAction.SHORT:
            # Execute next-action
            print("Shower-Button pressed shortly")

            self.nextState()

            self.executeActions()

        if action == ButtonAction.LONG:
            # Cancel script
            print("Shower-Button pressed long")

            self.currentState = State.IDLE

            self.executeActions()

    def nextState(self):
        if self.currentState == len(State):
            self.currentState = 1
        else:
            self.currentState += 1
    # Execute action based on state
    def executeActions(self):
        self.cancelTimeout()

        if self.currentState == State.IDLE:
            self.turn_on(LIGHT_DEFAULT_MODE_SCRIPT)

        if self.currentState == State.WATER_WARMING:
            self.turn_on(LIGHT_EFFECT_WATER_WARMING)
            self.turn_on(WATER_HEATER_SWITCH)
            # Wait x minutes to next state
            self.setTimeout(10)

        if self.currentState == State.WATER_WARM:
            self.turn_on(LIGHT_EFFECT_WATER_WARM)
            self.setTimeout(20)

        if self.currentState == State.SHOWERING:
            self.turn_on(LIGHT_PLAYLIST_SHOWERING)
            self.setTimeout(15)

        if self.currentState == State.SHOWERING_LONG:
            self.turn_on(LIGHT_EFFECT_SHOWERING_LONG)
            self.setTimeout(15)

    def cancelTimeout(self):
        # TODO cancel timer

    def setTimeout(self, minutes):
        # TODO implement async timer, then call executeActions
        self.nextState()
        self.executeActions()
