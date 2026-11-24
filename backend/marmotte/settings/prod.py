"""Settings for production, on the Pi."""

from marmotte.settings.base import *

DEBUG = False

# Cookies only over HTTPS (the app is served in HTTPS, lot 7).
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
