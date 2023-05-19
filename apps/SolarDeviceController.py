import hassapi as hass
from enum import Enum
from datetime import datetime, time


class LastExcessState(Enum):
    NONE = 0
    NEGATIVE_EXCESS = 1
    POSITIVE_EXCESS = 2


class Device:
    def __init__(self, name, consumption, minimum_toggle_interval=20):
        self.name = name
        self.consumption = consumption
        self.minimum_toggle_interval = minimum_toggle_interval

        self.enabled = False


class SolarDeviceController(hass.Hass):
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
    - solar_consumption:
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
        In seconds. Define how long there must be enough power for the devices before powering on.
        This value should be good balanced.
        This prevents that devices turn on for like only 2 min when there are quick power production spikes when it is very cloudy.
    - power_off_wait_stable:
        In seconds.
        This prevents that the devices turn off just because there is a cloud for 2 mins that reduces the production.
        You want this even with dumb heaters that don't care to be toggled often because this will wear and destroy your
        smart plug relays faster.
    """
    def initialize(self):
        print("Initializing SolarDeviceController")
        self.debug = self.args['debug']

        self.power_on_wait_stable = int(self.args['power_on_wait_stable'])
        self.power_off_wait_stable = int(self.args['power_off_wait_stable'])

        self.solar_production_sensor = self.get_entity(self.args['solar_production'])
        self.solar_consumption_sensor = self.get_entity(self.args['solar_consumption'])

        self.current_excess_state_timer = 0
        self.last_excess_state = LastExcessState.NONE

        # TODO load devices from apps.yaml
        # Optional parameters: minimum_toggle_interval - In seconds; Default: 20
        self.devices = {
            Device(name="switch.heizteppich_kuche", consumption=300),
            Device(name="switch.heizteppich_esszimmer", consumption=660),
            Device(name="switch.heizung_bad_unten", consumption=900),
            Device(name="switch.heizung_werkstatt", consumption=1500),
        }

        print("Initialization finished!")

        # Start loop
        self.run_every(self.loop, start="now+3", interval=1)

    def mylog(self, msg):
        if self.debug:
            self.log(msg)

    """
    The loops needs to be called exactly every second in order to work correctly.
    """
    def loop(self, entity=None, attribute=None, old=None, new=None, kwargs=None):
        production = int(self.solar_production_sensor.get_state())
        consumption = int(self.solar_consumption_sensor.get_state())

        # Buffer for excess power.
        # Examples:
        # 200  -> adds 200W to excess power
        # -200 -> virtually consumes 200W (removes 200W from excess power)
        buffer = 0

        excess_power = (production - consumption) + buffer

        for device in self.devices:
            self.update_device_state(device)

            if device.enabled and self.get_state(device.name) == "on":
                excess_power += device.consumption

        if excess_power > 0:
            excess_state = LastExcessState.POSITIVE_EXCESS
        elif excess_power < 0:
            excess_state = LastExcessState.NEGATIVE_EXCESS
        else:
            excess_state = self.last_excess_state

        if self.last_excess_state == excess_state:
            self.current_excess_state_timer += 1
        else:
            # Add some buffer. For example afternoons the productions is since 100 seconds 150W below the consumption
            # while it is cloudy. But if the sun passes through a cloud for like 5 seconds and after that the production
            # again is 150W below consumption the timer is completely reset and the devices will consume that power
            # even longer. Because of that we do not instantly set it to 0, but we divide the current timer by 10 and
            # remove that value from it. This means the timer gets reduced a lot and will be at 0 after around 10 secs
            # but will not instantly set to 0.
            # factor: lower = faster; higher value = slower
            factor = 10
            amount = int((self.current_excess_state_timer / factor))
            if amount < factor:
                amount = factor
            self.current_excess_state_timer -= amount
            if self.current_excess_state_timer <= 5:
                self.current_excess_state_timer = 0

        if self.current_excess_state_timer == 0:
            self.last_excess_state = excess_state

        # TODO remove log
        self.mylog("Looping. Excess power: " + str(excess_power) + "; current_state_timer: "+str(self.current_excess_state_timer)+"; excess_state: " + str(self.last_excess_state))

        # Control devices if excess is positive and the state is positive for at least "power_on_wait_stable"
        if self.current_excess_state_timer >= self.power_on_wait_stable:
            for device in self.devices:
                excess_power -= self.control_device(device, excess_power)

            # TODO remove log
            self.mylog("Done: excess: " + str(excess_power))

    def update_device_state(self, device):
        if self.get_state("input_boolean.solar_automatik_" + device.name.split('.')[1]) == 'on':
            device.enabled = True
        else:
            device.enabled = False

    """
    Turns a device on or off based on the excessPower.
    
    @returns an integer:
    >  0: Device is on
    == 0: Device is off
    """
    def control_device(self, device, excess_power):
        if not device.enabled:
            return 0

        device_entity = self.get_entity(device.name)
        device_state = device_entity.get_state()

        last_changed_seconds = int(datetime.now().timestamp() - self.convert_utc(self.get_entity(device.name).get_state(attribute="last_changed")).timestamp())
        if last_changed_seconds < device.minimum_toggle_interval:
            self.mylog("Did not control device "+device.name+" because of minimum toggle interval.")
            return 0

        power_on = False
        if device.consumption < excess_power:
            power_on = True

        power_usage = 0

        if power_on:
            power_usage = device.consumption
            if device_state == 'off':
                device_entity.turn_on()
        else:
            if device_state == 'on':
                device_entity.turn_off()

        # TODO remove log
        self.mylog("Controlled the device "+str(device.name)+". Power usage: " + str(power_usage))

        return power_usage
