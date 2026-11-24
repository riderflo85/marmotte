"""ASGI entry point, served by Uvicorn: ``uvicorn marmotte.asgi:application``."""

import os

from django.core.asgi import get_asgi_application

from marmotte.settings import load_env

# The .env may choose the settings module: load it first. Default: production.
load_env()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "marmotte.settings.prod")

application = get_asgi_application()
