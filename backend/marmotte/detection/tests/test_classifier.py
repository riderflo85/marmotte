import hashlib
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from marmotte.common.enums import SoundClass
from marmotte.detection import model_files
from marmotte.detection.classifier import DEFAULT_CLASS_MAP
from marmotte.detection.classifier import YAMNET_NAMES
from marmotte.detection.classifier import YamnetClassifier
from marmotte.detection.classifier import class_indices
from marmotte.detection.classifier import load_class_names
from marmotte.detection.classifier import retained_scores
from marmotte.detection.model_files import DEFAULT_MODELS_DIR
from marmotte.detection.model_files import ModelChecksumError
from marmotte.detection.model_files import ensure_yamnet
from marmotte.detection.types import WINDOW

FIXTURES = Path(__file__).parent / "fixtures"
MODEL_BYTES = b"not really a model"


def _write_models_toml(models_dir: Path, sha256: str) -> None:
    """Write a models.toml that describes a fake model file."""
    (models_dir / "models.toml").write_text(
        "[yamnet]\n"
        'url = "https://example.invalid/yamnet.tflite"\n'
        f'sha256 = "{sha256}"\n'
        'file = "yamnet.tflite"\n'
        'license = "Apache-2.0"\n'
    )


def _fake_download(url: str, destination: Path) -> None:
    """Stand-in for the network: write MODEL_BYTES."""
    destination.write_bytes(MODEL_BYTES)


def _yamnet() -> YamnetClassifier:
    return YamnetClassifier(ensure_yamnet(DEFAULT_MODELS_DIR))


class TestLoadClassNames:
    def test_class_map_contains_all_retained_classes(self) -> None:
        """Every YAMNet name retained by Marmotte exists in the class map shipped with the package."""
        # GIVEN
        retained = {name for group in YAMNET_NAMES.values() for name in group}
        # WHEN
        names = load_class_names(DEFAULT_CLASS_MAP)
        # THEN
        assert len(names) == 521
        assert retained <= set(names)


class TestClassIndices:
    def test_matches_exact_names(self) -> None:
        """A name is found by exact match: "Whimper" is not "Whimper (dog)"."""
        # GIVEN
        names = ["Speech", "Whimper (dog)", "Whimper", "Screaming"]
        # WHEN
        indices = class_indices(names, {SoundClass.WHIMPER: ("Whimper",), SoundClass.SCREAM: ("Screaming",)})
        # THEN
        assert indices == {SoundClass.WHIMPER: (2,), SoundClass.SCREAM: (3,)}

    def test_unknown_name_is_refused(self) -> None:
        """A retained name missing from the class map stops with its name."""
        # GIVEN
        names = ["Speech"]
        # WHEN / THEN
        with pytest.raises(ValueError, match="Baby cry"):
            class_indices(names, {SoundClass.CRY: ("Baby cry, infant cry",)})


class TestRetainedScores:
    def test_category_takes_highest_score_of_its_names(self) -> None:
        """A category grouping several YAMNet names gets the highest of their scores."""
        # GIVEN
        raw = np.array([0.1, 0.7, 0.4, 0.2], dtype=np.float32)
        indices = {SoundClass.CRY: (1, 2), SoundClass.SCREAM: (3,)}
        # WHEN
        scores = retained_scores(raw, indices)
        # THEN
        assert scores == {SoundClass.CRY: pytest.approx(0.7), SoundClass.SCREAM: pytest.approx(0.2)}


class TestEnsureYamnet:
    def test_downloads_missing_model(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """A missing model is downloaded, checked, and its path returned."""
        # GIVEN
        _write_models_toml(tmp_path, hashlib.sha256(MODEL_BYTES).hexdigest())
        monkeypatch.setattr(model_files, "_download", _fake_download)
        # WHEN
        path = ensure_yamnet(tmp_path)
        # THEN
        assert path == tmp_path / "yamnet.tflite"
        assert path.read_bytes() == MODEL_BYTES

    def test_rejects_bad_checksum(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """A download whose SHA-256 differs is refused and not kept."""
        # GIVEN
        _write_models_toml(tmp_path, "0" * 64)
        monkeypatch.setattr(model_files, "_download", _fake_download)
        # WHEN / THEN
        with pytest.raises(ModelChecksumError):
            ensure_yamnet(tmp_path)
        assert not (tmp_path / "yamnet.tflite").exists()

    def test_rejects_altered_local_model(self, tmp_path: Path) -> None:
        """A model already on disk is checked too, without downloading."""
        # GIVEN
        _write_models_toml(tmp_path, hashlib.sha256(MODEL_BYTES).hexdigest())
        (tmp_path / "yamnet.tflite").write_bytes(b"altered")
        # WHEN / THEN
        with pytest.raises(ModelChecksumError):
            ensure_yamnet(tmp_path)


@pytest.mark.model
class TestYamnetClassifier:
    def test_returns_retained_classes_only(self) -> None:
        """The real model gives one score in [0, 1] per retained category, and nothing else."""
        # GIVEN
        classifier = _yamnet()
        # WHEN
        scores = classifier.scores(np.zeros(WINDOW, dtype=np.float32))
        # THEN
        assert set(scores) == set(SoundClass)
        assert all(0.0 <= value <= 1.0 for value in scores.values())

    def test_scores_cry_fixture_as_cry(self) -> None:
        """A real infant cry (CC0) scores high as a cry."""
        # GIVEN
        samples, rate = sf.read(FIXTURES / "cry_cc0.flac", dtype="float32")
        assert rate == 16_000
        window = np.asarray(samples[:WINDOW], dtype=np.float32)
        # WHEN
        scores = _yamnet().scores(window)
        # THEN
        assert scores[SoundClass.CRY] > 0.3
