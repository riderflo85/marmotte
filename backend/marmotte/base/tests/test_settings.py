import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured

from marmotte.settings import get_config_value, load_env, to_bool, to_list

VAR = "MARMOTTE_TEST_VAR"


def test_missing_required_value_names_the_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(VAR, raising=False)
    with pytest.raises(ImproperlyConfigured, match=VAR):
        get_config_value(VAR)


def test_empty_value_counts_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(VAR, "")
    with pytest.raises(ImproperlyConfigured, match=VAR):
        get_config_value(VAR)
    assert get_config_value(VAR, default="x") == "x"


def test_value_from_environment_wins_over_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(VAR, "from-env")
    assert get_config_value(VAR, default="x") == "from-env"


def test_default_is_cast_too(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(VAR, raising=False)
    assert get_config_value(VAR, default="a, b", cast=to_list) == ["a", "b"]


def test_cast_error_names_the_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(VAR, "maybe")
    with pytest.raises(ImproperlyConfigured, match=VAR):
        get_config_value(VAR, cast=to_bool)


def test_to_bool_accepts_true_and_false_any_case() -> None:
    assert to_bool("TRUE") is True
    assert to_bool("false") is False


def test_to_list_strips_spaces_and_empty_items() -> None:
    assert to_list("127.0.0.1, localhost,") == ["127.0.0.1", "localhost"]
    assert to_list("") == []


def test_load_env_reads_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # set then delete: monkeypatch removes the variable that load_env sets, after the test.
    monkeypatch.setenv(VAR, "placeholder")
    monkeypatch.delenv(VAR)
    env_file = tmp_path / ".env"
    env_file.write_text(f"{VAR}=from-file\n", encoding="utf-8")
    load_env(env_file)
    assert os.environ[VAR] == "from-file"


def test_load_env_keeps_existing_variables(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(VAR, "already-set")
    env_file = tmp_path / ".env"
    env_file.write_text(f"{VAR}=from-file\n", encoding="utf-8")
    load_env(env_file)
    assert os.environ[VAR] == "already-set"


def test_load_env_uses_file_named_by_marmotte_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(VAR, "placeholder")
    monkeypatch.delenv(VAR)
    env_file = tmp_path / "other.env"
    env_file.write_text(f"{VAR}=from-named-file\n", encoding="utf-8")
    monkeypatch.setenv("MARMOTTE_ENV_FILE", str(env_file))
    load_env()
    assert os.environ[VAR] == "from-named-file"


def test_load_env_does_nothing_when_marmotte_env_file_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []
    monkeypatch.setattr("marmotte.settings.load_dotenv", lambda *args, **kwargs: calls.append(args))
    monkeypatch.setenv("MARMOTTE_ENV_FILE", "")
    load_env()
    assert calls == []


def test_tests_never_load_the_local_env_file() -> None:
    # Set by pytest-env (pyproject.toml), whatever the shell or the local .env say.
    assert os.environ["MARMOTTE_ENV_FILE"] == ""
    assert os.environ["DJANGO_SETTINGS_MODULE"] == "marmotte.settings.dev"


def test_dev_settings_enable_debug() -> None:
    assert importlib.import_module("marmotte.settings.dev").DEBUG is True


def test_prod_settings_disable_debug() -> None:
    assert importlib.import_module("marmotte.settings.prod").DEBUG is False


def test_prod_refuses_to_start_without_secret_key() -> None:
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "marmotte.settings.prod",
        # Empty, so that a local .env cannot provide a key (it never overrides).
        "DJANGO_SECRET_KEY": "",
    }
    result = subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY" in result.stderr
