import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured

from marmotte.settings import get_config_value, load_env, prepare_environment, to_bool, to_list
from marmotte.settings.django.paths import BACKEND_DIR

VAR = "MARMOTTE_TEST_VAR"
PRINT_MODE = "from django.conf import settings; print(settings.SETTINGS_MODULE, settings.DEBUG)"


def _run_without_settings_module(*args: str) -> subprocess.CompletedProcess[str]:
    """Run Python with a key and hosts, but no settings module and no .env file."""
    env = {key: value for key, value in os.environ.items() if key != "DJANGO_SETTINGS_MODULE"}
    env |= {
        "MARMOTTE_ENV_FILE": "",
        "DJANGO_SECRET_KEY": "test-only-secret-key",
        "DJANGO_ALLOWED_HOSTS": "localhost",
    }
    return subprocess.run(
        [sys.executable, *args], env=env, capture_output=True, text=True, check=False
    )


class TestGetConfigValue:
    def test_missing_required_value_names_the_variable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A required variable that is not set stops with its name in the message."""
        # GIVEN
        monkeypatch.delenv(VAR, raising=False)
        # WHEN / THEN
        with pytest.raises(ImproperlyConfigured, match=VAR):
            get_config_value(VAR)

    def test_empty_value_counts_as_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An empty variable is refused, or replaced by the default."""
        # GIVEN
        monkeypatch.setenv(VAR, "")
        # WHEN / THEN
        with pytest.raises(ImproperlyConfigured, match=VAR):
            get_config_value(VAR)
        assert get_config_value(VAR, default="x") == "x"

    def test_blank_value_counts_as_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A variable made of spaces is refused, or replaced by the default."""
        # GIVEN
        monkeypatch.setenv(VAR, "   ")
        # WHEN / THEN
        with pytest.raises(ImproperlyConfigured, match=VAR):
            get_config_value(VAR)
        assert get_config_value(VAR, default="x") == "x"

    def test_value_from_environment_wins_over_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A variable that is set is used instead of the default."""
        # GIVEN
        monkeypatch.setenv(VAR, "from-env")
        # WHEN
        value = get_config_value(VAR, default="x")
        # THEN
        assert value == "from-env"

    def test_default_is_cast_too(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The default goes through the same cast as a value from the environment."""
        # GIVEN
        monkeypatch.delenv(VAR, raising=False)
        # WHEN
        value = get_config_value(VAR, default="a, b", cast=to_list)
        # THEN
        assert value == ["a", "b"]

    def test_cast_error_names_the_variable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A value that the cast refuses stops with the variable's name."""
        # GIVEN
        monkeypatch.setenv(VAR, "maybe")
        # WHEN / THEN
        with pytest.raises(ImproperlyConfigured, match=VAR):
            get_config_value(VAR, cast=to_bool)

    def test_any_cast_error_names_the_variable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Any exception raised by the cast, not only ValueError, names the variable."""

        # GIVEN
        def broken_cast(_value: str) -> int:
            raise TypeError("not a number")

        monkeypatch.setenv(VAR, "12")
        # WHEN / THEN
        with pytest.raises(ImproperlyConfigured, match=VAR):
            get_config_value(VAR, cast=broken_cast)

    def test_list_without_items_names_the_variable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A list variable holding only separators stops with the variable's name."""
        # GIVEN
        monkeypatch.setenv(VAR, ",")
        # WHEN / THEN
        with pytest.raises(ImproperlyConfigured, match=VAR):
            get_config_value(VAR, cast=to_list)


class TestToBool:
    def test_accepts_true_and_false_any_case(self) -> None:
        """Reads "true" and "false" whatever their case."""
        # WHEN / THEN
        assert to_bool("TRUE") is True
        assert to_bool("false") is False


class TestToList:
    def test_strips_spaces_and_empty_items(self) -> None:
        """Items lose their spaces, empty items are dropped, an empty value gives []."""
        # WHEN / THEN
        assert to_list("127.0.0.1, localhost,") == ["127.0.0.1", "localhost"]
        assert to_list("") == []

    def test_refuses_a_value_without_items(self) -> None:
        """A value made only of separators is refused."""
        # WHEN / THEN
        with pytest.raises(ValueError):
            to_list(" , ,")


class TestLoadEnv:
    def test_reads_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """The variables of the given file are loaded."""
        # GIVEN: set then delete, so that monkeypatch removes what load_env sets.
        monkeypatch.setenv(VAR, "placeholder")
        monkeypatch.delenv(VAR)
        env_file = tmp_path / ".env"
        env_file.write_text(f"{VAR}=from-file\n", encoding="utf-8")
        # WHEN
        load_env(env_file)
        # THEN
        assert os.environ[VAR] == "from-file"

    def test_keeps_existing_variables(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A variable already set is never replaced by the file."""
        # GIVEN
        monkeypatch.setenv(VAR, "already-set")
        env_file = tmp_path / ".env"
        env_file.write_text(f"{VAR}=from-file\n", encoding="utf-8")
        # WHEN
        load_env(env_file)
        # THEN
        assert os.environ[VAR] == "already-set"

    def test_uses_file_named_by_marmotte_env_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without a path, the file named by MARMOTTE_ENV_FILE is loaded."""
        # GIVEN
        monkeypatch.setenv(VAR, "placeholder")
        monkeypatch.delenv(VAR)
        env_file = tmp_path / "other.env"
        env_file.write_text(f"{VAR}=from-named-file\n", encoding="utf-8")
        monkeypatch.setenv("MARMOTTE_ENV_FILE", str(env_file))
        # WHEN
        load_env()
        # THEN
        assert os.environ[VAR] == "from-named-file"

    def test_does_nothing_when_marmotte_env_file_is_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An empty MARMOTTE_ENV_FILE turns the loading off."""
        # GIVEN
        calls: list[object] = []
        monkeypatch.setattr(
            "marmotte.settings.load_dotenv", lambda *args, **kwargs: calls.append((args, kwargs))
        )
        monkeypatch.setenv("MARMOTTE_ENV_FILE", "")
        # WHEN
        load_env()
        # THEN
        assert calls == []

    def test_tests_never_load_the_local_env_file(self) -> None:
        """pytest-env (pyproject.toml) turns the .env off and fixes the settings module."""
        # THEN
        assert os.environ["MARMOTTE_ENV_FILE"] == ""
        assert os.environ["DJANGO_SETTINGS_MODULE"] == "marmotte.settings.dev"


class TestSettingsModes:
    def test_dev_settings_enable_debug(self) -> None:
        """Development settings turn DEBUG on."""
        # WHEN / THEN
        assert importlib.import_module("marmotte.settings.dev").DEBUG is True

    def test_prod_settings_disable_debug(self) -> None:
        """Production settings turn DEBUG off."""
        # WHEN / THEN
        assert importlib.import_module("marmotte.settings.prod").DEBUG is False

    def test_prod_refuses_to_start_without_secret_key(self) -> None:
        """Production stops at start-up without a secret key."""
        # GIVEN: an empty key, so that a local .env cannot provide one (it never overrides).
        env = {
            **os.environ,
            "DJANGO_SETTINGS_MODULE": "marmotte.settings.prod",
            "DJANGO_SECRET_KEY": "",
        }
        # WHEN
        result = subprocess.run(
            [sys.executable, "-c", "import django; django.setup()"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        # THEN
        assert result.returncode != 0
        assert "ImproperlyConfigured" in result.stderr
        assert "DJANGO_SECRET_KEY is required" in result.stderr


class TestPrepareEnvironment:
    def test_defaults_to_prod_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Without a settings module, production is chosen."""
        # GIVEN
        monkeypatch.delenv("DJANGO_SETTINGS_MODULE")
        # WHEN
        prepare_environment()
        # THEN
        assert os.environ["DJANGO_SETTINGS_MODULE"] == "marmotte.settings.prod"

    def test_replaces_a_blank_settings_module(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A blank settings module is replaced by production."""
        # GIVEN
        monkeypatch.setenv("DJANGO_SETTINGS_MODULE", " ")
        # WHEN
        prepare_environment()
        # THEN
        assert os.environ["DJANGO_SETTINGS_MODULE"] == "marmotte.settings.prod"

    def test_keeps_the_chosen_settings_module(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A chosen settings module is kept."""
        # GIVEN
        monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "marmotte.settings.dev")
        # WHEN
        prepare_environment()
        # THEN
        assert os.environ["DJANGO_SETTINGS_MODULE"] == "marmotte.settings.dev"


class TestEntryPoints:
    def test_manage_py_runs_prod_settings_without_configuration(self) -> None:
        """manage.py runs the production settings when nothing is configured."""
        # WHEN
        result = _run_without_settings_module(
            str(BACKEND_DIR / "manage.py"), "shell", "--no-imports", "-c", PRINT_MODE
        )
        # THEN
        assert result.stdout.strip() == "marmotte.settings.prod False", result.stderr

    def test_asgi_runs_prod_settings_without_configuration(self) -> None:
        """asgi.py runs the production settings when nothing is configured."""
        # WHEN
        result = _run_without_settings_module("-c", f"import marmotte.asgi; {PRINT_MODE}")
        # THEN
        assert result.stdout.strip() == "marmotte.settings.prod False", result.stderr
