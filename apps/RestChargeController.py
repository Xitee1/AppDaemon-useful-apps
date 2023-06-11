import hassapi as hass
import requests

# Variables
block_battery = False


class RestChargeController(hass.Hass):

    def initialize(self):
        self.debug_enabled              = self.args['debug']

        self.sensor_battery_percentage  = self.args['sensor_battery_percentage']
        self.sensor_production          = self.args['sensor_production']
        self.sensor_consumption         = self.args['sensor_consumption']
        self.switch_enable_control      = self.args['switch_enable_control']
        self.switch_enable_battery      = self.args['switch_enable_battery']
        self.switch_limit_percentage    = self.args['switch_limit_percentage']
        self.switch_only_charge         = self.args['switch_only_charge']
        self.switch_only_discharge      = self.args['switch_only_discharge']

        self.battery_charge_limit       = self.args['battery_charge_limit']
        self.battery_recharge_threshold = self.args['battery_recharge_threshold']

        self.url_discharge              = self.args['url_discharge']
        self.url_charge                 = self.args['url_charge']
        self.url_headers                = self.args['url_headers']
        self.refresh_interval           = self.args['refresh_interval']

        # Run all x seconds
        self.run_every(self.loop, start="now+2", interval=self.refresh_interval)

    def mylog(self, text):
        if self.debug_enabled:
            self.log("(DEBUG) " + text)

    def block_battery(self):
        self.charge_battery(0)

    """
    power: negative = discharge; positive = charge
    """
    def charge_battery(self, power):
        if power > 0:
            self.mylog("Charging battery with {} W.".format(str(power)))
            request = requests.post(self.url_charge.format(str(power)), headers=self.url_headers)
        else:
            power = abs(power)  # This device only accepts positive numbers (url needs to be changed for charge/discharge)
            self.mylog("Discharging battery with {} W.".format(str(power)))
            request = requests.post(self.url_discharge.format(str(power)), headers=self.url_headers)

    def loop(self, kwargs=None):
        self.mylog("----------")
        # Cancel if this script is disabled
        if self.get_state(self.switch_enable_control) == 'off':
            self.mylog("Battery-Script is disabled.")
            return

        # Block charge/discharge battery if battery is disabled
        if self.get_state(self.switch_enable_battery) == 'off':
            self.mylog("Battery is disabled.")
            self.block_battery()
            return

        # Battery control is active - initialize sensors
        battery_percentage = int(self.get_state(self.sensor_battery_percentage))
        production = int(self.get_state(self.sensor_production))
        consumption = int(self.get_state(self.sensor_consumption))

        # TODO
        """
        # Block charge/discharge battery if percentage is limited
        if self.get_state(self.switch_limit_percentage) == 'on':
            if battery_percentage >= self.battery_charge_limit:


            # Limit charging level
            if self.get_state(switch_limit_charge) == 'on' and production > consumption:
                anyStepExecuted = True
                if battery_percentage >= charge_limit:
                    block_battery = True

                if battery_percentage <= charge_again:
                    block_battery = False
        """

        # Prevent discharging (only allow charge)
        if self.get_state(self.switch_only_charge) == 'on':
            if production <= consumption:
                self.mylog("Battery is not allowed to discharge.")
                self.block_battery()
                return

        # Prevent charging (only allow discharge)
        if self.get_state(self.switch_only_discharge) == 'on':
            if production >= consumption:
                self.mylog("Battery is not allowed to charge.")
                self.block_battery()
                return

        # If this point in the script is reached, there are no more restrictions.
        # Battery can be freely controlled now.
        # TODO charge slower if percentage is high
        # TODO smooth out battery charging (do not allow instantaneous (example) switch from charging with 2000W to discharging 2000W, which would be a 4000W difference)
        # TODO slower charging in the morning (somehow check if it is a sunny day). In the winter most of the time all power is needed that it can get. But if it's a sunny day it has enough time to charge slower.
        self.charge_battery(production - consumption)

        self.mylog("----------")