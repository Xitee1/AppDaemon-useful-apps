import hassapi as hass
from enum import Enum
import time
from appdaemon.exceptions import TimeOutException


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

    Required arguments:
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
    - led_strip_turn_off:
        Any entity with that turns the light off (e.g.: light.shower_light)
        You can also specify a script here (e.g.: script.turn_off_shower_light) if you want to do some
        extra logic.
    - preset_water_warming:
        The preset name for the "water is warming"-state.
        E.g. a preset that lets the light shine blue.
    - preset_water_warm:
        The preset name for the "water is warm"-state.
        E.g. a preset that lets the light shine green.
    - preset_showering_long:
        The preset name for the "showering long"-state.
        E.g. red blinks red.
    - playlist_showering:
        The playlist name for the "showering"-state.
        This playlist can be filled with cool effects that play while showering.


    Optional arguments:
    - led_strip_controlled_by_script:
        This binary sensor will be set to on while the script is controlling the light. This allows you to use it as condition for other automations.
        Use any entity id for it that does not exist.
        Default: none
    - preheat_duration:
        How long the heater must be on so the state changes to "WATER_WARM". For example if your heater needs 10 minutes to make warm water, set it to 10.
        Default: 10
    - general_timeout_duration:
        If a state takes longer than this timeout, the app cancels, turns off the heater and the lights.
        Default: 20
    - time_to_shower_warning:
        When showering longer than the set minutes the light will switch to the "preset_showering_long" preset indicating that you should stop showering.
        Default: 10
    """

    def initialize(self):
        print("Initializing ShowerController")
        self.currentState = State.IDLE
        self.timer_count = -1

        # Arguments
        self.debug = self.args['debug']

        self.entity_water_heater = self.get_entity(self.args['water_heater_switch'])
        self.entity_led_strip_preset = self.get_entity(self.args['led_strip_preset'])
        self.entity_led_strip_playlist = self.get_entity(self.args['led_strip_playlist'])
        self.entity_led_strip = self.get_entity(self.args['led_strip'])

        # Optional arguments
        self.led_strip_controlled_by_script = (self.args['led_strip_controlled_by_script'] if 'led_strip_controlled_by_script' in self.args else None)
        self.duration_heating = (int(self.args['preheat_duration']) if 'preheat_duration' in self.args else 10) * 60
        self.timeout_water_warm = (int(self.args['timeout_water_warm']) if 'timeout_water_warm' in self.args else 20) * 60
        self.timeout_general = (int(self.args['general_timeout_duration']) if 'general_timeout_duration' in self.args else 20) * 60
        self.timeout_long_shower = (int(self.args['time_to_shower_warning']) if 'time_to_shower_warning' in self.args else 10) * 60

        # Buttons
        self.get_entity(self.args['short_press_sensor']).listen_state(self.button_press_short)
        self.get_entity(self.args['long_press_sensor']).listen_state(self.button_press_long)

        # Timer (executes timer_run every second to count down)
        self.run_every(self.timer_run, start="now", interval=1)

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

            self.set_state()  # Do state logic and set next state
            self.execute_actions()

        if action == ButtonAction.LONG:
            # Cancel script
            print("Shower-Button pressed long")

            self.set_state(state=State.IDLE)
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

        if self.led_strip_controlled_by_script != None:
            if(self.currentState == State.IDLE):
                self.led_strip_controlled_by_script.turn_off()
            else:
                self.led_strip_controlled_by_script.turn_on()

        match self.currentState:
            case State.IDLE:
                self.entity_led_strip.turn_off()
                self.entity_water_heater.turn_off()

            case State.WATER_WARMING:
                self.entity_led_strip_preset.call_service("select_option", option=self.args['preset_water_warming'])
                self.entity_water_heater.turn_on()
                self.wait_for_heater()

            case State.WATER_WARM:
                self.entity_led_strip_preset.call_service("select_option", option=self.args['preset_water_warm'])
                self.set_timeout(self.timeout_water_warm)

            case State.SHOWERING:
                self.entity_led_strip_playlist.call_service("select_option", option=self.args['playlist_showering'])
                self.set_timeout(self.timeout_long_shower)

            case State.SHOWERING_LONG:
                self.entity_led_strip_preset.call_service("select_option", option=self.args['preset_showering_long'])
                self.set_timeout(self.timeout_general)

    def set_timeout(self, seconds):
        if self.timer_count != -1:
            self.mylog("Warning: Cannot set new timeout because a timer is already running!")
            return

        self.timer_count = seconds
        self.mylog(f"Timeout for current action in state {self.currentState} set to {int(seconds / 60)}min.")

    def cancel_timeout(self):
        self.timer_count = -1
        # TODO cancel wait for heater
        self.mylog("Timeout has been cancelled.")


    def timer_run(self):
        if self.timer_count > 0:
            self.timer_count -= 1

    async def wait_for_heater(self):
        self.mylog(f"Waiting for heater to be on for {int(self.duration_heating / 60)}min")

        try:
            await self.entity_water_heater.wait_state("on", duration=self.duration_heating, timeout=self.duration_heating + 5)
            self.set_state(state=None, ignore_logic=True)
            self.execute_actions()
        except TimeOutException:
            self.set_state(State.IDLE)
            self.mylog("Error: Heating failed. Heater wasn't on state 'on' for long enough.")
            pass

