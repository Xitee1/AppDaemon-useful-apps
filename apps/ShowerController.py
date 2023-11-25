import hassapi as hass
from enum import Enum


class State(Enum):
    IDLE = 1
    PREPARING = 2
    READY = 3
    IN_USE = 4
    GET_OUT = 5


class ShowerController(hass.Hass):
    """
    Preheat the water, show the state of the heated water by the color of the light and when showering applying some cool effects to the light.
    Only with a few presses on a button.

    Requirements:
    TODO

    How to use:
    TODO update
    - Press the button once to turn on the water heater. The light will shine blue to indicate the cold water.
      After a set delay, it will turn green to indicate that the water should be warm now.
    - Right before you go under the shower, press the button again to set the script to showering state.
      In this state the light will play the WLED showering playlist. Water heater stays on.
      After a set delay, the light will blink red to indicate that you should finish showering.
    - After you're done showering, press the button again. This will set the light to the default mode and turns
      off the water heater.
    - A long press cancels everything - Light will go into default mode and water heater will turn off.
    """

    def initialize(self):
        self.log("Initializing ShowerController..")
        # Init arguments
        self.debug = bool(self.args['debug']) if 'debug' in self.args else False

        self.shower_script = self.get_entity(self.args['shower_script'])
        self.shower_prepare_duration = int(self.args['shower_prepare_duration']) * 60 if 'shower_prepare_duration' in self.args else None
        self.shower_prepare_state = self.get_entity(self.args['shower_prepare_state']) if 'shower_prepare_state' in self.args else None

        self.timeout_ready = (int(self.args['timeout_ready']) if 'timeout_ready' in self.args else 20) * 60
        self.timeout_in_use = (int(self.args['timeout_in_use']) if 'timeout_in_use' in self.args else 10) * 60
        self.timeout_get_out = (int(self.args['timeout_get_out']) if 'timeout_get_out' in self.args else 5) * 60

        self.trigger_entity = self.get_entity(self.args['trigger_entity'])
        self.cancel_entity = self.get_entity(self.args['cancel_entity'])

        # Init vars
        self.current_state = State.IDLE
        self.timer_count = -1
        self.proceed_if_prepare_state = False

        # Triggers
        self.trigger_entity.listen_state(self.trigger_script)
        self.cancel_entity.listen_state(self.cancel_script)

        # Timer (executes timer_run every second to count down)
        self.run_every(self.timer_run, start="now", interval=1)

        self.log("ShowerController initialized!")

    def clog(self, msg):
        if self.debug:
            self.log(msg)

    def trigger_script(self, entity, attribute, old, new, kwargs):
        self.clog("Script triggered by trigger_entity. Proceed to next state (with logic).")
        self.set_state()  # Do state logic and set next state

    def cancel_script(self, entity, attribute, old, new, kwargs):
        self.clog("Script cancelled by cancel_entity. Script will return to idle mode.")
        self.set_state(state=State.IDLE)

    """
    State handling
    """
    def set_state(self, state=None, ignore_logic=False):
        """
        :param state: optional -> automatically go to next state
        :param ignore_logic: optional -> only relevant when state is None, increases state += 1 and does not set new state based on current state
        :return:

        Sets a new shower state, either automatically or applies the wanted state from the state parameter.
        """

        # For some reason "state" is not "None" if undefined as it should be but "False".
        # Does someone know from where the "False" comes? Clearly it is defined to be "None" if the param isn't passed.
        if state is False:
            state = None

        if state is None:
            # If executed without logic, go to the next step...
            if ignore_logic:
                if self.current_state == len(State):
                    self.current_state = 1
                else:
                    self.current_state += 1
            # ...otherwise skip some steps and apply a bit of logic
            else:
                # IDLE -> PREPARING
                if self.current_state == State.IDLE:
                    self.current_state = State.PREPARING

                # PREPARING or READY -> IN_USE
                elif self.current_state in (State.PREPARING, State.READY):
                    self.current_state = State.IN_USE

                # IN_USE or GET_OUT -> IDLE
                elif self.current_state in (State.IN_USE, State.GET_OUT):
                    self.current_state = State.IDLE

                else:
                    self.log(f"Error: Unknown state: {self.current_state}")
        else:
            self.current_state = state

        self.clog(f"State has been changed to {self.current_state}")
        self.execute_actions()

    # Execute action based on state
    def execute_actions(self):
        self.clog(f"Executing actions. Current state is: {self.current_state}")

        self.cancel_timeout()

        match self.current_state:
            case State.IDLE:
                self.shower_script.turn_on(variables={'state': 'idle'})

            case State.PREPARING:
                self.shower_script.turn_on(variables={'state': 'preparing'})
                self.set_preparing_timeout()

            case State.READY:
                self.shower_script.turn_on(variables={'state': 'ready'})
                self.set_timeout(self.timeout_ready)

            case State.IN_USE:
                self.shower_script.turn_on(variables={'state': 'in_use'})
                self.set_timeout(self.timeout_in_use)

            case State.GET_OUT:
                self.shower_script.turn_on(variables={'state': 'get_out'})
                self.set_timeout(self.timeout_get_out)

    """
    Timers & Timeout
    """
    def set_timeout(self, seconds):
        if self.timer_count != -1:
            self.log("Error: Cannot set new timeout because a timer is already running!")
            return

        self.timer_count = seconds
        self.clog(f"Timeout for current action in state {self.current_state} set to {int(seconds / 60)}min.")

    def cancel_timeout(self):
        if self.timer_count != -1:
            self.timer_count = -1
            self.clog("Timeout has been cancelled.")


    def timer_run(self, kwargs=None):
        if self.proceed_if_prepare_state and self.shower_prepare_state.get_state() == "on":
            self.proceed_if_prepare_state = False
            self.set_state(ignore_logic=True)

        if self.timer_count > 0:
            self.timer_count -= 1

        if self.timer_count == 0:
            self.timer_count = -1
            self.clog("Timeout reached! Proceeding to next step...")
            self.proceed_if_prepare_state = False
            self.set_state(ignore_logic=True)

    def set_preparing_timeout(self):
        if self.shower_prepare_duration is None and self.shower_prepare_state is None:
            self.log("Error: You need to define at least one of the two 'shower_prepare_duration' or 'shower_prepare_state' arguments!")
            return

        if self.shower_prepare_state is not None:
            self.proceed_if_prepare_state = True

        if self.shower_prepare_duration is not None:
            self.set_timeout(self.shower_prepare_duration)
