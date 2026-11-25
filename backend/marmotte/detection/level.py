"""Sound level, adaptive noise floor and micro health (first stage of the detection chain)."""

import math

import numpy as np
from scipy.signal import butter
from scipy.signal import sosfilt

from marmotte.detection.types import SAMPLE_RATE
from marmotte.detection.types import Audio

SILENCE_DB = -120.0
"""Level given to digital silence, instead of minus infinity."""

_WARMUP_TAU_S = 1.0


def rms_dbfs(frame: Audio) -> float:
    """RMS level of a frame in dBFS (0 dBFS = a full-scale square wave), never below SILENCE_DB."""
    mean_square = float(np.mean(np.square(frame, dtype=np.float64))) if len(frame) else 0.0
    if mean_square <= 0.0:
        return SILENCE_DB
    return max(10.0 * math.log10(mean_square), SILENCE_DB)


class HighPass:
    """Butterworth high-pass filter that keeps its state from one frame to the next.

    It removes the slow pressure drift of the micro (1-2 Hz) before the level is measured.
    YAMNet gets the unfiltered sound.
    """

    def __init__(self, cutoff_hz: float = 80.0, order: int = 2) -> None:
        # butter() returns a tuple for other outputs: asarray narrows the type for pyright.
        self._sos = np.asarray(butter(order, cutoff_hz, "highpass", fs=SAMPLE_RATE, output="sos"))
        self._state = np.zeros((self._sos.shape[0], 2))

    def process(self, frame: Audio) -> Audio:
        filtered, self._state = sosfilt(self._sos, frame, zi=self._state)
        return np.asarray(filtered, dtype=np.float32)


class NoiseFloor:
    """Background level of the room, in dBFS, that adapts to the place.

    The first level sets it (arriving in the middle of a party). During the warm-up it follows the
    level both ways (time constant 1 s); then it falls quickly to a quieter level and rises slowly
    to a louder one, so that a long cry does not become the background.
    """

    def __init__(self, warmup_s: float = 10.0, rise_db_per_s: float = 0.1, fall_tau_s: float = 2.0) -> None:
        self._warmup_s = warmup_s
        self._rise_db_per_s = rise_db_per_s
        self._fall_tau_s = fall_tau_s
        self._elapsed_s = 0.0
        self._started = False
        self.value_db = SILENCE_DB

    @property
    def started(self) -> bool:
        """True once a first level has been measured."""
        return self._started

    def update(self, level_db: float, dt: float) -> float:
        """Take the level of the last `dt` seconds into account and return the new floor."""
        if not self._started:
            self.value_db = level_db
            self._started = True
        elif self._elapsed_s < self._warmup_s:
            self.value_db += (level_db - self.value_db) * (1.0 - math.exp(-dt / _WARMUP_TAU_S))
        elif level_db < self.value_db:
            self.value_db += (level_db - self.value_db) * (1.0 - math.exp(-dt / self._fall_tau_s))
        else:
            self.value_db = min(level_db, self.value_db + self._rise_db_per_s * dt)
        self._elapsed_s += dt
        return self.value_db


class MicHealth:
    """Flag a silent micro (unplugged module: perfect zeros) after a long digital silence."""

    def __init__(self, silent_db: float = -100.0, silent_after_s: float = 10.0) -> None:
        self._silent_db = silent_db
        self._silent_after_s = silent_after_s
        self._silent_for_s = 0.0

    def update(self, level_db: float, dt: float) -> None:
        """Take the level of the last `dt` seconds into account."""
        self._silent_for_s = self._silent_for_s + dt if level_db < self._silent_db else 0.0

    @property
    def is_silent(self) -> bool:
        """True after `silent_after_s` seconds in a row below `silent_db`."""
        return self._silent_for_s >= self._silent_after_s
