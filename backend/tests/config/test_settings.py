import pytest
from django.core.exceptions import ImproperlyConfigured

from marmotte.config.settings import load_secret_key


def test_settings_refuse_missing_secret_key_outside_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MARMOTTE_SECRET_KEY", raising=False)
    monkeypatch.setenv("MARMOTTE_DEBUG", "0")
    with pytest.raises(ImproperlyConfigured):
        load_secret_key()


def test_settings_refuse_empty_secret_key_outside_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARMOTTE_SECRET_KEY", "")
    monkeypatch.delenv("MARMOTTE_DEBUG", raising=False)
    with pytest.raises(ImproperlyConfigured):
        load_secret_key()


def test_settings_use_secret_key_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARMOTTE_SECRET_KEY", "a-real-key-generated-on-the-pi")
    monkeypatch.setenv("MARMOTTE_DEBUG", "0")
    assert load_secret_key() == "a-real-key-generated-on-the-pi"


def test_settings_fall_back_to_dev_only_key_in_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MARMOTTE_SECRET_KEY", raising=False)
    monkeypatch.setenv("MARMOTTE_DEBUG", "1")
    assert "dev-only" in load_secret_key()
