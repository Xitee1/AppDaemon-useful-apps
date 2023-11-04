import hassapi as hass
import datetime

class ThermostatController(hass.Hass):
    """
    App to control thermostat that can be directly controlled (valve position), like the Eurotronic Spirit/Comet.

    Required Arguments:
        - entity_thermostat:
            A HomeAssistant climate entity (dummy thermostat using generic_thermostat).
        - entity_valve_position:
            A HomeAssistant number entity of the valve position with a range of 0-255.
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
        self.entity_enabled = self.get_entity(self.args['enabled']) if 'enabled' in self.args else None
        self.entity_thermostat = self.get_entity(self.args['entity_thermostat'])
        self.entity_valve_position = self.get_entity(self.args['entity_valve_position'])

        # App
        self.entity_thermostat.listen_state(self.update_valve_position)
        self.entity_thermostat.listen_state(self.update_valve_position, attribute="temperature")
        self.entity_thermostat.listen_state(self.update_valve_position, attribute="current_temperature")
        self.log("ThermostatController initialized!")


    def add_execution_credit(self, kwargs=None):
        if self.execution_credits < self.max_execution_credits:
            self.execution_credits += 1

    def update_valve_position(self, attribute, entity=None, old=None, new=None, kwargs=None):
        # TODO check if everything is available

        # Check if controller is enabled
        if self.entity_enabled is not None and self.entity_enabled.is_state("off"):
            self.log("Controller is disabled.")
            return

        # Init values
        current_temp = self.entity_thermostat.get_state(attribute="current_temperature")
        target_temp = self.entity_thermostat.get_state(attribute="temperature")
        difference_last_temp = abs(current_temp - self.last_current_temp)

        # TODO bypass wait if attribute is not 'current_temperature'
        # Check if temperature difference is too small (only if updated by current temp change)
        if attribute == "current_temperature":
            if difference_last_temp < self.min_temp_difference and current_temp < target_temp:
                self.log("Not updating valve position (temperature difference too small)")
                return

        valve_position = self.get_valve_position(target_temp, current_temp)
        if valve_position != self.last_valve_position:
            self.entity_valve_position.set_state(state=valve_position)
            self.last_valve_position = valve_position
            self.log(f"New valve position: {valve_position}")
        else:
            self.log(f"Not updating valve position (already same value ({valve_position}))")

        self.last_current_temp = current_temp


    def get_valve_position(self, target_temp, current_temp):
        difference = target_temp - current_temp # How many degrees need to be heated
        self.log(f"Valve position calculation: Temp difference: {difference}")

        # TODO Make this definable per app instance
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

        return 255