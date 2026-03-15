# SmartyPlants for Home Assistant

An unofficial Home Assistant custom integration for [SmartyPlants](https://www.smartyplants.co.uk/) plant sensors. Pulls sensor readings from the SmartyPlants cloud API and creates devices for each of your plants.

## What you get

Each plant with an assigned sensor becomes a device in Home Assistant with the following entities:

| Entity          | Type          | Unit | Notes                              |
| --------------- | ------------- | ---- | ---------------------------------- |
| Temperature     | Sensor        | °C   |                                    |
| Humidity        | Sensor        | %    |                                    |
| Soil moisture   | Sensor        | %    | VWC (Volumetric Water Content)     |
| Light           | Sensor        | lx   |                                    |
| Battery         | Sensor        | %    | Diagnostic                         |
| Needs attention | Binary sensor |      | Matches the SmartyPlants app alert |

There are also optional status sensors (temperature status, humidity status, etc.) that show the SmartyPlants assessment for each reading - "Optimal", "Low", "Slightly high", etc. These are disabled by default and can be toggled on or off in the integration options.

Each numeric sensor also exposes `status` and `status_message` as state attributes, where `status_message` is the human-friendly text from the API (e.g. "Healthy and thriving", "Too wet").

Devices are named after your plants, with the species shown as the full binomial name (e.g. "Pachira aquatica"). If your plant has an environment set in SmartyPlants (e.g. "Living Room"), it will be suggested as the Home Assistant area.

Plants without an assigned sensor are ignored.

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Click the three dots in the top right, then "Custom repositories"
3. Add `https://github.com/rexxars/ha-smartyplants` as an "Integration"
4. Search for "SmartyPlants" in HACS and install it
5. Restart Home Assistant

### Manual

Copy the `custom_components/smartyplants` folder into your Home Assistant `config/custom_components/` directory and restart.

## Setup

Go to **Settings > Devices & Services > Add Integration** and search for "SmartyPlants". Sign in with the same email and password you use in the SmartyPlants app.

Your password is only used during login to get an access token - it's not stored.

## Options

After setup, click "Configure" on the integration to change:

- **Polling interval** - How often to check for new readings (default: 15 minutes, minimum: 5 minutes)
- **Show plant status sensors** - Enable the status sensors that show SmartyPlants' reading assessments

## Using with the Plant integration

You can optionally feed the sensors into Home Assistant's built-in [Plant integration](https://www.home-assistant.io/integrations/plant/) to get a combined plant status card:

```yaml
plant:
  monstera:
    sensors:
      moisture: sensor.monstera_soil_moisture
      temperature: sensor.monstera_temperature
      brightness: sensor.monstera_light
      battery: sensor.monstera_battery
    min_moisture: 20
    max_moisture: 80
```

Note that the Plant integration has its own thresholds (separate from the ones the SmartyPlants API provides), and it only supports a subset of sensors - humidity is not one of them.

## How it works

The integration polls the SmartyPlants API on the configured interval. It fetches all your plants and their latest sensor data, plus which plants currently need attention. If the access token expires, it refreshes automatically. If the refresh token expires, you'll get a re-authentication prompt.

## Requirements

- Home Assistant 2025.2.0 or later
- A SmartyPlants account with at least one plant that has a sensor assigned

## Disclaimer

This project is not affiliated with, endorsed by, or connected to SmartyPlants LTD. It uses the same API as the SmartyPlants mobile app, which could change without notice.

## License

MIT-licensed. See LICENSE.
