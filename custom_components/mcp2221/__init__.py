"""The command_line component."""
from __future__ import annotations

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
    CONF_SWITCHES, CONF_NAME, CONF_PIN, CONF_UNIQUE_ID, CONF_DEVICE_ID,
    SERVICE_RELOAD, Platform)

from .MCP2221 import MCP2221

from .const import (CONF_DEV, CONF_PID, CONF_VID, DOMAIN, LOGGER)

BINARY_SENSOR_DEFAULT_NAME = "Binary Command Sensor"
DEFAULT_PAYLOAD_ON = "ON"
DEFAULT_PAYLOAD_OFF = "OFF"
CONF_JSON_ATTRIBUTES = "json_attributes"
SENSOR_DEFAULT_NAME = "Command Sensor"
CONF_NOTIFIERS = "notifiers"

PLATFORM_MAPPING = {
    CONF_SWITCHES: Platform.SWITCH,
}

SWITCH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_PIN): cv.positive_int,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    },
    required=True,
)
COMBINED_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_VID, default=0x04D8): cv.positive_int,
        vol.Optional(CONF_PID, default=0x00DD): cv.positive_int,
        vol.Optional(CONF_DEV, default=0): cv.positive_int,
        vol.Optional(CONF_SWITCHES): [SWITCH_SCHEMA],
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
        await async_load_platforms(hass, reload_config.get(DOMAIN, []), reload_config)

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
        device = MCP2221(device_config.get(
            "vid"), device_config.get("pid"), device_config.get("dev"))

        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}

        hass.data[DOMAIN][device_id] = device

        for platform, platform_config in device_config.items():
            seen_pins = set()

            # check only platforms, leaving the rest of setting
            if platform in PLATFORM_MAPPING:
                LOGGER.debug(
                    "Loading config %s for platform '%s'",
                    device_config.get(platform),
                    PLATFORM_MAPPING.get(platform),
                )

                # check for duplicate pins
                for item in platform_config:
                    pin = item.get('pin')
                    if pin in seen_pins:
                        LOGGER.error("Duplicate pin GP%i", pin)
                        raise ValueError("Duplicate pin found")
                    seen_pins.add(pin)

                # append device index
                for item in platform_config:
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
