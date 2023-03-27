### Install additional python packages in AppDaemon (HomeAssistant-Addon)
You can install additional python packages in AppDaemon.
Some of my apps require additional packages. For example GenerateRoombaMap.<br>
They are listed in the requirements in each of my apps when they are needed.

### How to install
<a href="https://my.home-assistant.io/redirect/supervisor_addon/?addon=a0d7b954_appdaemon" target="_blank"><img src="https://my.home-assistant.io/badges/supervisor_addon.svg" alt="Open your Home Assistant instance and show the dashboard of a Supervisor add-on." /></a><br>
Go to your HomeAssistant Settings -> Add-ons -> AppDaemon -> Configuration -> 3 dots -> Edit as YAML

By default your config should look like this:
```yaml
init_commands: []
python_packages: []
system_packages: []
```
Just add all the needed packages as a list to "python_packages":
```yaml
init_commands: []
python_packages:
  - pillow
system_packages: []
```