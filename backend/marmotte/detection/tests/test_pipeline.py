from datetime import UTC
from datetime import datetime
from datetime import timedelta

import numpy as np

from marmotte.common.enums import Mode
from marmotte.common.enums import SoundClass
from marmotte.detection.classifier import Classifier
from marmotte.detection.level import rms_dbfs
from marmotte.detection.pipeline import DetectionConfig
from marmotte.detection.pipeline import DetectionPipeline
from marmotte.detection.tests.fakes import FakeClassifier
from marmotte.detection.tests.fakes import loud_is_cry
from marmotte.detection.tests.fakes import silent
from marmotte.detection.types import HOP
from marmotte.detection.types import AlertEvent
from marmotte.detection.types import Audio

START = datetime(2026, 1, 1, tzinfo=UTC)


def noise(seconds: float, dbfs: float, seed: int = 0) -> Audio:
    """White noise whose RMS level is exactly `dbfs`."""
    samples = np.random.default_rng(seed).standard_normal(int(16_000 * seconds))
    samples *= 10 ** (dbfs / 20) / np.sqrt(np.mean(samples**2))
    return np.clip(samples, -1.0, 1.0).astype(np.float32)


def pipeline(mode: Mode, classifier: Classifier) -> DetectionPipeline:
    """A pipeline with the default configuration and a fixed mode."""
    return DetectionPipeline(classifier, DetectionConfig(), lambda: mode, lambda: START)


def feed_all(p: DetectionPipeline, audio: Audio) -> list[AlertEvent]:
    """Feed the audio hop by hop and return every alert."""
    alerts: list[AlertEvent] = []
    for start in range(0, len(audio), HOP):
        alerts += p.feed(audio[start : start + HOP])
    return alerts


