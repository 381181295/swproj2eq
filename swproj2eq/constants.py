"""Shared CLI constants."""

from enum import IntEnum


class ExitCode(IntEnum):
    OK = 0
    USAGE = 2
    RUNTIME_ERROR = 10
    NOT_IMPLEMENTED = 20
    UNHEALTHY = 30


APP_NAME = "swproj2eq"
VIRTUAL_SINK = "swproj2eq_in"
SERVICE_NAME = "swproj2eq-camilla.service"
