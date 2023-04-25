import hassapi as hass
from enum import Enum
import time


class ButtonAction(Enum):
    SHORT = 1
    LONG = 2


class ShowerController(hass.Hass):
    """
    Preheat the wa

    Requirements:
    - Solar system with current production and consumption sensors
    - Devices as switch entity with a known and relatively stable consumption

    Optional:
    - Solar house battery with current charge/discharge rate and percentage sensors

    TODO make better english

    Required arguments:
    - solar_production:
        A sensor with the current solar production power in W.
    - own_consumption:
        A sensor with the current power consumption.
    - has_battery:
        Set this to true if you have a battery and want to make this script a bit smarter.
    - battery_percentage:
        A sensor with the current battery percentage.
    - battery_target_percentage:
        Before this percentage is reached, the script leaves at least 'battery_max_charge' Watts for the battery to charge.
        This will make sure that the battery is charged before taking too much power. Because it could be the case that
        the sun shines really bright in the morning and the script will turn on all devices. But then is no power left to charge the battery.
        And if it begins to rain in the evening it will turn off the devices but the battery is still empty.

    - battery_max_charge:
        Specify the max input in W what your battery can handle.
        For example my battery can charge at max with 3400W. In this case, set this to: 34000
    - battery_min_charge:
        After the 'battery_target_percentage' is reached, the battery will charge with this wattage until it is at 98%.
        This value can be 0.
    - power_on_wait_stable:
        In minutes. Define how long there must be enough power for the devices before powering on.
        This value should be good balanced.
        This prevents that devices turn on for like only 2 min when there are quick power production spikes when it is very cloudy.
    - power_off_wait_stable:
        In minutes.
        This prevents that the devices turn off just because there is a cloud for 2 mins that reduces the production.
        You want this even with dumb heaters that don't care to be toggled often because this will wear and destroy your
        smart plug relays faster.
    """

    def initialize(self):
        print("Initializing ShowerController")

        self.debug = self.args['debug']


        self.get_entity(self.args['short_press_sensor']).listen_state(self.button_press_short)
        self.get_entity(self.args['long_press_sensor']).listen_state(self.button_press_long)

    def mylog(self, msg):
        if self.debug:
            self.log(msg)
