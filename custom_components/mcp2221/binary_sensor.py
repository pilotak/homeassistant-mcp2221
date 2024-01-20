"""MCP2221 binary sensor"""

from datetime import datetime, timedelta
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity
)
from homeassistant.const import (
    CONF_PIN,
    CONF_NAME,
    CONF_UNIQUE_ID,
    CONF_DEVICE_ID,
    CONF_ICON,
    CONF_DEVICE_CLASS,
    CONF_SCAN_INTERVAL
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.template import Template
from homeassistant.helpers.trigger_template_entity import ManualTriggerEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.event import async_track_time_interval

from .const import (CONF_INVERTED, LOGGER, DOMAIN)
from MCP2221 import MCP2221


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Setup binary sensors."""
    binary_sensors = []

    for binary_sensor in discovery_info:
        LOGGER.info("Setting up binary_sensor: '%s' on pin GP%i",
                    binary_sensor.get(CONF_NAME), binary_sensor.get(CONF_PIN))

        name: str = binary_sensor.get(CONF_NAME)
        device_class: BinarySensorDeviceClass | None = binary_sensor.get(
            CONF_DEVICE_CLASS
        )
        scan_interval: timedelta = binary_sensor.get(CONF_SCAN_INTERVAL)
        icon: Template | None = binary_sensor.get(CONF_ICON)
        unique_id: str | None = binary_sensor.get(CONF_UNIQUE_ID)
        pin: int = binary_sensor.get(CONF_PIN)
        inverted: bool = binary_sensor.get(CONF_INVERTED)

        trigger_entity_config = {
            CONF_UNIQUE_ID: unique_id,
            CONF_NAME: Template(name, hass),
            CONF_DEVICE_CLASS: device_class,
            CONF_ICON: icon,
        }

        # get MCP2221 instance
        device_instance: MCP2221.MCP2221() | None = hass.data[DOMAIN].get(
            binary_sensor.get(CONF_DEVICE_ID))

        if not isinstance(device_instance, MCP2221.MCP2221):
            LOGGER.error("No instance of MCP2221")
            return

        binary_sensors.append(
            MCP2221BinarySensor(
                trigger_entity_config,
                device_instance,
                pin,
                inverted,
                scan_interval
            )
        )

    async_add_entities(binary_sensors)


class MCP2221BinarySensor(ManualTriggerEntity, BinarySensorEntity):
    """Representation of a binary sensor."""

    _attr_should_poll = False

    def __init__(
        self,
        config: ConfigType,
        device: MCP2221,
        pin: int,
        inverted: bool,
        interval: timedelta,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(self.hass, config)
        self._device = device
        self._pin = pin
        self._inverted = inverted
        self._scan_interval = interval

        # init GP
        self._device.InitGP(pin, MCP2221.TYPE.INPUT)
        self._state = self._device.ReadGP(self._pin)

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()

        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._update_state,
                self._scan_interval,
                cancel_on_shutdown=True,
            ),
        )

    @property
    def is_on(self):
        if self._inverted:
            return 1 if self._state == 0 else 0
        return self._state

    def _update_state(self, now: datetime | None = None) -> None:
        """Update value."""
        try:
            self._state = self._device.ReadGP(self._pin)
        except OSError:
            LOGGER.error("Device not available")
            self._state = None

        self.async_write_ha_state()