class TestDetectionPipeline:
    def test_cry_alert_within_8_s_of_onset(self) -> None:
        """A cry 20 dB above the floor alerts within 8 s, as a cry."""
        # GIVEN
        p = pipeline(Mode.SIESTE, loud_is_cry(-45))
        audio = np.concatenate([noise(20, -55), noise(15, -35, seed=1)])
        # WHEN
        alerts = feed_all(p, audio)
        # THEN
        assert alerts
        assert alerts[0].kind == SoundClass.CRY
        assert not alerts[0].via_scream_net
        assert 20.0 <= alerts[0].offset_s <= 28.0

    def test_alert_time_is_read_on_the_clock_at_decision(self) -> None:
        """The alert time comes from the clock when the alert is decided, not from the start time."""
        # GIVEN
        now = [START]
        p = DetectionPipeline(loud_is_cry(-45), DetectionConfig(), lambda: Mode.SIESTE, clock=lambda: now[0])
        feed_all(p, noise(20, -55))
        decision_time = START + timedelta(hours=1)
        now[0] = decision_time
        # WHEN
        alerts = feed_all(p, noise(15, -35, seed=1))
        # THEN
        assert [alert.at for alert in alerts] == [decision_time]

    def test_long_cry_alerts_once_per_pause(self) -> None:
        """A cry that lasts 50 s gives one alert, not one per slice (anti-burst)."""
        # GIVEN
        p = pipeline(Mode.SIESTE, loud_is_cry(-45))
        audio = np.concatenate([noise(20, -55), noise(50, -35, seed=1)])
        # WHEN
        alerts = feed_all(p, audio)
        # THEN
        assert len(alerts) == 1

    def test_no_alert_outside_sieste(self) -> None:
        """In silent monitoring, neither the model nor the scream net alerts."""
        # GIVEN
        p = pipeline(Mode.SILENT, loud_is_cry(-45))
        audio = np.concatenate([noise(20, -55), noise(15, -10, seed=1)])
        # WHEN
        alerts = feed_all(p, audio)
        # THEN
        assert alerts == []

    def test_quiet_background_does_not_run_the_model(self) -> None:
        """While nothing rises above the noise floor, the classifier is not called."""
        # GIVEN
        classifier = silent()
        p = pipeline(Mode.SIESTE, classifier)
        # WHEN
        feed_all(p, noise(30, -55))
        # THEN
        assert classifier.calls == 0

    def test_very_loud_unrecognized_sound_does_not_alert(self) -> None:
        """A sound 45 dB above the floor that the model does not recognize gives no alert (bench, 2026-11-25)."""
        # GIVEN
        p = pipeline(Mode.SIESTE, silent())
        audio = np.concatenate([noise(20, -55), noise(5, -10, seed=1)])
        # WHEN
        alerts = feed_all(p, audio)
        # THEN
        assert alerts == []

    def test_recognized_scream_alerts_through_scream_net_during_pause(self) -> None:
        """A scream recognized by the model alerts even in the pause that follows a cry alert."""
        # GIVEN
        classifier = FakeClassifier(
            lambda window: {SoundClass.SCREAM: 0.8} if rms_dbfs(window) > -15 else {SoundClass.CRY: 0.9}
        )
        p = pipeline(Mode.SIESTE, classifier)
        audio = np.concatenate([noise(20, -55), noise(15, -35, seed=1), noise(5, -10, seed=2)])
        # WHEN
        alerts = feed_all(p, audio)
        # THEN
        assert [(alert.kind, alert.via_scream_net) for alert in alerts] == [
            (SoundClass.CRY, False),
            (SoundClass.SCREAM, True),
        ]
        assert 35.0 <= alerts[1].offset_s <= 37.0

    def test_scream_alert_holds_back_the_next_cry_alert(self) -> None:
        """F-21: a scream net alert, then a cry seconds later, gives one notification for the pause."""
        # GIVEN
        classifier = FakeClassifier(
            lambda window: {SoundClass.SCREAM: 0.8} if rms_dbfs(window) > -15 else {SoundClass.CRY: 0.9}
        )
        p = pipeline(Mode.SIESTE, classifier)
        audio = np.concatenate([noise(20, -55), noise(5, -10, seed=1), noise(15, -35, seed=2)])
        # WHEN
        alerts = feed_all(p, audio)
        # THEN
        assert [(alert.kind, alert.via_scream_net) for alert in alerts] == [(SoundClass.SCREAM, True)]

    def test_damaged_samples_do_not_deafen_the_chain(self) -> None:
        """Review Focus 5: a NaN in the stream is cleaned, and the cry that follows still alerts."""
        # GIVEN
        p = pipeline(Mode.SIESTE, loud_is_cry(-45))
        quiet = noise(20, -55)
        quiet[100_000] = np.nan
        quiet[100_001] = np.inf
        audio = np.concatenate([quiet, noise(15, -35, seed=1)])
        # WHEN
        alerts = feed_all(p, audio)
        # THEN
        assert [alert.kind for alert in alerts] == [SoundClass.CRY]
        assert np.isfinite(p.stats.floor_db)

    def test_door_slam_does_not_alert(self) -> None:
        """Review Focus 2: a 0.3 s very loud sound does not alert."""
        # GIVEN
        p = pipeline(Mode.SIESTE, silent())
        audio = np.concatenate([noise(20, -55), noise(0.3, -3, seed=1), noise(10, -55, seed=2)])
        # WHEN
        alerts = feed_all(p, audio)
        # THEN
        assert alerts == []

    def test_loud_party_from_start_does_not_trigger_scream_net(self) -> None:
        """Review Focus 3: loud music from the start becomes the floor, without a scream alert."""
        # GIVEN
        p = pipeline(Mode.SIESTE, silent())
        # WHEN
        alerts = feed_all(p, noise(60, -20))
        # THEN
        assert alerts == []

    def test_cry_6_db_over_loud_music_still_alerts(self) -> None:
        """Review Focus 4: a cry 6 dB above loud music still alerts."""
        # GIVEN
        p = pipeline(Mode.SIESTE, loud_is_cry(-22))
        audio = np.concatenate([noise(40, -25), noise(15, -19, seed=1)])
        # WHEN
        alerts = feed_all(p, audio)
        # THEN
        assert any(alert.kind == SoundClass.CRY for alert in alerts)

    def test_stats_report_mic_silence(self) -> None:
        """Review Focus 1: after 10 s of digital silence, the stats flag a silent micro."""
        # GIVEN
        p = pipeline(Mode.SIESTE, silent())
        # WHEN
        feed_all(p, np.zeros(16_000 * 11, dtype=np.float32))
        # THEN
        assert p.stats.mic_silent

    def test_stats_report_level_floor_and_last_alert(self) -> None:
        """The stats give the last level, the floor and the last alert."""
        # GIVEN
        p = pipeline(Mode.SIESTE, loud_is_cry(-45))
        # WHEN
        alerts = feed_all(p, np.concatenate([noise(20, -55), noise(15, -35, seed=1)]))
        # THEN
        assert abs(p.stats.level_db - -35.0) < 0.5
        assert -55.5 < p.stats.floor_db < -50.0
        assert not p.stats.mic_silent
        assert p.stats.last_alert == alerts[-1]

    def test_chunks_of_any_size_give_same_alerts(self) -> None:
        """The pipeline cuts its own hops: odd chunk sizes change nothing."""
        # GIVEN
        audio = np.concatenate([noise(20, -55), noise(15, -35, seed=1)])
        by_hop = feed_all(pipeline(Mode.SIESTE, loud_is_cry(-45)), audio)
        p = pipeline(Mode.SIESTE, loud_is_cry(-45))
        # WHEN
        odd: list[AlertEvent] = []
        for start in range(0, len(audio), 1_000):
            odd += p.feed(audio[start : start + 1_000])
        # THEN
        assert [(a.kind, a.offset_s) for a in odd] == [(a.kind, a.offset_s) for a in by_hop]
