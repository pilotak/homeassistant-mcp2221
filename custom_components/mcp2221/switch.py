"""MCP2221 switch"""

from datetime import datetime, timedelta
from typing import Any, cast

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.const import (
    CONF_PIN,
    CONF_NAME,
    CONF_UNIQUE_ID,
    CONF_DEVICE_ID
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.template import Template
from homeassistant.helpers.trigger_template_entity import ManualTriggerEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.config_entries import ConfigEntry

from .const import LOGGER, DOMAIN
from .MCP2221 import MCP2221


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Setup switches."""
    switches = []

    for object_id, switch in enumerate(discovery_info):
        LOGGER.info("Setting up switch: '%s' on pin GP%i",
                    switch.get(CONF_NAME), switch.get(CONF_PIN))
        trigger_entity_config = {
            CONF_UNIQUE_ID: switch.get(CONF_UNIQUE_ID),
            CONF_NAME: Template(switch.get(CONF_NAME, object_id), hass),
        }

        # get MCP2221 instance
        device_instance = hass.data[DOMAIN].get(switch.get(CONF_DEVICE_ID))

        if not isinstance(device_instance, MCP2221):
            LOGGER.error("No instance of MCP2221")
            return

        switches.append(
            MCP2221Switch(
                trigger_entity_config,
                device_instance,
                switch.get(CONF_PIN),
            )
        )

    async_add_entities(switches)


class MCP2221Switch(ManualTriggerEntity, SwitchEntity):
    """Representation of a switch."""

    def __init__(
        self,
        config: ConfigType,
        device: Any,
        pin: int
    ) -> None:
        """Initialize the switch."""
        super().__init__(self.hass, config)
        self._device_class = SwitchDeviceClass.SWITCH
        self._device = device
        self._pin = pin
        self._state = False

        # init GP
        self._device.InitGP(pin, 1)

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()

    @property
    def is_on(self):
        return self._state

    def turn_on(self, **kwargs):
        LOGGER.info("Turn on GP%i", self._pin)
        self._device.WriteGP(self._pin, 1)

        self._state = True

    def turn_off(self, **kwargs):
        LOGGER.info("Turn off GP%i", self._pin)
        self._device.WriteGP(self._pin, 0)

        self._state = False