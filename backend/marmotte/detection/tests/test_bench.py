from collections.abc import Callable
from datetime import UTC
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from marmotte.common.enums import Mode
from marmotte.detection.bench.manifest import Clip
from marmotte.detection.bench.manifest import load_manifest
from marmotte.detection.bench.prepare import prepare_clip
from marmotte.detection.bench.runner import BenchReport
from marmotte.detection.bench.runner import false_alerts_per_2h
from marmotte.detection.bench.runner import missed_long_cries
from marmotte.detection.bench.runner import run_bench
from marmotte.detection.pipeline import DetectionConfig
from marmotte.detection.pipeline import DetectionPipeline
from marmotte.detection.tests.fakes import loud_is_cry
from marmotte.detection.tests.test_pipeline import noise

START = datetime(2026, 1, 1, tzinfo=UTC)


def _manifest_with(tmp_path: Path, license: str = "CC0-1.0", label: str = "cry") -> Path:
    """A manifest with one clip of the given license and label."""
    path = tmp_path / "manifest.toml"
    path.write_text(
        "[[clip]]\n"
        'file = "clips/cry.flac"\n'
        f'label = "{label}"\n'
        "tags = []\n"
        'source = "https://freesound.org/s/1/"\n'
        'author = "someone"\n'
        f'license = "{license}"\n'
        "segments = [[0.0, 12.5], [20, 31]]\n"
    )
    return path


def _clip(
    tmp_path: Path,
    name: str,
    audio: np.ndarray,
    label: str,
    tags: tuple[str, ...] = (),
    segments: tuple[tuple[float, float], ...] = (),
) -> Clip:
    """Write `audio` as a FLAC file and describe it as a clip."""
    path = tmp_path / f"{name}.flac"
    sf.write(path, audio, 16_000)
    return Clip(path, label, tags, "https://freesound.org/s/1/", "someone", "CC0-1.0", segments)


def _fake_pipeline_factory(
    classifier_threshold_db: float,
) -> Callable[[Callable[[], Mode], DetectionConfig], DetectionPipeline]:
    """Pipelines whose classifier calls any slice louder than the threshold a cry."""

    def make(mode_provider: Callable[[], Mode], config: DetectionConfig) -> DetectionPipeline:
        return DetectionPipeline(loud_is_cry(classifier_threshold_db), config, mode_provider, START)

    return make


class TestMissedLongCries:
    def test_long_cry_detected_within_budget_is_not_missed(self) -> None:
        """An alert 3.5 s after the onset of a 12 s cry: detected."""
        # WHEN
        result = missed_long_cries([(0.0, 12.0)], [13.5], shift_s=10.0)
        # THEN
        assert result == (1, 0)

    def test_long_cry_detected_too_late_is_missed(self) -> None:
        """An alert 9 s after the onset: missed."""
        # WHEN
        result = missed_long_cries([(0.0, 12.0)], [19.0], shift_s=10.0)
        # THEN
        assert result == (1, 1)

    def test_alert_before_onset_does_not_count(self) -> None:
        """An alert before the cry starts is not its detection."""
        # WHEN
        result = missed_long_cries([(0.0, 12.0)], [9.0], shift_s=10.0)
        # THEN
        assert result == (1, 1)

    def test_short_cry_is_not_counted_as_long(self) -> None:
        """A 5 s cry is not part of the "long cries" objective."""
        # WHEN
        result = missed_long_cries([(0.0, 5.0)], [], shift_s=10.0)
        # THEN
        assert result == (0, 0)


class TestFalseAlertsPer2h:
    def test_rate_is_scaled_to_two_hours(self) -> None:
        """One false alert in one hour is two per two hours."""
        # WHEN
        rate = false_alerts_per_2h(1, 3600.0)
        # THEN
        assert rate == 2.0


