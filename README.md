# AppDaemon-useful-apps
These are all my AppDaemon apps that I have coded and use in my HomeAssistant.
The apps are made to fit in my specific case, but I try to make them configurable so others can use them too.

You can just download them and copy the ones you need into your 'apps' folder.

#### Some apps do require [fonts](apps/fonts/README.md).
#### Some apps do require [additional python packages](INSTALL_PY_PACKAGES.md).

### Important: These apps are in an early state and do not fully work yet.

## ShowerController
#### Timeout not working yet. State is only changeable by pressing the button - no water is warm signal, no long showering alarm.
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

## GenerateRoombaMap
#### TODO keep history of old maps instead deleting them
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

# SolarDeviceController
#### Not available yet, needs rewrite
    Control devices based on solar production, power consumption, battery percentage (optional) and time (optional)
    
    Requirements:
    - Sensor for current solar production (W), current power consumption (W), solar battery (%, optional)
    - Controlled device must be controllable by services turn_on/turn_off
    - Controlled devices need a rather constant consumption (Devices whose power supply varies a lot do not work well)
    - Need to know the average power consumption of the devices (for Example: 700W, 900W,...).
      It does not need smart plugs that measure the power consumption. These values must be hard-coded.
# BatteryChargeLimiter
#### Not available yet, needs rewrite
#### Originally developed for solar battery, it is planned to make this work for more battery types (for example Smartphone charger with Smart Plug)
    With this app you can limit the charge capacity of your batteries.
    For some batteries, this can also only allow charge or only allow discharge.
    
    # TODO
    Requirements:
    - Controllable battery
