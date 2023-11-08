import hassapi as hass
import datetime

class ThermostatController(hass.Hass):
    """
    App to control thermostat that can be directly controlled (valve position), like the Eurotronic Spirit/Comet.

    Arguments:
        - entity_thermostat:
            Required. (climate entity id)
            A HomeAssistant climate entity (dummy thermostat using generic_thermostat).
        - entity_valve_position:
            Required. (number entity id)
            A HomeAssistant number entity of the valve position with a range of 0-255.
        - entity_enabled:
            Optional. (switch entity id)
            Specify a switch to enable/disable the script.
        - update_interval: (int: seconds)
            Optional.
            Instead of updating on state change of the thermostat entity, it will update at a fixed update interval.
            Specify the fixed update interval in seconds.
            Useful if you want to reduce calls to the valve.
        - valve_compare_current_value:
            Optional. (True/False)
            Set this to true to compare to the current valve position to update it instead the stored value by the script.
            Use this if you want to overwrite manually set valve position instantly.
            (Can be helpful if your valve resets its valve position after some time)
        - valve_always_update:
            Optional. (True/False)
            Do not check temp difference or current valve position and always update its position.
            Can be helpful if your thermostat does reset itself after some time. May be used in combination with the 'update_interval' option.
            Option 'valve_compare_current_value' will be ignored.
            WARNING: May degrease battery life!
    """

    def initialize(self):
        # Init
        self.log("Initializing ThermostatController..")
        self.last_current_temp = 0
        self.last_execution_time = datetime.datetime.now()
        self.last_valve_position = None

        # Config
        self.min_temp_difference = 0.2
        self.max_update_interval = 120 # Max update interval in seconds

        # Arguments
        self.enabled = self.args['enabled'] if 'enabled' in self.args else True
        self.entity_enabled = self.get_entity(self.args['entity_enabled']) if 'entity_enabled' in self.args else None
        self.entity_thermostat = self.get_entity(self.args['entity_thermostat'])
        self.entity_valve_position = self.get_entity(self.args['entity_valve_position'])

        self.update_interval = int(self.args['update_interval']) if 'update_interval' in self.args else -1
        self.max_temp_value = self.args['max_valve_position'] if 'max_valve_position' in self.args else 255
        self.temp_values = self.args['temp_values'] if 'temp_values' in self.args else None
        self.valve_compare_current_value = self.args['valve_compare_current_value'] if 'valve_compare_current_value' in self.args else False
        self.valve_always_update = self.args['valve_always_update'] if 'valve_always_update' in self.args else False

        # App
        if not self.enabled:
            self.log("ThermostatController disabled.")
            return

        if self.update_interval == -1:
            self.entity_thermostat.listen_state(self.update_valve_position)
            self.entity_thermostat.listen_state(self.update_valve_position, attribute="temperature")
            self.entity_thermostat.listen_state(self.update_valve_position, attribute="current_temperature")
        else:
            self.run_every(self.update_valve_position, start=f"now+{self.update_interval}", interval=self.update_interval)
        self.log("ThermostatController initialized!")


    def update_valve_position(self, entity=None, attribute=None, old=None, new=None, kwargs=None):
        # TODO check if everything is available

        # Check if controller is enabled
        if self.entity_enabled is not None and self.entity_enabled.is_state("off"):
            self.log("Controller is disabled.")
            return

        # Init values
        current_temp = self.entity_thermostat.get_state(attribute="current_temperature")
        target_temp = self.entity_thermostat.get_state(attribute="temperature")
        difference_last_temp = abs(current_temp - self.last_current_temp)

        # Check if temperature difference is too small (only if updated by current temp change)
        if attribute == "current_temperature":
            if difference_last_temp < self.min_temp_difference and current_temp < target_temp:
                self.log("Not updating valve position (temperature difference too small)")
                return

        valve_position = self.get_valve_position(target_temp, current_temp)

        update_valve_same_value = True
        if not self.valve_always_update:
            if self.valve_compare_current_value:
                current_valve_position = int(self.entity_valve_position.get_state())
                self.log(f"Current valve position: {current_valve_position}")
                update_valve_same_value = valve_position != current_valve_position
            else:
                update_valve_same_value = valve_position != self.last_valve_position

        if update_valve_same_value:
            self.entity_valve_position.set_state(state=valve_position)
            self.last_valve_position = valve_position
            self.log(f"New valve position: {valve_position}")
        else:
            self.log(f"Not updating valve position (already same value ({valve_position}))")

        self.last_current_temp = current_temp


    def get_valve_position(self, target_temp, current_temp):
        difference = target_temp - current_temp # How many degrees need to be heated
        self.log(f"Valve position calculation: Temp difference: {difference}")

        if self.temp_values is not None:
            for temp_value in self.temp_values:
                if difference <= float(temp_value['diff']):
                    return int(temp_value['value'])
        else:
            if difference <= 0.0:
                return 0

            if difference <= 0.1:
                return 20

            if difference <= 0.2:
                return 50

            if difference <= 0.5:
                return 80

            if difference <= 0.7:
                return 120

            if difference <= 1.0:
                return 160

            if difference <= 1.5:
                return 210

        return self.max_valve_position