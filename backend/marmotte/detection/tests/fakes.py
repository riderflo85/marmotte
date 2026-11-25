"""Fake classifiers for the tests: the decision chain is tested without the model."""

from collections.abc import Callable
from collections.abc import Mapping

from marmotte.common.enums import SoundClass
from marmotte.detection.level import rms_dbfs
from marmotte.detection.types import Audio


class FakeClassifier:
    """A classifier that applies a rule to each slice it gets."""

    def __init__(self, rule: Callable[[Audio], Mapping[SoundClass, float]]) -> None:
        self._rule = rule
        self.calls = 0

    def scores(self, window: Audio) -> Mapping[SoundClass, float]:
        self.calls += 1
        return self._rule(window)


def loud_is_cry(threshold_db: float) -> FakeClassifier:
    """A slice louder than `threshold_db` is a cry (score 0.9); anything else is nothing."""
    return FakeClassifier(lambda window: {SoundClass.CRY: 0.9} if rms_dbfs(window) > threshold_db else {})


def silent() -> FakeClassifier:
    """A classifier that never recognizes anything."""
    return FakeClassifier(lambda window: {})
