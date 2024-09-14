"""The MCP2221 component."""

import asyncio
from collections.abc import Coroutine
from typing import Any

import voluptuous as vol

from homeassistant.core import Event, HomeAssistant, ServiceCall
from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import async_get_platforms
from homeassistant.helpers.reload import async_integration_yaml_config
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import (
    CONF_SWITCHES,
    CONF_BINARY_SENSORS,
    CONF_SENSORS,
    CONF_DEVICE_CLASS,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_PIN,
    CONF_ICON,
    CONF_UNIQUE_ID,
    CONF_DEVICE_ID,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_VALUE_TEMPLATE,
    SERVICE_RELOAD,
    Platform,
    UnitOfInformation)

from homeassistant.components.binary_sensor import (
    DEVICE_CLASSES_SCHEMA as BINARY_SENSOR_DEVICE_CLASSES_SCHEMA,
    SCAN_INTERVAL as BINARY_SENSOR_DEFAULT_SCAN_INTERVAL,
)
from homeassistant.components.sensor import (
    DEVICE_CLASSES_SCHEMA as SENSOR_DEVICE_CLASSES_SCHEMA,
    SCAN_INTERVAL as SENSOR_DEFAULT_SCAN_INTERVAL,
    CONF_STATE_CLASS,
    STATE_CLASSES_SCHEMA as SENSOR_STATE_CLASSES_SCHEMA,
    SensorStateClass
)

from MCP2221 import MCP2221

from .const import (CONF_DEV, CONF_PID, CONF_VID,
                    CONF_INVERTED, CONF_ADC_REF, CONF_ADC, DOMAIN, LOGGER)

PLATFORM_MAPPING = {
    CONF_ADC: Platform.SENSOR,
    CONF_BINARY_SENSORS: Platform.BINARY_SENSOR,
    CONF_SWITCHES: Platform.SWITCH,
}

SENSOR_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_PIN): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=3), msg="invalid pin"
        ),
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Optional(
            CONF_SCAN_INTERVAL, default=SENSOR_DEFAULT_SCAN_INTERVAL
        ): vol.All(cv.time_period, cv.positive_timedelta),
        vol.Optional(CONF_ICON): cv.template,
        vol.Optional(CONF_DEVICE_CLASS): SENSOR_DEVICE_CLASSES_SCHEMA,
        vol.Optional(
            CONF_UNIT_OF_MEASUREMENT, default=UnitOfInformation.BITS
        ): cv.string,
        vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
        vol.Optional(
            CONF_STATE_CLASS, default=SensorStateClass.MEASUREMENT
        ): SENSOR_STATE_CLASSES_SCHEMA,
    },
    required=True,
)

ADC_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ADC_REF): vol.In(["VDD", 1.024, 2.048, 4.096]),
        vol.Required(CONF_SENSORS): [SENSOR_SCHEMA],
    },
    required=True,
)

BINARY_SENSOR_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_PIN): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=3), msg="invalid pin"
        ),
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Optional(CONF_INVERTED, default=False): cv.boolean,
        vol.Optional(
            CONF_SCAN_INTERVAL, default=BINARY_SENSOR_DEFAULT_SCAN_INTERVAL
        ): vol.All(cv.time_period, cv.positive_timedelta),
        vol.Optional(CONF_ICON): cv.template,
        vol.Optional(CONF_DEVICE_CLASS): BINARY_SENSOR_DEVICE_CLASSES_SCHEMA,
    },
    required=True,
)

SWITCH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_PIN): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=3), msg="invalid pin"
        ),
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Optional(CONF_ICON): cv.template,
    },
    required=True,
)

COMBINED_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_VID, default=0x04D8): cv.positive_int,
        vol.Optional(CONF_PID, default=0x00DD): cv.positive_int,
        vol.Optional(CONF_DEV, default=0): cv.positive_int,
        vol.Optional(CONF_SWITCHES): [SWITCH_SCHEMA],
        vol.Optional(CONF_BINARY_SENSORS): [BINARY_SENSOR_SCHEMA],
        vol.Optional(CONF_ADC): ADC_SCHEMA
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            cv.ensure_list,
            [COMBINED_SCHEMA],
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up MCP2221 from yaml config."""

    async def _reload_config(call: Event | ServiceCall) -> None:
        """Reload MCP2221."""
        reload_config = await async_integration_yaml_config(hass, DOMAIN)
        reset_platforms = async_get_platforms(hass, DOMAIN)

        for reset_platform in reset_platforms:
            LOGGER.debug("Reload resetting platform: %s",
                         reset_platform.domain)
            await reset_platform.async_reset()
        if not reload_config:
            LOGGER.warn("Nothing to reload")
            return
        await async_load_platforms(hass, reload_config.get(DOMAIN, []),
                                   reload_config)

    async_register_admin_service(hass, DOMAIN, SERVICE_RELOAD, _reload_config)

    await async_load_platforms(hass, config.get(DOMAIN, []), config)

    return True


async def async_load_platforms(
    hass: HomeAssistant,
    devices_config: list[dict[str, dict[str, Any]]],
    config: ConfigType,
) -> None:
    """Load platforms from yaml."""
    if not devices_config:
        return

    load_coroutines: list[Coroutine[Any, Any, None]] = []
    platforms: list[Platform] = []

    for device_id, device_config in enumerate(devices_config):
        """Init USB device class"""
        try:
            device = MCP2221.MCP2221(device_config.get(
                "vid"), device_config.get("pid"), device_config.get("dev"))

        except IndexError:
            LOGGER.error("Error opening MCP2221 device")
            return

        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}

        hass.data[DOMAIN][device_id] = {
            "device": device,
            "lock": asyncio.Lock()
        }

        for platform, platform_config in device_config.items():
            used_pins = set()

            # check only platforms, leaving the rest of setting
            if platform in PLATFORM_MAPPING:
                LOGGER.debug(
                    "Loading config %s for platform '%s'",
                    device_config.get(platform),
                    PLATFORM_MAPPING.get(platform),
                )

                # check for duplicate pins
                for item in (platform_config if platform != CONF_ADC else
                             platform_config.get(CONF_SENSORS)):
                    pin = item.get('pin')

                    if pin in used_pins:
                        LOGGER.error("Duplicate pin GP%i", pin)
                        raise ValueError("Duplicate pin found")
                    used_pins.add(pin)

                    # append device index
                    item[CONF_DEVICE_ID] = device_id

                platforms.append(PLATFORM_MAPPING.get(platform))

                load_coroutines.append(
                    discovery.async_load_platform(
                        hass,
                        PLATFORM_MAPPING.get(platform),
                        DOMAIN,
                        platform_config,
                        config,
                    )
                )

    if load_coroutines:
        await asyncio.gather(*load_coroutines)
