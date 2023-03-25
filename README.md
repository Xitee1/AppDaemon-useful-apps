# AppDaemon-useful-apps
These are all my AppDaemon apps that I have coded and use in my HomeAssistant.
The apps are made to fit in my specific case, but I try to make them configurable so others can use them too.

You can just download them and copy the ones you need into your 'apps' folder.

### Important: These apps are in an early state and do not fully work yet.
ShowerController _works_ so far, but without the timeout to automatically skip to the next state.<br>
GenerateRoombaMap also _works_ but needs a rewrite _again_ .. (This is already the 3th revision, started with a custom hass addon copied from dorita980 - but I'm getting closer)

## ShowerController
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