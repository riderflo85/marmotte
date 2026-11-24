#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys


def main() -> None:
    from marmotte.settings import load_env

    # The .env may choose the settings module: load it first. Default: production.
    load_env()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "marmotte.settings.prod")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
