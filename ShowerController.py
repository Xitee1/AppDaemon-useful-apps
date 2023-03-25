import hassapi as hass
from enum import Enum
import time


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
    """
    Preheat the water, show the state of the heated water and when showering applying some cool effects to the light.
    Only with a few presses on a button.

    Requirements:
    - Switch for water heater ('switch.')
    - Input button for switch states (short and long press) ('input_button.')
    - LED strip in the shower running WLED
    - Script to set the light to a default mode
      In my case: After sunrise: Light goes off - After sunset: Light turn on at brightness level 1%

    How to use:
    - Press the button once to turn on the water heater. The light will shine blue to indicate the cold water.
      After a set delay, it will turn green to indicate that the water should be warm now.
    - Right before you go under the shower, press the button again to set the script to showering state.
      In this state the light will play the WLED showering playlist. Water heater stays on.
      After a set delay, the light will blink red to indicate that you should finish showering.
    - After you're done showering, press the button again. This will set the light to the default mode and turns
      off the water heater.
    - A long press cancels everything - Light will go into default mode and water heater will turn off.

    Required Arguments:
    - short_press_sensor:
        A input_button that triggers when the button is pressed short.
    - long_press_sensor:
        A input_button that triggers when the button is pressed long.
    - water_heater_switch:
        The switch that will turn on the water heater.
    - led_strip_preset:
        The WLED preset 'select.' entity of the LED strip.
    - led_strip_playlist:
        The WLED playlist 'select.' entity of the LED strip.
    - led_strip_default_mode_script:
        A script that turns off the light.
        This is a script to allow some extra functions if you for example want to turn on the light at night at a low brightness level.
    - preset_water_warming:
        The preset name for the "water is warming"-state.
        E.g. a preset that lets the light shine blue.
    - preset_water_warm
        The preset name for the "water is warm"-state.
        E.g. a preset that lets the light shine green.
    - playlist_showering
        The playlist name for the "showering"-state.
        This playlist can be filled with cool effects that play while showering.
    - preset_showering_long
        The preset name for the "showering long"-state.
        E.g. red blinks red.
    """

    def __init__(self):
        self.currentState = State.IDLE
        self.water_heater = None
        self.led_strip_preset = None
        self.led_strip_playlist = None

    def initialize(self):
        print("Initializing ShowerController")

        self.water_heater = self.get_entity(self.args['water_heater_switch'])
        self.led_strip_preset = self.get_entity(self.args['led_strip_preset'])
        self.led_strip_playlist = self.get_entity(self.args['led_strip_playlist'])

        self.listen_state(self.handle_button_press(), self.args['short_press_sensor'], new="on")
        self.listen_state(self.handle_button_press(action=ButtonAction.LONG), self.args['long_press_sensor'], new="on")

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
        # TODO need to set select. entity instead turn on
        if self.currentState == State.IDLE:
            self.turn_on(self.args['led_strip_default_mode_script'])
            self.water_heater.turn_off()

        if self.currentState == State.WATER_WARMING:
            self.led_strip_preset.set_state(state=self.args['preset_water_warming'])
            self.water_heater.turn_on()
            # Wait x minutes to next state
            self.set_timeout(10)

        if self.currentState == State.WATER_WARM:
            self.led_strip_preset.set_state(state=self.args['preset_water_warm'])
            self.set_timeout(20)

        if self.currentState == State.SHOWERING:
            self.led_strip_playlist.set_state(state=self.args['playlist_showering'])
            self.set_timeout(15)

        if self.currentState == State.SHOWERING_LONG:
            self.led_strip_preset.set_state(state=self.args['preset_showering_long'])
            self.set_timeout(15)

    def cancel_timeout(self):
        # TODO cancel timer
        print("TODO cancel timer")

    def set_timeout(self, minutes):
        time.sleep(60 * minutes)
        self.next_state(True)
        self.execute_actions()
