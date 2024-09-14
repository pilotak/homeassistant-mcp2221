"""MCP2221 sensor"""

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    CONF_STATE_CLASS
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
    CONF_SENSORS,
    CONF_VALUE_TEMPLATE
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.trigger_template_entity import ManualTriggerEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.template import Template
from homeassistant.helpers.trigger_template_entity import (
    ManualTriggerSensorEntity
)

from .const import (LOGGER, DOMAIN, CONF_ADC_REF)
from MCP2221 import MCP2221

TRIGGER_ENTITY_OPTIONS = (
    CONF_DEVICE_CLASS,
    CONF_ICON,
    CONF_UNIQUE_ID,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_STATE_CLASS
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Setup sensors."""
    sensors = []

    LOGGER.info("%s", discovery_info)

    for object_id, sensor in enumerate(discovery_info.get(CONF_SENSORS)):
        LOGGER.info("Setting up sensor: '%s' on pin GP%i",
                    sensor.get(CONF_NAME), sensor.get(CONF_PIN))

        name: str = Template(sensor.get(CONF_NAME, object_id), hass)
        scan_interval: timedelta = sensor.get(CONF_SCAN_INTERVAL)
        pin: int = sensor.get(CONF_PIN)
        value_template: Template | None = sensor.get(CONF_VALUE_TEMPLATE)

        trigger_entity_config = {CONF_NAME: name}
        for key in TRIGGER_ENTITY_OPTIONS:
            if key not in sensor:
                continue
            trigger_entity_config[key] = sensor.get(key)

        # get MCP2221 instance
        device_instance: MCP2221.MCP2221() | None = hass.data[DOMAIN].get(
            sensor.get(CONF_DEVICE_ID))

        if not isinstance(device_instance, MCP2221.MCP2221):
            LOGGER.error("No instance of MCP2221")
            return

        # set ADC reference
        conf_ref = discovery_info.get(CONF_ADC_REF)
        ref = MCP2221.VRM.VDD

        if conf_ref == 1.024:
            ref = MCP2221.VRM.REF_1_024V
        elif conf_ref == 2.048:
            ref = MCP2221.VRM.REF_2_048V
        elif conf_ref == 4.096:
            ref = MCP2221.VRM.REF_4_096V

        device_instance.SetADCVoltageReference(ref)

        sensors.append(
            MCP2221Sensor(
                hass,
                trigger_entity_config,
                value_template,
                device_instance,
                pin,
                scan_interval
            )
        )

    async_add_entities(sensors)


class MCP2221Sensor(ManualTriggerEntity, RestoreSensor):
    """Representation of a sensor."""

    _attr_native_value: Any
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigType,
        value_template: Template | None,
        device: MCP2221,
        pin: int,
        scan_interval: timedelta,
    ) -> None:
        """Initialize the sensor."""
        ManualTriggerSensorEntity.__init__(self, hass, config)
        self._device = device
        self._pin = pin
        self._scan_interval = scan_interval
        self._value_template = value_template

        # init GP
        self._device.InitGP(pin, MCP2221.TYPE.ADC)
        self._attr_native_value = self._device.ReadADC(self._pin)

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()

        # get previous state
        if (state := await self.async_get_last_sensor_data()) is not None:
            self._attr_native_value = state.native_value

        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._update_state,
                self._scan_interval,
                cancel_on_shutdown=True,
            ),
        )

    def _update_state(self, now: datetime | None = None) -> None:
        """Update value."""

        try:
            value = self._device.ReadADC(self._pin)
        except OSError:
            LOGGER.error("Device not available")
            value = None

        # apply value template
        if self._value_template is not None and value is not None:
            self._attr_native_value = self._value_template.render(
                parse_result=False, value=value)

        else:
            self._attr_native_value = value

        self.schedule_update_ha_state()
