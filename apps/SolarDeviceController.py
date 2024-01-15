import hassapi as hass
from enum import Enum
from datetime import datetime, time


class ExcessState(Enum):
    NONE = 0
    NEGATIVE_EXCESS = 1
    POSITIVE_EXCESS = 2


class BatteryState:
    def __init__(self, percentage, start, end, min_charge_power):
        self.percentage = percentage
        self.start = start
        self.end = end
        self.min_charge_power = min_charge_power

class Device:
    def __init__(self, entity_id, consumption, enabled=False, enabled_by=None, min_cycle_duration=30):
        self.entity_id = entity_id
        self.consumption = consumption
        self.__enabled = enabled
        self.__enabled_by_id = enabled_by
        self.__min_cycle_duration = min_cycle_duration

        self.__entity = self.get_entity(self.entity_id)
        self.__enabled_by = self.get_entity(self.__enabled_by) if self.__enabled_by_id else None

    def turn_on(self):
        if device_state == 'off':
            device_entity.turn_on()
            device.powered_on = True
            return True
        return False

    def turn_off(self):
        if device_state == 'on':
            device_entity.turn_off()
            device.powered_on = True
            return True
        return False

    def is_enabled(self):
        if not self.__enabled:
            return False

        if self.__enabled_by:
            return self.__enabled_by.get_state() == 'on'

        return True

    def passed_min_toggle_interval(self):
        last_changed_seconds = int(datetime.now().timestamp() -
                                   self.convert_utc(self.__entity.get_state(attribute="last_changed")).timestamp())
        return last_changed_seconds > device.min_cycle_duration

    def is_powered_on(self):
        return self.__entity.get_state() == 'on'



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
        self.excess_buffer = int(self.args['excess_buffer']) if 'excess_buffer' in self.args else 10
        self.enabling_battery_percentage = int(self.args['enabling_battery_percentage']) if 'enabling_battery_percentage' in self.args else 0
        self.update_interval = int(self.args['update_interval']) if 'update_interval' in self.args else 10

        # Initialize devices
        self.devices = []
        raw_devices = self.args['devices']
        for device in raw_devices:
            self.devices.append(
                Device(
                    entity_id=device['entity'],
                    consumption=int(device['consumption']),
                    enabled=device['enabled'] if 'enabled' in device else True,
                    enabled_by=device['enabled_by'] if 'enabled_by' in device else None,
                    min_cycle_duration=int(device['min_cycle_duration']) if 'min_cycle_duration' in device else 30,
                )
            )

        # Initialize battery states
        self.battery_states = []
        if self.battery_sensor:
            raw_battery_states = self.args['battery_states']
            for raw_battery_state in raw_battery_states:
                self.battery_states.append(
                    BatteryState(
                        percentage=int(raw_battery_state['percentage']),
                        start=raw_battery_state['start'] or '00:00',
                        end=raw_battery_state['end'] or '23:59',
                        min_charge_power=int(raw_battery_state['min_charge_power'])
                    )
                )

        # Start loop
        self.run_every(self.loop, start=f"now+3", interval=1)

        self.log("Initialization done!")

    """
    The loops needs to be called exactly every second in order to work correctly.
    """
    def loop(self, entity=None, attribute=None, old=None, new=None, kwargs=None):
        production = int(self.production_sensor.get_state())
        consumption = int(self.consumption_sensor.get_state())
        excess_power = (production - consumption) + self.excess_buffer

        # Set excess to -1 if battery percentage below 'enabling_battery_percentage' (powers off all devices)
        if self.battery_sensor:
            battery_percentage = int(self.battery_sensor.get_state())
            if battery_percentage < self.enabling_battery_percentage:
                excess_power = -1

        # Add consumption of already powered on devices to access (to prevent toggling on each update)
        for device in self.devices:
            if device.is_enabled() and device.is_powered_on():
                excess_power += device.consumption

        # Set last excess state
        if excess_power > 0:
            excess_state = ExcessState.POSITIVE_EXCESS
        elif excess_power < 0:
            excess_state = ExcessState.NEGATIVE_EXCESS
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
                excess_power -= self.control_device(device, excess_power)

            self.log(f"Excess: {excess_power}")

    """
    Turns a device on or off based on the excess power.
    
    @returns the power usage of the device (0 if powered off)
    """
    def control_device(self, device, excess_power):
        if not device.is_enabled():
            return 0

        if not device.passed_min_toggle_interval():
            self.log(f"Did not toggle device {device.entity_id} because of minimum toggle interval.")
            return 0

        if device.consumption < excess_power:
            if device.turn_on():
                self.log(f"Turned on device {device.entity_id}.")
            return device.consumption
        else:
            if device.turn_off():
                self.log(f"Turned off device {device.entity_id}.")
            return 0
