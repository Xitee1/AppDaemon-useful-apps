# AppDaemon-useful-apps
These are all my AppDaemon apps that I have coded and use in my HomeAssistant.
The apps are made to fit in my specific case, but I try to make them configurable so others can use them too.

You can just download them and copy the ones you need into your 'apps' folder.

#### Some apps do require [fonts](apps/fonts/README.md).
#### Some apps do require [additional python packages](INSTALL_PY_PACKAGES.md).

### Important: These apps are in an early state and do not fully work yet.

### General Todo
- Move apps into their own folders and also create a README for all of them in that folder instead everything in the main README.

## ShowerController
#### Timeout not working yet. State is only changeable by pressing the button - no water is warm signal, no long showering alarm.
#### Example apps.yaml is out of date!
    Preheat the water, show the state of the heated water by the color of the light and when showering applying some cool effects to the light.
    Only with a few presses on a button.

    Requirements:
    - Switch for water heater ('switch.')
    - Any entity that changes its state (only!) when pressing the button (each, for short and long press)
    - LED strip in the shower running WLED
    - Script to set the light to a default mode
      In my case: After sunrise: Light goes off - After sunset: Light turn on at brightness level 1%

    How to use:
    - Press the button once to turn on the water heater. The light will shine blue to indicate the cold water.
      After a set delay, it will turn green to indicate that the water should be warm now.
    - Right before you go under the shower, press the button again to set the script to showering state.
      In this state the light will play the WLED showering playlist. Water heater stays on.
      After a set delay, the light will blink red to indicate that you should finish showering.
    - After you're done showering, press the button again. This will set the light to the default mode and turns
      off the water heater.
    - A long press cancels everything - Light will go into default mode and water heater will turn off.

    Required arguments:
    - short_press_sensor:
        A input_button that triggers when the button is pressed short.
    - long_press_sensor:
        A input_button that triggers when the button is pressed long.
    - water_heater_switch:
        The switch that will turn on the water heater.
    - led_strip_preset:
        The WLED preset 'select.' entity of the LED strip.
    - led_strip_playlist:
        The WLED playlist 'select.' entity of the LED strip.
    - led_strip_default_mode_script:
        A script that turns off the light.
        This is a script to allow some extra functions if you for example want to turn on the light at night at a low brightness level.
    - preset_water_warming:
        The preset name for the "water is warming"-state.
        E.g. a preset that lets the light shine blue.
    - preset_water_warm:
        The preset name for the "water is warm"-state.
        E.g. a preset that lets the light shine green.
    - playlist_showering:
        The playlist name for the "showering"-state.
        This playlist can be filled with cool effects that play while showering.
    - preset_showering_long:
        The preset name for the "showering long"-state.
        E.g. red blinks red.

    Optional arguments:
    - led_strip_controlled_by_script:
        This binary sensor will be set to on while the script is controlling the light. This allows you to use it as condition for other automations.
        Use any entity id for it that does not exist.
        Default: none
    - preheat_duration:
        How long the heater must be on so the state changes to "WATER_WARM". For example if your heater needs 10 minutes to make warm water, set it to 10.
        Default: 10
    - general_timeout_duration:
        If a state takes longer than this timeout, the app cancels, turns off the heater and the lights.
        Default: 20
    - time_to_shower_warning:
        When showering longer than the set minutes the light will switch to the "preset_showering_long" preset indicating that you should stop showering.
        Default: 10

## GenerateRoombaMap
#### TODO keep history of old maps instead deleting them
<img src="https://github.com/Xitee1/AppDaemon-useful-apps/assets/59659167/823517c2-d144-49ed-8333-e6b889889b78" height="300">

    Generates a map of the area cleaned by Roomba.

    To have the image in a camera entity:
    - Add the following to your configuration.yaml:
        camera:
          - platform: local_file
            name: Roomba Karte
            file_path: /config/www/tmp/vacuum_yourRobotName/map.png

    Requirements:
    - A vacuum that exposes its cords as attribute the following format: Position (x, x, x)
    - A floor plan of your home (// TODO make optional (but recommended) //)
    - pillow python package (Read INSTALL_PY_PACKAGES.md)
    - This app needs the "fonts" folder to work. // TODO For now, make sure the fonts are in the absolute path "/config/appdaemon/apps/fonts/Arimo-Bold.ttf"!! //

    Required arguments:
    - debug:
        Enable debug log
    - vacuum_entity:
        Your vacuum entity. E.g. 'vacuum.roomba'
    - vacuum_name:
        Used for naming the vacuum folders.
    - tmp_path:
        Path to a tmp folder where the log and image should be stored. E.g. /config/www/tmp
    - floor_plan_location:
        The file path of your floor plan. E.g. '/config/floorplans/home.png'
    - offset_cords_x:
        Adjust the offset so the generated lines match the floor plan
    - offset_cord_y:
        Adjust the offset so the generated lines match the floor plan
    - image_rotation:
        If the cords aren't drawn correctly to the map, you can try rotating the image (0, 90, 180, 270)

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