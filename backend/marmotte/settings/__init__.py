"""Tools to read the configuration from the environment.

The settings modules (``base``, ``dev``, ``prod``) read every value with
``get_config_value``. In development, the values come from ``backend/.env``,
loaded by ``load_env``; on the Pi, systemd provides them.
"""

import os
from collections.abc import Callable
from pathlib import Path
from typing import Final, overload

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

from marmotte.settings.django.paths import BACKEND_DIR


class _Required:
    """Marks a configuration value without default: it must be set."""

    def __repr__(self) -> str:
        return "REQUIRED"


REQUIRED: Final = _Required()


@overload
def get_config_value(name: str, default: str | _Required = REQUIRED) -> str: ...


@overload
def get_config_value[T](
    name: str, default: str | _Required = REQUIRED, *, cast: Callable[[str], T]
) -> T: ...


def get_config_value[T](
    name: str, default: str | _Required = REQUIRED, *, cast: Callable[[str], T] | None = None
) -> str | T:
    """Return the environment variable ``name``, cast if asked.

    An empty variable counts as missing: the default is used instead, and cast
    too. Without a default, a missing variable stops the start-up with a clear
    message, as does a value that cannot be cast.
    """
    raw = os.environ.get(name) or default
    if isinstance(raw, _Required):
        raise ImproperlyConfigured(f"The environment variable {name} is required but not set.")
    if cast is None:
        return raw
    try:
        return cast(raw)
    except ValueError as error:
        raise ImproperlyConfigured(
            f"The environment variable {name} is invalid: {error}"
        ) from error


def to_bool(value: str) -> bool:
    """Convert ``"true"`` or ``"false"`` (any case) to a boolean."""
    match value.strip().lower():
        case "true":
            return True
        case "false":
            return False
        case _:
            raise ValueError(f'expected "true" or "false", got "{value}"')


def to_list(value: str, separator: str = ",") -> list[str]:
    """Split ``value`` on ``separator``, without surrounding spaces nor empty items."""
    return [item.strip() for item in value.split(separator) if item.strip()]


def load_env(path: Path | None = None) -> None:
    """Load a ``.env`` file, never replacing a variable already set.

    Without ``path``, the file is the one named by ``MARMOTTE_ENV_FILE``, or
    ``backend/.env`` when that variable is not set. An empty ``MARMOTTE_ENV_FILE``
    turns the loading off: the tests use it to never read the developer's ``.env``.
    """
    if path is None:
        configured = os.environ.get("MARMOTTE_ENV_FILE")
        if configured == "":
            return
        path = Path(configured) if configured else BACKEND_DIR / ".env"
    load_dotenv(path, override=False)
