"""Settings shared by every mode: development (dev.py) and production (prod.py)."""

from marmotte.settings import load_env

load_env()

from marmotte.settings.django.apps import *  # noqa: E402
from marmotte.settings.django.core import *  # noqa: E402
from marmotte.settings.django.internationalization import *  # noqa: E402
from marmotte.settings.django.middlewares import *  # noqa: E402
from marmotte.settings.django.paths import *  # noqa: E402
from marmotte.settings.django.templates import *  # noqa: E402
from marmotte.settings.project.data import *  # noqa: E402
