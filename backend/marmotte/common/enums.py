"""Enumerations shared by every Marmotte service."""

from enum import StrEnum


class Mode(StrEnum):
    """Monitoring mode of the babyphone."""

    STARTING = "starting"
    COUNTDOWN = "countdown"
    SIESTE = "sieste"
    SILENT = "silent"
    MAINTENANCE = "maintenance"


class SoundClass(StrEnum):
    """Sound categories retained from YAMNet."""

    CRY = "cry"
    WHIMPER = "whimper"
    BABBLE = "babble"
    LAUGH = "laugh"
    SCREAM = "scream"


class Sensitivity(StrEnum):
    """Detection sensitivity chosen in the app."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
