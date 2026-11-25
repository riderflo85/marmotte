"""Download and check the model files listed in `models/models.toml`."""

import hashlib
import logging
import shutil
import tomllib
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
"""`backend/models/`: models.toml and the downloaded model files."""

_DOWNLOAD_TIMEOUT_S = 60


class ModelChecksumError(Exception):
    """A model file does not have the SHA-256 written in models.toml."""


def _download(url: str, destination: Path) -> None:
    with urllib.request.urlopen(url, timeout=_DOWNLOAD_TIMEOUT_S) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out)


def _check_sha256(path: Path, expected: str) -> None:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected:
        raise ModelChecksumError(f"{path.name}: SHA-256 {digest}, expected {expected}")


def ensure_yamnet(models_dir: Path) -> Path:
    """Return the path of the YAMNet model, downloading it if missing; its SHA-256 is always checked."""
    with (models_dir / "models.toml").open("rb") as f:
        spec = tomllib.load(f)["yamnet"]
    path = models_dir / spec["file"]
    if path.exists():
        _check_sha256(path, spec["sha256"])
        return path
    partial = path.with_name(f"{path.name}.part")
    logger.info("Downloading %s from %s", path.name, spec["url"])
    _download(spec["url"], partial)
    try:
        _check_sha256(partial, spec["sha256"])
    except ModelChecksumError:
        partial.unlink()
        raise
    partial.replace(path)
    return path
