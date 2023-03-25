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
    Preheat the water, show the state of the heated water by the color of the light and when showering applying some cool effects to the light.
    Only with a few presses on a button.

    Requirements:
    - Switch for water heater ('switch.')
    - Any entity that changes its state (only!) when pressing the button (each, for short and long press)
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

    def initialize(self):
        print("Initializing ShowerController")
        self.currentState = State.IDLE

        self.debug = self.args['debug']

        self.water_heater = self.get_entity(self.args['water_heater_switch'])
        self.led_strip_preset = self.get_entity(self.args['led_strip_preset'])
        self.led_strip_playlist = self.get_entity(self.args['led_strip_playlist'])

        self.get_entity(self.args['short_press_sensor']).listen_state(self.button_press_short)
        self.get_entity(self.args['long_press_sensor']).listen_state(self.button_press_long)

    def mylog(self, msg):
        if self.debug:
            self.log(msg)

    #######
    # This is needed because sadly in the listen_state function from AppDaemon you cannot specify parameters
    # We also do not need all the arguments: entity, attribute, old, new, kwargs
    def button_press_short(self, entity, attribute, old, new, kwargs):
        self.handle_button_press(action=ButtonAction.SHORT)

    def button_press_long(self, entity, attribute, old, new, kwargs):
        self.handle_button_press(action=ButtonAction.LONG)
    #######

    def handle_button_press(self, action):
        if action == ButtonAction.SHORT:
            # Execute next-action
            print("Shower-Button pressed shortly")

            self.set_state(False)
            self.execute_actions()

        if action == ButtonAction.LONG:
            # Cancel script
            print("Shower-Button pressed long")

            self.currentState = State.IDLE
            self.execute_actions()

    def set_state(self, state=None, ignore_logic=False):
        """
        :param state: optional -> automatically go to next state
        :param ignore_logic: optional -> only relevant when state is None, increases state += 1 and does not set new state based on current state
        :return:

        Sets a new shower state, either automatically or applies the wanted state from the state parameter.
        """

        # For some reason state is not None by default as defined but False.
        # If I set it to None with "state = None" it is none.. does someone know why this is??
        # if state is None:
        if state in (None, False):
            # If executed by timeout, go through all steps...
            if ignore_logic:
                if self.currentState == len(State):
                    self.currentState = 1
                else:
                    self.currentState += 1
            # ..otherwise (if manually) specify the next state manually based on the current state
            else:
                # IDLE -> WATER_WARMING
                if self.currentState == State.IDLE:
                    self.currentState = State.WATER_WARMING

                # WATER_WARMING or WATER_WARM -> SHOWERING
                elif self.currentState in (State.WATER_WARMING, State.WATER_WARM):
                    self.currentState = State.SHOWERING

                # SHOWERING or SHOWERING_LONG -> IDLE
                elif self.currentState in (State.SHOWERING, State.SHOWERING_LONG):
                    self.currentState = State.IDLE

                else:
                    self.log(f"Error: Unknown state: {self.currentState}")
        else:
            self.currentState = state

        self.mylog(f"State has changed to {self.currentState}")

    # Execute action based on state
    def execute_actions(self):
        self.mylog(f"Executing actions. Current state is: {self.currentState}")

        self.cancel_timeout()

        if self.currentState == State.IDLE:
            self.turn_on(self.args['led_strip_default_mode_script'])
            self.water_heater.turn_off()

        if self.currentState == State.WATER_WARMING:
            self.led_strip_preset.call_service("select_option", option=self.args['preset_water_warming'])
            self.water_heater.turn_on()
            # Wait x minutes to next state
            self.set_timeout(10)

        if self.currentState == State.WATER_WARM:
            self.led_strip_preset.call_service("select_option", option=self.args['preset_water_warm'])
            self.set_timeout(20)

        if self.currentState == State.SHOWERING:
            self.led_strip_playlist.call_service("select_option", option=self.args['playlist_showering'])
            self.set_timeout(15)

        if self.currentState == State.SHOWERING_LONG:
            self.led_strip_preset.call_service("select_option", option=self.args['preset_showering_long'])
            self.set_timeout(15)

    def cancel_timeout(self):
        self.mylog("Timeout has been cancelled.")
        # TODO cancel timer
        print("TODO cancel timer")

    def set_timeout(self, minutes):
        self.mylog(f"Timeout for current action in state {self.currentState} set to {minutes}min.")
        #time.sleep(60 * minutes)
        #self.set_state(ignore_logic=True)
        #self.execute_actions()