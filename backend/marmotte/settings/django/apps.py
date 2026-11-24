"""Settings for Django applications."""

DJANGO_APPS: list[str] = []

THIRD_PARTY_APPS: list[str] = []

LOCAL_APPS = [
    "marmotte.base",
]

# https://docs.djangoproject.com/en/6.0/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
