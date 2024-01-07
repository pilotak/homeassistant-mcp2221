"""MCP2221 binary sensor"""

from datetime import timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.const import (
    CONF_PIN,
    CONF_NAME,
    CONF_UNIQUE_ID,
    CONF_DEVICE_ID,
    CONF_ICON,
    CONF_DEVICE_CLASS,
    CONF_SCAN_INTERVAL,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_SENSORS
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.trigger_template_entity import ManualTriggerEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.template import Template

from .const import (LOGGER, DOMAIN, CONF_ADC_REF)
from .MCP2221 import MCP2221

SCAN_INTERVAL = timedelta(seconds=10)

TRIGGER_ENTITY_OPTIONS = (
    CONF_DEVICE_CLASS,
    CONF_ICON,
    CONF_UNIQUE_ID,
    CONF_UNIT_OF_MEASUREMENT,
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Setup switches."""
    sensors = []

    LOGGER.info("%s", discovery_info)

    for object_id, sensor in enumerate(discovery_info.get(CONF_SENSORS)):
        LOGGER.info("Setting up sensor: '%s' on pin GP%i",
                    sensor.get(CONF_NAME), sensor.get(CONF_PIN))

        name: str = Template(sensor.get(CONF_NAME, object_id), hass)
        scan_interval: timedelta = sensor.get(
            CONF_SCAN_INTERVAL, SCAN_INTERVAL
        )
        pin: int = sensor.get(CONF_PIN)

        trigger_entity_config = {CONF_NAME: name}
        for key in TRIGGER_ENTITY_OPTIONS:
            if key not in sensor:
                continue
            trigger_entity_config[key] = sensor.get(key)

        # get MCP2221 instance
        device_instance: MCP2221 | None = hass.data[DOMAIN].get(
            sensor.get(CONF_DEVICE_ID))

        if not isinstance(device_instance, MCP2221):
            LOGGER.error("No instance of MCP2221")
            return

        # set ADC reference
        device_instance.SetADCVoltageReference(
            discovery_info.get(CONF_ADC_REF))

        sensors.append(
            MCP2221Sensor(
                trigger_entity_config,
                device_instance,
                pin,
                scan_interval
            )
        )

    async_add_entities(sensors)


class MCP2221Sensor(ManualTriggerEntity, SensorEntity):
    """Representation of a switch."""

    def __init__(
        self,
        config: ConfigType,
        device: MCP2221,
        pin: int,
        scan_interval: timedelta,
    ) -> None:
        """Initialize the switch."""
        super().__init__(self.hass, config)
        self._device = device
        self._pin = pin
        self._scan_interval = scan_interval
        self.value = None

        # init GP
        self._device.InitGP(pin, 2)

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self.update,
                self._scan_interval,
                cancel_on_shutdown=True,
            ),
        )

    @property
    def native_value(self) -> int:
        return self.value

    def update(self):
        """Update value."""
        self.value = self._device.ReadADC(self._pin)
        self.async_write_ha_state()
