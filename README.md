# AppDaemon-useful-apps
These are some of my AppDaemon apps that I have coded and use in my HomeAssistant.<br>
**The apps are all experimental and in an early state. Some of them are only for testing.
If an App is (nearly) ready for production, I will move it to into its own repo.**


You can just download them and copy the ones you need into your 'apps' folder.

#### Some apps might require [additional python packages](INSTALL_PY_PACKAGES.md).

### Check out my other apps:
- [RoombaMap](https://github.com/Xitee1/AD-RoombaMap)
- [ThermostatController](https://github.com/Xitee1/AD-ThermostatController)

# ShowerController
#### Timeout not working yet. State is only changeable by pressing the button - no water is warm signal, no long showering alarm.
#### Example apps.yaml is out of date!
    Preheat the water, show the state of the heated water by the color of the light and when showering apply some cool effects to the light.
    Only with a few presses on a button.

    Requirements:
    - A heater controllable by HA to preheat the bathroom
    - Any entity that changes its state to proceed the showering state (e.g. a button)
    - Any entity that changes its state to cancel the showering process (e.g. a button when a long-press is detected)
    - The showering script set up

    There are x states:
    - IDLE (1)
    - PREPARING (2)
    - READY (3)
    - IN_USE (4)
    - GET_OUT (5)
    The dafault state is IDLE. It should be configured to turn off everything showering related, e.g. the heater.
    When the triggering entity now changes its state, the state proceeds to PREPARING. This state should be used to
    turn on the heater etc. (prepareing the bathroom). After a configured timeout or if the configured entity
    'shower_prepare_state' changes its state to 'on', the app proceeds to READY. You should configure this step to
    indicate that the bathroom is ready to the user.
    So now, the bathroom should be prepared and the user also knows it.
    Next step is to go into the bathroom and take a shower. But right before you start, e.g. press the button once
    so that the app changes it state to IN_USE. If you want, you can configure this step to turn on an led strip
    with cool effects. Now the user has the configured timeout to take his shower. If the timeout is reached, you can
    indicate that to the user by e.g. turning the lights red. After the set timeout, the state will change to IDLE again.
    But you can also press the button once more after getting out to directly change to the IDLE state.

    Where can I configure all this?
    Just copy the template file into your HA config: /config/blueprints/script/Xitee/shower-controller.yaml
    and create a new script using this template. Configure the 'shower_script' option in the apps.yaml to point to
    the entity id of the script.

# RestChargeController
    Only allow charge/discharge, limit the battery percentage and slow charging if the battery gets nearly full to not wear it that much.
    Currently only works with house batteries for solar systems.

    Requirements:
    - The battery charge/discharge rate must be controllable by REST API
    - You need a sensor for (in W):
        - solar production
        - house consumption
        - current battery charge rate
        - current battery discharge rate
        - current battery percentage (in %)
    - You need the following input booleans:
        - Enable control (enabling the script)
        - Enable battery (when off, battery in/out will be disabled)
        - Limit percentage (if charging percentage should be limited)
        - Only charge (only allow charging but no discharging)
        - Only discharge (only allow discharging but no charging)
    - You need some input booleans in HA

    Example can be found in apps.yaml.

# SolarDeviceController
#### Not available yet, needs rewrite
    Control devices based on solar production, power consumption, battery percentage (optional) and time (optional)
    
    Requirements:
    - Sensor for current solar production (W), current power consumption (W), solar battery (%, optional)
    - Controlled device must be controllable by services turn_on/turn_off
    - Controlled devices need a rather constant consumption (Devices whose power supply varies a lot do not work well)
    - Need to know the average power consumption of the devices (for Example: 700W, 900W,...).
      It does not need smart plugs that measure the power consumption. These values must be hard-coded.