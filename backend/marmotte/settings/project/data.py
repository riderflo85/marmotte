"""Settings for the babyphone's data."""

from pathlib import Path

from marmotte.settings import get_config_value
from marmotte.settings.django.paths import BACKEND_DIR

# Where the babyphone keeps its data (database, keys…): the data partition on the Pi.
DATA_DIR = get_config_value("MARMOTTE_DATA_DIR", default=str(BACKEND_DIR / ".data"), cast=Path)
