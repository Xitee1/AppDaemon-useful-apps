import hassapi as hass
from enum import Enum
import time

testmode = True

LISTEN_BIN_SENSOR_1         = "binary_sensor.some_switch"

WATER_HEATER_SWITCH         = "switch.warmwasserpumpe"
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
        self.currentState = State.IDLE

    def initialize(self):
        print("Initializing ShowerController")

        self.listen_state(self.handle_button_press(), LISTEN_BIN_SENSOR_1, new="on")
        # TODO execute button press

    def handle_button_press(self, action=ButtonAction.SHORT, kwargs=None):
        if action == ButtonAction.SHORT:
            # Execute next-action
            print("Shower-Button pressed shortly")

            self.next_state(False)
            self.execute_actions()

        if action == ButtonAction.LONG:
            # Cancel script
            print("Shower-Button pressed long")

            self.currentState = State.IDLE
            self.execute_actions()

    def next_state(self, by_timeout=False):
        if self.currentState == len(State):
            self.currentState = 1
        else:
            # If executed by timeout, go through all steps...
            if by_timeout:
                self.currentState += 1
            # ..otherwise (if manually) specify the next state manually based on the current state
            else:
                # IDLE -> WATER_WARMING
                if self.currentState == State.IDLE:
                    self.currentState = State.WATER_WARMING

                # WATER_WARMING or WATER_WARM -> SHOWERING
                if self.currentState in (State.WATER_WARMING, State.WATER_WARM):
                    self.currentState = State.SHOWERING

                # SHOWERING or SHOWERING_LONG -> IDLE
                if self.currentState in (State.SHOWERING, State.SHOWERING_LONG):
                    self.currentState = State.IDLE

    # Execute action based on state
    def execute_actions(self):
        self.cancel_timeout()

        if self.currentState == State.IDLE:
            self.turn_on(LIGHT_DEFAULT_MODE_SCRIPT)

        if self.currentState == State.WATER_WARMING:
            self.turn_on(LIGHT_EFFECT_WATER_WARMING)
            self.turn_on(WATER_HEATER_SWITCH)
            # Wait x minutes to next state
            self.set_timeout(10)

        if self.currentState == State.WATER_WARM:
            self.turn_on(LIGHT_EFFECT_WATER_WARM)
            self.set_timeout(20)

        if self.currentState == State.SHOWERING:
            self.turn_on(LIGHT_PLAYLIST_SHOWERING)
            self.set_timeout(15)

        if self.currentState == State.SHOWERING_LONG:
            self.turn_on(LIGHT_EFFECT_SHOWERING_LONG)
            self.set_timeout(15)

    def cancel_timeout(self):
        # TODO cancel timer
        print("TODO cancel timer")

    def set_timeout(self, minutes):
        time.sleep(60 * minutes)
        self.next_state(True)
        self.execute_actions()
