import hassapi as hass
from enum import Enum
from datetime import datetime, time


class LastExcessState(Enum):
    NONE = 0
    NEGATIVE_EXCESS = 1
    POSITIVE_EXCESS = 2


class Device:
    def __init__(self, entity_id, consumption, enabled=False, enabled_by=None, enabled_state="on", min_cycle_duration=30):
        self.entity_id = entity_id
        self.consumption = consumption
        self.enabled = enabled
        self.enabled_by = enabled_by
        self.enabled_state = enabled_state
        self.min_cycle_duration = min_cycle_duration
        self.powered_on = False


class SolarDeviceController(hass.Hass):
    """
    Controls devices based on solar production.

    TODO Include battery percentage in calculations.

    """
    def initialize(self):
        self.log("Initializing SolarDeviceController")

        self.current_excess_state_timer = 0
        self.last_excess_state = LastExcessState.NONE

        # Init values from params
        self.debug = self.args['debug']

        self.production_sensor = self.get_entity(self.args['production_sensor'])
        self.consumption_sensor = self.get_entity(self.args['consumption_sensor'])
        self.battery_sensor = self.get_entity(self.args['battery_percentage_sensor']) if 'battery_percentage_sensor' in self.args else None
        self.battery_min_percentage = int(self.args['battery_min_percentage']) if 'battery_min_percentage' in self.args else 0
        self.excess_buffer = int(self.args['excess_buffer'])

        # Get devices
        self.devices = []
        raw_devices = self.args['devices']
        for device in raw_devices:
            self.devices.append(
                Device(
                    entity_id=device['entity'],
                    consumption=int(device['consumption']),
                    enabled=device['enabled'] if 'enabled' in device else True,
                    enabled_by=device['enabled_by'] if 'enabled_by' in device else None,
                    enabled_state=device['enabled_state'] if 'enabled_state' in device else 'on',
                    min_cycle_duration=int(device['min_cycle_duration']) if 'min_cycle_duration' in device else 30,
                )
            )

        # Start loop
        self.run_every(self.loop, start=f"now+3", interval=1)

        self.log("Initialization finished!")

    """
    The loops needs to be called exactly every second in order to work correctly.
    """
    def loop(self, entity=None, attribute=None, old=None, new=None, kwargs=None):
        production = int(self.production_sensor.get_state())
        consumption = int(self.consumption_sensor.get_state())
        excess_power = (production - consumption) + self.excess_buffer

        if self.battery_sensor:
            battery_percentage = int(self.battery_sensor.get_state())
            if battery_percentage < self.battery_min_percentage:
                excess_power = -1

        for device in self.devices:
            device.enabled = self.get_state(device.enabled_by) == device.enabled_state
            if device.enabled and device.powered_on:
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
            # Add some buffer. For example afternoons the production is since 100 seconds 150W below the consumption
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

        self.log(f"Excess power: {excess_power}; current_state_timer: {self.current_excess_state_timer}; excess_state: {self.last_excess_state}")

        # Control devices
        if self.last_excess_state == excess_state:
            for device in self.devices:
                if self.current_excess_state_timer >= device.min_cycle_duration:
                    excess_power -= self.control_device(device, excess_power)

            self.log(f"Excess: {excess_power}")

    """
    Turns a device on or off based on the excess power.
    
    @returns the power usage of the device (0 if powered off)
    """
    def control_device(self, device, excess_power):
        if not device.enabled:
            return 0

        device_entity = self.get_entity(device.entity_id)
        device_state = device_entity.get_state()

        last_changed_seconds = int(datetime.now().timestamp() - self.convert_utc(device_entity.get_state(attribute="last_changed")).timestamp())
        if last_changed_seconds < device.min_cycle_duration:
            self.log(f"Did not toggle device {device.entity_id} because of minimum toggle interval.")
            return 0

        power_on = False
        if device.consumption < excess_power:
            power_on = True

        if power_on:
            power_usage = device.consumption
            if device_state == 'off':
                device_entity.turn_on()
                device.powered_on = True
        else:
            power_usage = 0
            if device_state == 'on':
                device_entity.turn_off()
                device.powered_on = False

        self.log(f"Checked device {device.entity_id}. Power usage: {power_usage}")

        return power_usage
