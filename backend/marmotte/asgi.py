"""ASGI entry point, served by Uvicorn: ``uvicorn marmotte.asgi:application``."""

from django.core.asgi import get_asgi_application

from marmotte.settings import prepare_environment

prepare_environment()

application = get_asgi_application()
