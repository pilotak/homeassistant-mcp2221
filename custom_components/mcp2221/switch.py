"""MCP2221 switch"""

from asyncio import Lock
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import (
    CONF_PIN,
    CONF_NAME,
    CONF_ICON,
    CONF_UNIQUE_ID,
    CONF_DEVICE_ID
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.template import Template
from homeassistant.helpers.trigger_template_entity import ManualTriggerEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import LOGGER, DOMAIN
from MCP2221 import MCP2221


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

        name: str = Template(switch.get(CONF_NAME, object_id), hass)
        icon: Template | None = switch.get(CONF_ICON)
        unique_id: str | None = switch.get(CONF_UNIQUE_ID)

        trigger_entity_config = {
            CONF_UNIQUE_ID: unique_id,
            CONF_NAME: name,
            CONF_ICON: icon
        }

        # get MCP2221 instance

        device_instance = hass.data[DOMAIN].get(
            switch.get(CONF_DEVICE_ID))

        if not isinstance(device_instance["device"], MCP2221.MCP2221):
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
        device,
        pin: int
    ) -> None:
        """Initialize the switch."""
        super().__init__(self.hass, config)
        self._device: MCP2221.MCP2221 = device["device"]
        self._lock: Lock = device["lock"]
        self._pin = pin

        # init GP
        self._state = prev_state = False

        if self._device.GetGPType(self._pin) == MCP2221.TYPE.OUTPUT:
            # if already an output init prev state directly
            prev_state = bool(self._device.ReadGP(self._pin))
            self._state = prev_state

        self._device.InitGP(pin, MCP2221.TYPE.OUTPUT, prev_state)

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()

    @property
    def is_on(self):
        return self._state

    async def async_turn_on(self, **kwargs):
        LOGGER.info("Turn on GP%i", self._pin)
        try:
            async with self._lock:
                self._device.WriteGP(self._pin, 1)
                self._state = True
        except OSError:
            LOGGER.error("Device not available")
            self._state = None

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        LOGGER.info("Turn off GP%i", self._pin)
        try:
            async with self._lock:
                self._device.WriteGP(self._pin, 0)
                self._state = False
        except OSError:
            LOGGER.error("Device not available")
            self._state = None

        self.async_write_ha_state()
