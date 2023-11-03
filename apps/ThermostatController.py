import hassapi as hass
from appdaemon.exceptions import TimeOutException
import datetime as datetime


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
        self.last_execution_time = datetime.now()
        self.last_valve_position = None

        # Config
        self.min_temp_difference = 0.2
        self.max_update_interval = 120 # Max update interval in seconds

        # Arguments
        self.entity_thermostat = self.get_entity(self.args['entity_thermostat'])
        self.entity_valve_position = self.get_entity(self.args['entity_valve_position'])

        # App
        self.entity_thermostat.listen_state(self.update_valve_position)
        self.run_every(self.update_valve_position, start="now+2", interval=self.max_update_interval)
        self.log("ThermostatController initialized!")

    def log(self, msg):
        if self.debug:
            self.log(msg)


    def update_valve_position(self, entity=None, attribute=None, old=None, new=None, kwargs=None):
        time_difference = datetime.now() - self.last_execution_time
        if time_difference.total_seconds() >= self.max_update_interval:
            self.log("Not updating valve position (updated less than 2 minutes ago)")
            return


        current_temp = self.entity_thermostat.get_state(attribute="current_temperature")
        target_temp = self.entity_thermostat.get_state(attribute="temperature")
        difference_last_temp = abs(current_temp - self.last_current_temp)

        if difference_last_temp >= self.min_temp_difference:
            valve_position = self.get_valve_position(target_temp, current_temp)

            if valve_position != self.last_valve_position:
                self.entity_valve_position.set_state(state=valve_position)
                self.log(f"New valve position: {valve_position}")
            else:
                self.log("Not updating valve position (already same value)")

        else:
            self.log("Not updating valve position (temperature difference too small)")

        self.last_current_temp = current_temp


    def get_valve_position(self, target_temp, current_temp):
        difference = target_temp - current_temp # How many degrees need to be heated

        # TODO Make this definable per app instance:
        if difference <= 0.1:
            return 0

        if difference >= 0.2:
            return 55

        if difference >= 0.5:
            return 130

        if difference >= 1.0:
            return 190

        if difference >= 1.5:
            return 210

        return 255