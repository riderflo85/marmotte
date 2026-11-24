"""Settings for Django core."""

from marmotte.settings import get_config_value, to_list

# https://docs.djangoproject.com/en/6.0/ref/settings/#secret-key
SECRET_KEY = get_config_value("DJANGO_SECRET_KEY")

# https://docs.djangoproject.com/en/6.0/ref/settings/#allowed-hosts
ALLOWED_HOSTS = get_config_value("DJANGO_ALLOWED_HOSTS", cast=to_list)

# https://docs.djangoproject.com/en/6.0/ref/settings/#root-urlconf
ROOT_URLCONF = "marmotte.urls"

ASGI_APPLICATION = "marmotte.asgi.application"
