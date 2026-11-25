import numpy as np
import pytest

from marmotte.detection.level import SILENCE_DB
from marmotte.detection.level import HighPass
from marmotte.detection.level import MicHealth
from marmotte.detection.level import NoiseFloor
from marmotte.detection.level import rms_dbfs
from marmotte.detection.types import HOP

HOP_S = 0.4875


def _sine(freq_hz: float, seconds: float, amplitude: float = 1.0) -> np.ndarray:
    """A sine at 16 kHz, as float32."""
    t = np.arange(int(16_000 * seconds)) / 16_000
    return (amplitude * np.sin(2 * np.pi * freq_hz * t)).astype(np.float32)


def _warmed_up_floor(level_db: float) -> NoiseFloor:
    """A noise floor fed 30 s of a steady level, past its warm-up."""
    floor = NoiseFloor()
    for _ in range(30):
        floor.update(level_db, 1.0)
    return floor


class TestRmsDbfs:
    def test_full_scale_sine_is_minus_3_dbfs(self) -> None:
        """A full-scale sine has an RMS of 1/sqrt(2), i.e. -3.01 dBFS."""
        # GIVEN
        tone = _sine(440, 1.0)
        # WHEN
        level = rms_dbfs(tone)
        # THEN
        assert level == pytest.approx(-3.01, abs=0.05)

    def test_silence_is_floor(self) -> None:
        """Digital silence gives SILENCE_DB instead of minus infinity."""
        # GIVEN
        silence = np.zeros(HOP, dtype=np.float32)
        # WHEN
        level = rms_dbfs(silence)
        # THEN
        assert level == SILENCE_DB


class TestHighPass:
    def test_removes_slow_drift(self) -> None:
        """The 1-2 Hz pressure drift of the micro (lot 0, about -50 dBFS) is removed, across calls."""
        # GIVEN
        drift = _sine(1.5, 4.0, amplitude=0.0045)
        high_pass = HighPass()
        # WHEN
        out = np.concatenate([high_pass.process(chunk) for chunk in np.split(drift, 8)])
        # THEN
        assert rms_dbfs(drift) == pytest.approx(-50.0, abs=0.5)
        assert rms_dbfs(out[16_000:]) < -90.0

    def test_keeps_voice_band(self) -> None:
        """A 500 Hz tone keeps its level."""
        # GIVEN
        tone = _sine(500, 1.0)
        # WHEN
        out = HighPass().process(tone)
        # THEN
        assert rms_dbfs(out[4_000:]) == pytest.approx(-3.01, abs=0.2)


class TestNoiseFloor:
    def test_starts_at_first_level(self) -> None:
        """The first measured level sets the floor (arriving in the middle of a party)."""
        # GIVEN
        floor = NoiseFloor()
        # WHEN
        floor.update(-20.0, HOP_S)
        # THEN
        assert floor.value_db == pytest.approx(-20.0)

    def test_converges_during_warmup(self) -> None:
        """During the warm-up, the floor follows a new level within a few seconds."""
        # GIVEN
        floor = NoiseFloor()
        floor.update(-60.0, HOP_S)
        # WHEN
        for _ in range(19):  # 20 x 0.4875 s < 10 s
            floor.update(-20.0, HOP_S)
        # THEN
        assert floor.value_db == pytest.approx(-20.0, abs=1.0)

    def test_rises_slowly_after_warmup(self) -> None:
        """After the warm-up, the floor rises by at most 0.1 dB per second."""
        # GIVEN
        floor = _warmed_up_floor(-50.0)
        # WHEN
        floor.update(-20.0, 1.0)
        # THEN
        assert -50.0 < floor.value_db <= -49.85

    def test_falls_fast_after_warmup(self) -> None:
        """After the warm-up, the floor follows a quieter room within seconds."""
        # GIVEN
        floor = _warmed_up_floor(-50.0)
        # WHEN
        for _ in range(10):
            floor.update(-70.0, 1.0)
        # THEN
        assert floor.value_db < -68.0


class TestMicHealth:
    def test_flags_digital_silence_after_10_s(self) -> None:
        """10 s of digital silence mean a silent micro; any sound clears the flag."""
        # GIVEN
        health = MicHealth()
        for _ in range(21):  # 10.2 s
            health.update(SILENCE_DB, HOP_S)
        silent_after_10_s = health.is_silent
        # WHEN
        health.update(-60.0, HOP_S)
        # THEN
        assert silent_after_10_s
        assert not health.is_silent

    def test_short_silence_is_not_flagged(self) -> None:
        """Less than 10 s of digital silence is not a silent micro."""
        # GIVEN
        health = MicHealth()
        # WHEN
        for _ in range(20):  # 9.75 s
            health.update(SILENCE_DB, HOP_S)
        # THEN
        assert not health.is_silent
