"""Alert decision: sliding window over the model scores, scream net and anti-burst pause."""

from collections import deque
from collections.abc import Mapping

from marmotte.common.enums import Sensitivity
from marmotte.common.enums import SoundClass

CRY_THRESHOLDS: dict[Sensitivity, float] = {
    Sensitivity.LOW: 0.5,
    Sensitivity.MEDIUM: 0.5,
    Sensitivity.HIGH: 0.4,
}
"""Score from which a slice counts as a cry, by sensitivity. Never above 0.5, tuned on the test bench to miss no
long cry; only HIGH lowers it, to catch fainter cries (F-23)."""
OTHER_THRESHOLDS: dict[Sensitivity, float] = {
    Sensitivity.LOW: 0.7,
    Sensitivity.MEDIUM: 0.5,
    Sensitivity.HIGH: 0.3,
}
"""Score from which a slice counts as a whimper, a babble or a laugh, by sensitivity."""

BABY_CLASSES = (SoundClass.CRY, SoundClass.WHIMPER, SoundClass.BABBLE, SoundClass.LAUGH)
"""Categories decided by the sliding window; the order is the priority on a tie."""


def thresholds_for(sensitivity: Sensitivity) -> dict[SoundClass, float]:
    """Score threshold of each baby category for a sensitivity."""
    other = OTHER_THRESHOLDS[sensitivity]
    return dict.fromkeys(BABY_CLASSES, other) | {SoundClass.CRY: CRY_THRESHOLDS[sensitivity]}


class SlidingWindowDecider:
    """Decide a category once `k` of the last `n` slices are positive for it."""

    def __init__(self, thresholds: Mapping[SoundClass, float], n: int = 4, k: int = 2) -> None:
        self._thresholds = thresholds
        self._k = k
        self._recent: deque[frozenset[SoundClass]] = deque(maxlen=n)

    def push(self, scores: Mapping[SoundClass, float]) -> SoundClass | None:
        """Add the scores of a new slice (empty when the model did not run) and return the decision."""
        self._recent.append(frozenset(c for c in BABY_CLASSES if scores.get(c, 0.0) >= self._thresholds[c]))
        for sound_class in BABY_CLASSES:
            if sum(sound_class in positives for positives in self._recent) >= self._k:
                return sound_class
        return None


class ScreamNet:
    """Fire on a scream recognized by the model, whatever the sliding window decides.

    The level alone does not fire it: on the bench, any loud household sound did (2026-11-25).
    It fires once per episode and is armed again when the scream score falls back.
    """

    def __init__(self, score_threshold: float = 0.5) -> None:
        self._score_threshold = score_threshold
        self._armed = True

    def push(self, scream_score: float) -> bool:
        """Take the scream score of the last slice into account; True when the net fires."""
        screaming = scream_score >= self._score_threshold
        if self._armed and screaming:
            self._armed = False
            return True
        if not screaming:
            self._armed = True
        return False


class AntiBurst:
    """One alert, then a pause before the next.

    Scream net alerts pass the pause of the sliding window alerts and start it again (F-21: one
    notification per pause for one crying episode); they also have their own pause, so a long scream
    does not ring at every breath.
    """

    def __init__(self, pause_s: float = 60.0) -> None:
        self._pause_s = pause_s
        self._last_s: float | None = None
        self._last_net_s: float | None = None

    def allow(self, now_s: float, via_scream_net: bool) -> bool:
        """True when an alert decided at `now_s` (seconds) may be sent."""
        last = self._last_net_s if via_scream_net else self._last_s
        if last is not None and now_s - last < self._pause_s:
            return False
        if via_scream_net:
            self._last_net_s = now_s
        self._last_s = now_s
        return True
