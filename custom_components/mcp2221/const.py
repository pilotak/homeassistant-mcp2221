"""MCP2221 constants"""


import logging

from homeassistant.const import Platform

LOGGER = logging.getLogger(__package__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    # Platform.SENSOR,
    Platform.SWITCH,
]


DOMAIN = "mcp2221"

CONF_VID = "vid"
CONF_PID = "pid"
CONF_DEV = "dev"
CONF_INVERTED = "inverted"
