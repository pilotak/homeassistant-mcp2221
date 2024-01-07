from .const import LOGGER

test = 0


class MCP2221:

    def __init__(self, vid, pid, dev):
        LOGGER.info("Class setup %i %i %i", vid, pid, dev)

    def InitGP(self, pin: int, type: int, value: int = 0):
        LOGGER.info("Init GP%i = %i", pin, type)

    def WriteGP(self, pin: int, value: int):
        LOGGER.info("write GP%i = %i", pin, value)

    def ReadGP(self, pin: int):
        LOGGER.info("read GP%i", pin)
        global test  # Reference the global variable
        test = 1 if test == 0 else 0
        return test
