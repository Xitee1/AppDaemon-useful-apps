### Install additional python packages in AppDaemon (HomeAssistant-Addon)
Some apps might require extra packages.<br>
You can easily add additional python packages in AppDaemon (HomeAssistant).

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