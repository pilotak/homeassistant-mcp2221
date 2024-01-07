from .const import LOGGER

class MCP2221:
    def __init__(self, vid, pid, dev):
        LOGGER.info("Class setup %i %i %i", vid, pid, dev)

    def InitGP(self, pin: int, type: int, value: int = 0):
        LOGGER.info("Init GP%i = %i", pin, type)
    
    def WriteGP(self, pin: int, value: int):
        LOGGER.info("write GP%i = %i", pin, value)
