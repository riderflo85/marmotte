"""Alert decision: sliding window over the model scores, scream net and anti-burst pause."""

from collections import deque
from collections.abc import Mapping

from marmotte.common.enums import Sensitivity
from marmotte.common.enums import SoundClass

THRESHOLDS: dict[Sensitivity, float] = {
    Sensitivity.LOW: 0.5,
    Sensitivity.MEDIUM: 0.3,
    Sensitivity.HIGH: 0.15,
}
"""Score from which a slice counts for a category, by sensitivity (tuned on the test bench)."""

BABY_CLASSES = (SoundClass.CRY, SoundClass.WHIMPER, SoundClass.BABBLE, SoundClass.LAUGH)
"""Categories decided by the sliding window; the order is the priority on a tie."""


class SlidingWindowDecider:
    """Decide a category once `k` of the last `n` slices are positive for it."""

    def __init__(self, threshold: float, n: int = 4, k: int = 2) -> None:
        self._threshold = threshold
        self._k = k
        self._recent: deque[frozenset[SoundClass]] = deque(maxlen=n)

    def push(self, scores: Mapping[SoundClass, float]) -> SoundClass | None:
        """Add the scores of a new slice (empty when the model did not run) and return the decision."""
        self._recent.append(frozenset(c for c in BABY_CLASSES if scores.get(c, 0.0) >= self._threshold))
        for sound_class in BABY_CLASSES:
            if sum(sound_class in positives for positives in self._recent) >= self._k:
                return sound_class
        return None


class ScreamNet:
    """Fire, whatever the model says, on a sound far above the floor for a while, or on a recognized scream.

    It fires once per episode and is armed again when both the level and the scream score fall back:
    a long scream passes the anti-burst pause and would otherwise ring at every slice.
    """

    def __init__(self, margin_db: float = 25.0, min_duration_s: float = 1.0, score_threshold: float = 0.5) -> None:
        self._margin_db = margin_db
        self._min_duration_s = min_duration_s
        self._score_threshold = score_threshold
        self._loud_for_s = 0.0
        self._armed = True

    def push(self, level_db: float, floor_db: float, scream_score: float, dt: float) -> bool:
        """Take the last `dt` seconds into account; True when the net fires."""
        loud = level_db - floor_db >= self._margin_db
        self._loud_for_s = self._loud_for_s + dt if loud else 0.0
        screaming = scream_score >= self._score_threshold
        if self._armed and (self._loud_for_s >= self._min_duration_s or screaming):
            self._armed = False
            return True
        if not loud and not screaming:
            self._armed = True
        return False


class AntiBurst:
    """One alert, then a pause before the next; scream net alerts pass during the pause.

    Only the alerts of the sliding window start the pause.
    """

    def __init__(self, pause_s: float = 60.0) -> None:
        self._pause_s = pause_s
        self._last_s: float | None = None

    def allow(self, now_s: float, via_scream_net: bool) -> bool:
        """True when an alert decided at `now_s` (seconds) may be sent."""
        if via_scream_net:
            return True
        if self._last_s is not None and now_s - self._last_s < self._pause_s:
            return False
        self._last_s = now_s
        return True
