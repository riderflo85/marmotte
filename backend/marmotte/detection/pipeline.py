"""Detection chain: level and noise floor, gate, classifier, sliding window, scream net, anti-burst."""

import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from marmotte.common.enums import Mode
from marmotte.common.enums import Sensitivity
from marmotte.common.enums import SoundClass
from marmotte.detection.audio import clean_samples
from marmotte.detection.classifier import Classifier
from marmotte.detection.decision import THRESHOLDS
from marmotte.detection.decision import AntiBurst
from marmotte.detection.decision import ScreamNet
from marmotte.detection.decision import SlidingWindowDecider
from marmotte.detection.level import SILENCE_DB
from marmotte.detection.level import HighPass
from marmotte.detection.level import MicHealth
from marmotte.detection.level import NoiseFloor
from marmotte.detection.level import rms_dbfs
from marmotte.detection.types import HOP
from marmotte.detection.types import SAMPLE_RATE
from marmotte.detection.types import WINDOW
from marmotte.detection.types import AlertEvent
from marmotte.detection.types import Audio

HOP_S = HOP / SAMPLE_RATE
"""Duration of a hop, in seconds."""
_HOPS_PER_WINDOW = WINDOW // HOP
"""Hops in a model slice (2)."""


@dataclass(frozen=True)
class DetectionConfig:
    """Settings of the detection chain (default values tuned on the test bench)."""

    gate_margin_db: float = 3.0
    """The model runs when a hop of the slice is this far above the noise floor."""
    n: int = 6
    """Size of the sliding window: the last `n` slices."""
    k: int = 3
    """Slices of the window that must reach the threshold for a baby category."""
    sensitivity: Sensitivity = Sensitivity.MEDIUM
    """Chooses the score threshold of a slice (`THRESHOLDS`)."""
    pause_s: float = 60.0
    """Anti-burst pause, in seconds: no other cry alert until it is over."""


@dataclass(frozen=True)
class PipelineStats:
    """State of the chain, for monitoring."""

    level_db: float
    """Level of the last hop after the high-pass filter, in dBFS."""
    floor_db: float
    """Noise floor, in dBFS."""
    mic_silent: bool
    """True after 10 s of digital silence: the micro is probably unplugged."""
    last_alert: AlertEvent | None
    """Last alert sent, if any."""


class DetectionPipeline:
    """Turn a stream of sound into alerts; alerts are only sent in the `sieste` mode."""

    def __init__(
        self,
        classifier: Classifier,
        config: DetectionConfig,
        mode_provider: Callable[[], Mode],
        clock: Callable[[], datetime],
    ) -> None:
        self._classifier = classifier
        self._config = config
        self._mode_provider = mode_provider
        self._clock = clock
        self._pending = np.zeros(0, dtype=np.float32)
        self._hops: deque[Audio] = deque(maxlen=_HOPS_PER_WINDOW)
        self._gate: deque[bool] = deque(maxlen=_HOPS_PER_WINDOW)
        self._samples_done = 0
        self._level_db = SILENCE_DB
        self._last_alert: AlertEvent | None = None
        self._high_pass = HighPass()
        self._floor = NoiseFloor()
        self._mic = MicHealth()
        self._decider = SlidingWindowDecider(THRESHOLDS[config.sensitivity], n=config.n, k=config.k)
        self._scream_net = ScreamNet()
        self._anti_burst = AntiBurst(pause_s=config.pause_s)

    @property
    def stats(self) -> PipelineStats:
        return PipelineStats(self._level_db, self._floor.value_db, self._mic.is_silent, self._last_alert)

    def feed(self, chunk: Audio) -> list[AlertEvent]:
        """Add sound of any length; return the alerts decided on the complete hops."""
        # A damaged sample (NaN, infinity) would spread to the filter and the floor for good.
        self._pending = np.concatenate([self._pending, clean_samples(chunk).astype(np.float32, copy=False)])
        alerts: list[AlertEvent] = []
        while len(self._pending) >= HOP:
            hop, self._pending = self._pending[:HOP], self._pending[HOP:]
            alert = self._process_hop(hop)
            if alert is not None:
                alerts.append(alert)
        return alerts

    def _process_hop(self, hop: Audio) -> AlertEvent | None:
        self._samples_done += HOP
        # The level is measured without the slow drift of the micro; the model gets the raw sound.
        level_db = rms_dbfs(self._high_pass.process(hop))
        # A new sound is compared to the background as it was before it.
        floor_db = self._floor.value_db if self._floor.started else level_db
        self._floor.update(level_db, HOP_S)
        self._mic.update(level_db, HOP_S)
        self._level_db = level_db
        self._hops.append(hop)
        self._gate.append(level_db - floor_db >= self._config.gate_margin_db)

        scores = {}
        if any(self._gate) and len(self._hops) == _HOPS_PER_WINDOW:
            scores = dict(self._classifier.scores(np.concatenate(self._hops)))
        decision = self._decider.push(scores)
        scream = self._scream_net.push(scores.get(SoundClass.SCREAM, 0.0))

        if self._mode_provider() != Mode.SIESTE:
            return None
        offset_s = self._samples_done / SAMPLE_RATE
        if decision is not None and self._anti_burst.allow(offset_s, via_scream_net=False):
            return self._alert(decision, offset_s, via_scream_net=False)
        if scream and self._anti_burst.allow(offset_s, via_scream_net=True):
            return self._alert(SoundClass.SCREAM, offset_s, via_scream_net=True)
        return None

    def _alert(self, kind: SoundClass, offset_s: float, via_scream_net: bool) -> AlertEvent:
        # The time is read when the alert is decided: the clock of the Pi may be set after the start.
        event = AlertEvent(uuid.uuid4(), kind, self._clock(), offset_s, via_scream_net)
        self._last_alert = event
        return event