class TestLoadManifest:
    def test_reads_clips_relative_to_manifest(self, tmp_path: Path) -> None:
        """Clip files are found next to the manifest; segments become tuples."""
        # GIVEN
        path = _manifest_with(tmp_path)
        # WHEN
        clips = load_manifest(path)
        # THEN
        assert len(clips) == 1
        assert clips[0].file == tmp_path / "clips" / "cry.flac"
        assert clips[0].segments == ((0.0, 12.5), (20.0, 31.0))

    def test_rejects_non_free_license(self, tmp_path: Path) -> None:
        """A non commercial license is refused (D81, no NC dependency)."""
        # GIVEN
        path = _manifest_with(tmp_path, license="CC-BY-NC-4.0")
        # WHEN / THEN
        with pytest.raises(ValueError, match=r"CC-BY-NC-4\.0"):
            load_manifest(path)

    def test_local_manifest_accepts_any_license(self, tmp_path: Path) -> None:
        """The local bench (never committed) may use any recording."""
        # GIVEN
        path = _manifest_with(tmp_path, license="YouTube")
        # WHEN
        clips = load_manifest(path, any_license=True)
        # THEN
        assert clips[0].license == "YouTube"

    def test_rejects_unknown_label(self, tmp_path: Path) -> None:
        """A label outside the known ones is refused."""
        # GIVEN
        path = _manifest_with(tmp_path, label="dog")
        # WHEN / THEN
        with pytest.raises(ValueError, match="dog"):
            load_manifest(path)


class TestBenchReport:
    def test_meets_targets_only_with_zero_missed_and_at_most_one_fa(self) -> None:
        """D81: no missed long cry and at most one false alert per two hours."""
        # GIVEN
        good = BenchReport(10, 0, 1, 7200.0, 1.0, {})
        missed_one = BenchReport(10, 1, 0, 7200.0, 0.0, {})
        too_many_fa = BenchReport(10, 0, 3, 7200.0, 1.5, {})
        # WHEN / THEN
        assert good.meets_targets()
        assert not missed_one.meets_targets()
        assert not too_many_fa.meets_targets()

    def test_empty_or_short_bench_does_not_meet_targets(self) -> None:
        """Without long cries, or with less than two hours of backgrounds, nothing is proven (D81)."""
        # GIVEN
        empty = BenchReport(0, 0, 0, 0.0, 0.0, {})
        short_background = BenchReport(10, 0, 0, 3_600.0, 0.0, {})
        # WHEN / THEN
        assert not empty.meets_targets()
        assert not short_background.meets_targets()


class TestPrepareClip:
    def test_converts_and_records_the_clip(self, tmp_path: Path) -> None:
        """A 44.1 kHz stereo file becomes a mono 16 kHz FLAC, listed in the manifest and the credits."""
        # GIVEN
        source = tmp_path / "download.wav"
        sf.write(source, np.zeros((44_100, 2), dtype=np.float32), 44_100)
        bench_dir = tmp_path / "bench"
        # WHEN
        prepare_clip(
            source,
            bench_dir,
            label="cry",
            source_url="https://freesound.org/s/42/",
            author="someone",
            license="CC-BY-4.0",
            segments=[(0.0, 0.5)],
            tags=["room"],
        )
        # THEN
        clips = load_manifest(bench_dir / "manifest.toml")
        assert [c.file.name for c in clips] == ["download.flac"]
        assert clips[0].segments == ((0.0, 0.5),)
        assert clips[0].tags == ("room",)
        info = sf.info(clips[0].file)
        assert (info.samplerate, info.channels) == (16_000, 1)
        assert "https://freesound.org/s/42/" in (bench_dir / "CREDITS.md").read_text()

    def test_credits_link_the_license_text(self, tmp_path: Path) -> None:
        """CC BY asks for a link to the license text: the credits row links it."""
        # GIVEN
        source = tmp_path / "download.wav"
        sf.write(source, np.zeros(16_000, dtype=np.float32), 16_000)
        bench_dir = tmp_path / "bench"
        # WHEN
        prepare_clip(
            source,
            bench_dir,
            label="laugh",
            source_url="https://freesound.org/s/42/",
            author="someone",
            license="CC-BY-3.0",
        )
        # THEN
        credits = (bench_dir / "CREDITS.md").read_text()
        assert "| [CC-BY-3.0](https://creativecommons.org/licenses/by/3.0/) |" in credits

    def test_refuses_non_free_license_before_writing(self, tmp_path: Path) -> None:
        """A non free license is refused before any file is written."""
        # GIVEN
        source = tmp_path / "download.wav"
        sf.write(source, np.zeros(16_000, dtype=np.float32), 16_000)
        bench_dir = tmp_path / "bench"
        # WHEN / THEN
        with pytest.raises(ValueError, match=r"CC-BY-NC-4\.0"):
            prepare_clip(
                source,
                bench_dir,
                label="cry",
                source_url="https://freesound.org/s/42/",
                author="someone",
                license="CC-BY-NC-4.0",
            )
        assert not bench_dir.exists()


