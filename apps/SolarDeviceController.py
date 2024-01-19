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
    def __init__(self, ad, entity_id, consumption, enabled=False, enabled_by=None, min_cycle_duration=30):
        self.entity_id = entity_id
        self.consumption = consumption
        self.__enabled = enabled
        self.__enabled_by_id = enabled_by
        self.__min_cycle_duration = min_cycle_duration

        self.__ad = ad
        self.__entity = ad.get_entity(self.entity_id)
        self.__enabled_by = ad.get_entity(self.__enabled_by) if self.__enabled_by_id else None

    def is_wanted_state(self, state="on"):
        return self.__entity.get_state() == state

    def turn_on(self):
        self.__entity.turn_on()

    def turn_off(self):
        self.__entity.turn_off()

    def is_enabled(self):
        if not self.__enabled:
            return False

        if self.__enabled_by:
            return self.__enabled_by.get_state() == 'on'

        return True

    def passed_min_toggle_interval(self):
        last_changed_seconds = int(
            datetime.now().timestamp() -
            self.__ad.convert_utc(self.__entity.get_state(attribute="last_changed")).timestamp()
        )
        return last_changed_seconds > self.__min_cycle_duration

    def is_powered_on(self):
        return self.__entity.get_state() == 'on'


class SolarDeviceController(hass.Hass):
    """
    Controls devices based on solar production.

    """
    def initialize(self):
        self.log("Initializing SolarDeviceController")

        # Init global values from params
        self.debug = bool(self.args[s]) if (s := 'debug') in self.args else False

        self.production_sensor = self.get_entity(self.args['production_sensor'])
        self.consumption_sensor = self.get_entity(self.args['consumption_sensor'])
        self.battery_sensor = self.get_entity(self.args[s]) if (s := 'battery_percentage_sensor') in self.args else None
        self.excess_buffer = int(self.args[s]) if (s := 'excess_buffer') in self.args else 10
        self.enabling_battery_percentage = int(self.args[s]) if (s := 'enabling_battery_percentage') in self.args else 0
        self.enabling_switch = self.get_entity(self.args[s]) if (s := 'enabled_switch_id') in self.args else None

        # Init vars
        update_interval = int(self.args[s]) if (s := 'update_interval') in self.args else 10
        state_settle_time = int(self.args[s]) if (s := 'state_settle_time') in self.args else 60

        self.current_excess_state_timer = 0
        self.last_excess_state = ExcessState.NONE
        self.max_excess_state_timer = int(state_settle_time / update_interval)

        # Initialize devices
        self.devices = []
        raw_devices = self.args['devices']
        for device in raw_devices:
            self.devices.append(
                Device(
                    ad=self,
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
        self.run_every(self.loop, start=f"now+3", interval=update_interval)

        self.log("Initialization done!")

    def clog(self, msg):
        if self.debug:
            self.log(msg)

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
            else:
                for battery_state in self.battery_states:
                    # TODO check time ranges
                    in_time_range = True
                    if battery_percentage <= battery_state.percentage and in_time_range:
                        excess_power -= battery_state.min_charge_power
                        self.clog(f"Preserving {battery_state.min_charge_power}W excess power for the battery"
                                  f"(Current percentage: {battery_percentage}).")
                        break

        # Add consumption of already powered on devices to access (to prevent toggling on each update)
        for device in self.devices:
            if device.is_enabled() and device.is_powered_on():
                excess_power += device.consumption

        # Initialize last excess state
        if excess_power > 0:
            excess_state = ExcessState.POSITIVE_EXCESS
        elif excess_power < 0:
            excess_state = ExcessState.NEGATIVE_EXCESS
        else:
            excess_state = self.last_excess_state

        # Run excess state counter
        if self.last_excess_state == excess_state:
            if self.current_excess_state_timer < self.max_excess_state_timer:
                self.current_excess_state_timer += 1
        else:
            if self.current_excess_state_timer > 0:
                self.current_excess_state_timer -= 1

        # If timer has been finished (is back to 0)
        if self.current_excess_state_timer == 0:
            self.last_excess_state = excess_state

        # Send debug message
        self.clog(
            f"Excess power: {excess_power}; "
            f"State timer: {self.current_excess_state_timer}; "
            f"Current state: {excess_state}; "
            f"Last state: {self.last_excess_state}"
        )

        # Control devices (if last excess state is equal to current excess state)
        if self.last_excess_state == excess_state:
            for device in self.devices:
                excess_power -= self.control_device(device, excess_power)

            # This should nearly match the grid excess power if the battery is full (or if you don't have one).
            self.clog(f"Excess (controlled devices included): {excess_power}")
        else:
            self.clog("Not controlling any devices. Waiting for last and current excess state to get equal..")

    """
    Turns a device on or off based on the excess power.
    
    @returns the power usage of the device (0 if powered off)
    """
    def control_device(self, device, excess_power):
        if not device.is_enabled():
            return 0

        passed_min_toggle_interval = device.passed_min_toggle_interval()

        if device.consumption < excess_power:
            if device.is_wanted_state("on"):
                return device.consumption
            else:
                if passed_min_toggle_interval:
                    device.turn_on()
                    self.clog(f"Turned on device {device.entity_id}.")
                    return device.consumption
                else:
                    self.clog(f"Did not turn on device {device.entity_id} because of minimum toggle interval.")
                    return 0

        else:
            if device.is_wanted_state("off"):
                return 0
            else:
                if passed_min_toggle_interval:
                    device.turn_off()
                    self.clog(f"Turned off device {device.entity_id}.")
                    return 0
                else:
                    self.clog(f"Did not turn off device {device.entity_id} because of minimum toggle interval.")
                    return device.consumption
