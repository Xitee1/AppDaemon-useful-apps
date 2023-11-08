import hassapi as hass
from enum import Enum
from datetime import datetime, time


class LastExcessState(Enum):
    NONE = 0
    NEGATIVE_EXCESS = 1
    POSITIVE_EXCESS = 2


class Device:
    def __init__(self, name, consumption, enabled, enabled_state="on", min_cycle_duration=20):
        self.name = name
        self.consumption = consumption
        self.enabled = enabled
        self.enabled_state = enabled_state
        self.min_cycle_duration = min_cycle_duration


class SolarDeviceController(hass.Hass):
    """
    Preheat the wa

    Requirements:
    - Solar system with current production and consumption sensors
    - Devices as switch entity with a known and relatively stable consumption

    Optional:
    - Solar house battery with current charge/discharge rate and percentage sensors

    """
    def initialize(self):
        self.log("Initializing SolarDeviceController")

        # Init values
        self.debug = self.args['debug']

        self.production_sensor = self.get_entity(self.args['production_sensor'])
        self.consumption_sensor = self.get_entity(self.args['consumption_sensor'])
        self.battery_sensor = self.get_entity(self.args['battery_percentage_sensor'])
        self.check_interval = int(self.args['check_interval'])


        self.current_excess_state_timer = 0
        self.last_excess_state = LastExcessState.NONE

        # Get devices
        self.devices = []
        raw_devices = self.args['devices']
        for device in raw_devices:
            self.devices.append(
                Device(
                    name=device['name'],
                    consumption=int(device['consumption']),
                    enabled=device['enabled'],
                    enabled_state=device['enabled_state'],
                    min_cycle_duration=int(device['min_cycle_duration']),
                )
            )

        # Start loop
        self.run_every(self.loop, start=f"now+{self.check_interval}", interval=self.check_interval)

        self.log("Initialization finished!")

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
        if self.last_excess_state == excess_state and self.current_excess_state_timer >= self.power_on_wait_stable:
            for device in self.devices:
                excess_power -= self.control_device(device, excess_power)

            # TODO remove log
            self.mylog("Done: excess: " + str(excess_power))

    def update_device_state(self, device):
        if device.enabled_by is None:
            device.enabled = True
        else:
            device.enabled = self.get_state(device.enabled_by) == device.enabled_state

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
