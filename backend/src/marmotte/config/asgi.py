"""ASGI entry point, served by Uvicorn: ``uvicorn marmotte.config.asgi:application``."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "marmotte.config.settings")

application = get_asgi_application()
