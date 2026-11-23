"""Django settings for Marmotte.

Sensitive values come from the environment, never from the repository:

- ``MARMOTTE_SECRET_KEY``: required outside development;
- ``MARMOTTE_DEBUG``: ``"1"`` enables development mode;
- ``MARMOTTE_DATA_DIR``: where runtime data lives (defaults to ``backend/.data``).
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BACKEND_DIR = Path(__file__).resolve().parents[3]

_DEV_ONLY_SECRET_KEY = "django-insecure-marmotte-dev-only-key-never-use-on-a-real-device"


def is_debug() -> bool:
    """Return True when development mode is enabled (``MARMOTTE_DEBUG=1``)."""
    return os.environ.get("MARMOTTE_DEBUG") == "1"


def load_secret_key() -> str:
    """Return the secret key, refusing to start without one outside development."""
    key = os.environ.get("MARMOTTE_SECRET_KEY")
    if key:
        return key
    if is_debug():
        return _DEV_ONLY_SECRET_KEY
    raise ImproperlyConfigured(
        "MARMOTTE_SECRET_KEY is not set. Set it, or set MARMOTTE_DEBUG=1 for development."
    )


DEBUG = is_debug()
SECRET_KEY = load_secret_key()
DATA_DIR = Path(os.environ.get("MARMOTTE_DATA_DIR", BACKEND_DIR / ".data"))

# The babyphone's own domain name is added when HTTPS arrives (lot 7).
ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS: list[str] = []

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

# Needed by the interactive API docs of django-ninja (/api/docs).
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates"}]

ROOT_URLCONF = "marmotte.config.urls"
ASGI_APPLICATION = "marmotte.config.asgi.application"

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True