class TestRunBench:
    def test_measures_cries_and_false_alerts(self, tmp_path: Path) -> None:
        """A loud 12 s cry is detected in time; 2 h of quiet background give no false alert."""
        # GIVEN
        clips = [
            _clip(tmp_path, "room", noise(30, -60), "background", tags=("room",)),
            _clip(tmp_path, "cry", noise(12, -30, seed=1), "cry", segments=((0.0, 12.0),)),
            _clip(tmp_path, "tv", noise(60, -50, seed=2), "background", tags=("tv",)),
        ]
        # WHEN
        report = run_bench(clips, _fake_pipeline_factory(-40.0))
        # THEN
        assert (report.long_cries, report.missed_long_cries) == (1, 0)
        assert report.false_alerts == 0
        assert report.background_s >= 7200.0
        assert report.recall_by_label == {"cry": 1.0}
        assert report.meets_targets()

    def test_long_cry_after_an_alerted_short_cry_is_detected_again(self, tmp_path: Path) -> None:
        """A short cry alerts; the long cry 3.5 s later is detected again within 8 s: not missed."""
        # GIVEN
        cry = np.concatenate([noise(4, -30, seed=1), noise(3.5, -60, seed=3), noise(15, -30, seed=4)])
        clips = [
            _clip(tmp_path, "room", noise(30, -60), "background", tags=("room",)),
            _clip(tmp_path, "cry", cry, "cry", segments=((0.0, 4.0), (7.5, 22.5))),
        ]
        # WHEN
        report = run_bench(clips, _fake_pipeline_factory(-40.0))
        # THEN
        assert (report.long_cries, report.missed_long_cries) == (1, 0)

    def test_undetected_long_cry_after_an_alert_is_missed(self, tmp_path: Path) -> None:
        """An earlier alert does not hide a long cry the chain does not detect within 8 s."""
        # GIVEN
        cry = np.concatenate([noise(4, -30, seed=1), noise(3.5, -60, seed=3), noise(15, -45, seed=4)])
        clips = [
            _clip(tmp_path, "room", noise(30, -60), "background", tags=("room",)),
            _clip(tmp_path, "cry", cry, "cry", segments=((0.0, 4.0), (7.5, 22.5))),
        ]
        # WHEN
        report = run_bench(clips, _fake_pipeline_factory(-40.0))
        # THEN
        assert (report.long_cries, report.missed_long_cries) == (1, 1)

    def test_counts_a_cry_too_quiet_to_detect_as_missed(self, tmp_path: Path) -> None:
        """A cry under the classifier threshold is a missed long cry, and the targets fail."""
        # GIVEN
        clips = [
            _clip(tmp_path, "room", noise(30, -60), "background", tags=("room",)),
            _clip(tmp_path, "cry", noise(12, -45, seed=1), "cry", segments=((0.0, 12.0),)),
        ]
        # WHEN
        report = run_bench(clips, _fake_pipeline_factory(-40.0))
        # THEN
        assert (report.long_cries, report.missed_long_cries) == (1, 1)
        assert report.recall_by_label == {"cry": 0.0}
        assert not report.meets_targets()
