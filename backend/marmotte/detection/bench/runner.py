"""Replay the bench through the detection chain and measure missed cries and false alerts (D81)."""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from datetime import UTC
from datetime import datetime
from functools import cache
from pathlib import Path

import numpy as np
import soundfile as sf

from marmotte.common.enums import Mode
from marmotte.detection.audio import to_mono_16k
from marmotte.detection.bench.manifest import BABY_LABELS
from marmotte.detection.bench.manifest import Clip
from marmotte.detection.classifier import YamnetClassifier
from marmotte.detection.model_files import DEFAULT_MODELS_DIR
from marmotte.detection.model_files import ensure_yamnet
from marmotte.detection.pipeline import DetectionConfig
from marmotte.detection.pipeline import DetectionPipeline
from marmotte.detection.types import SAMPLE_RATE
from marmotte.detection.types import Audio

LONG_CRY_S = 8.0
"""A cry longer than this must never be missed (D81)."""
DETECTION_BUDGET_S = 8.0
"""Delay allowed between the onset of a long cry and its alert (D24)."""
LEAD_S = 15.0
"""Quiet room before each baby sound, longer than the 10 s warm-up of the noise floor: the floor has settled
when the sound starts, as after the 30 s countdown in real life."""
TAIL_S = 5.0
"""Quiet room after each baby sound: an alert decided just after the sound still counts."""
MIN_BACKGROUND_S = 7_200.0
"""D81: false alerts are measured on at least 2 hours of backgrounds."""
BACKGROUND_TARGET_S = 21_600.0
"""Seconds of backgrounds replayed: 6 hours, so that the false alert rate hardly depends on the draw."""
TARGET_FALSE_ALERTS_PER_2H = 2.0
"""D81 (amended on 2026-11-26): at most two false alerts per 2-hour nap. YAMNet alerts on a door creak,
accepted since it may tell that someone enters the room."""
MAX_FALSE_ALERTS_PER_2H = 1.34
"""CI gate (P67): 4 false alerts in 6 h (1.33 per 2 h, all from the door creak) when lot 2 was tuned;
more is a regression, even under the D81 target (`docs/plans/resultats-tests-prealables.md`)."""
GAIN_RANGE_DB = 6.0
"""Each background is replayed with a random gain within ± this value."""
BENCH_TIME = datetime(2026, 1, 1, tzinfo=UTC)
"""Time given by the clock of the bench pipelines: reproducible alerts."""

type PipelineFactory = Callable[[Callable[[], Mode], DetectionConfig], DetectionPipeline]
"""Build a fresh pipeline from a mode provider and settings."""


def missed_long_cries(
    segments: list[tuple[float, float]],
    alert_offsets: list[float],
    shift_s: float,
    long_s: float = LONG_CRY_S,
    budget_s: float = DETECTION_BUDGET_S,
) -> tuple[int, int]:
    """Count the cries longer than `long_s`, and those with no alert within `budget_s` of their onset.

    Segments are relative to the clip, which starts `shift_s` seconds into the stream.
    """
    long_cries = [(start + shift_s, end + shift_s) for start, end in segments if end - start > long_s]
    missed = sum(not any(onset <= offset <= onset + budget_s for offset in alert_offsets) for onset, _ in long_cries)
    return len(long_cries), missed


def false_alerts_per_2h(n_alerts: int, seconds: float) -> float:
    """Scale a number of false alerts to a two-hour nap."""
    return n_alerts * 7_200.0 / seconds


@dataclass
class BenchReport:
    """Results of the bench, and the D81 targets."""

    long_cries: int
    """Cries longer than `LONG_CRY_S` in the baby sounds."""
    missed_long_cries: int
    """Long cries with no alert within `DETECTION_BUDGET_S` of their onset."""
    false_alerts: int
    """Alerts during the backgrounds."""
    background_s: float
    """Seconds of backgrounds replayed."""
    false_alerts_per_2h: float
    """False alerts scaled to a two-hour nap."""
    recall_by_label: dict[str, float]
    """Share of the baby sounds of each label with at least one alert."""
    missed_clips: list[str] = field(default_factory=list)
    """Cry files with a missed long cry."""
    false_alert_details: list[str] = field(default_factory=list)
    """One line per false alert: file, kind and time in the background stream."""

    def meets_targets(self) -> bool:
        """D81: no long cry missed, at most two false alerts per two hours, measured on enough sound."""
        return (
            self._measured() and self.missed_long_cries == 0 and self.false_alerts_per_2h <= TARGET_FALSE_ALERTS_PER_2H
        )

    def passes_ci_gate(self) -> bool:
        """P67: no long cry missed, and no more false alerts than when the detection was tuned."""
        return self._measured() and self.missed_long_cries == 0 and self.false_alerts_per_2h <= MAX_FALSE_ALERTS_PER_2H

    def _measured(self) -> bool:
        return self.long_cries > 0 and self.background_s >= MIN_BACKGROUND_S

    def to_text(self) -> str:
        lines = [
            f"Long cries (> {LONG_CRY_S:g} s): {self.long_cries}, missed: {self.missed_long_cries}",
            f"False alerts: {self.false_alerts} in {self.background_s / 3600:.2f} h"
            f" = {self.false_alerts_per_2h:.2f} per 2 h",
            "Recall by label: "
            + ", ".join(f"{label} {recall:.0%}" for label, recall in sorted(self.recall_by_label.items())),
            *(f"  missed: {name}" for name in self.missed_clips),
            *(f"  false alert: {detail}" for detail in self.false_alert_details),
            f"Targets (D81: no missed long cry, at most {TARGET_FALSE_ALERTS_PER_2H:g} false alerts per 2 h): "
            + ("met" if self.meets_targets() else "NOT met"),
            f"CI gate (no missed long cry, at most {MAX_FALSE_ALERTS_PER_2H:g} false alerts per 2 h): "
            + ("passed" if self.passes_ci_gate() else "FAILED"),
        ]
        return "\n".join(lines)


def load_audio(path: Path) -> Audio:
    """Read a clip as mono 16 kHz float32."""
    data, rate = sf.read(path, dtype="float32", always_2d=True)
    return to_mono_16k(np.asarray(data, dtype=np.float32), rate)


@cache
def _yamnet_classifier() -> YamnetClassifier:
    return YamnetClassifier(ensure_yamnet(DEFAULT_MODELS_DIR))


def make_yamnet_pipeline(mode_provider: Callable[[], Mode], config: DetectionConfig | None = None) -> DetectionPipeline:
    """A pipeline with the real YAMNet (loaded once) and a fixed clock."""
    return DetectionPipeline(_yamnet_classifier(), config or DetectionConfig(), mode_provider, lambda: BENCH_TIME)


def _sieste() -> Mode:
    return Mode.SIESTE


def run_bench(
    clips: list[Clip],
    make_pipeline: PipelineFactory,
    seed: int = 42,
    config: DetectionConfig | None = None,
    background_target_s: float = BACKGROUND_TARGET_S,
) -> BenchReport:
    """Replay each baby sound between quiet room sounds, then at least two hours of backgrounds.

    Baby sounds are replayed without the anti-burst pause, so that each long cry must be detected on
    its own; backgrounds are replayed with the settings as they run in real life.
    """
    config = config or DetectionConfig()
    # Two independent draws: adding a baby sound does not change the backgrounds' order and gains.
    baby_rng = np.random.default_rng([seed, 0])
    background_rng = np.random.default_rng([seed, 1])
    rooms = [clip for clip in clips if clip.label == "background" and "room" in clip.tags]
    babies = [clip for clip in clips if clip.label in BABY_LABELS]
    backgrounds = [clip for clip in clips if clip.label == "background"]
    if babies and not rooms:
        raise ValueError('The bench needs at least one background clip tagged "room"')

    long_cries = missed = 0
    missed_clips: list[str] = []
    detected: dict[str, list[bool]] = defaultdict(list)
    lead = int(LEAD_S * SAMPLE_RATE)
    for clip in babies:
        padding = np.resize(load_audio(rooms[baby_rng.integers(len(rooms))].file), lead + int(TAIL_S * SAMPLE_RATE))
        audio = load_audio(clip.file)
        # Without the anti-burst pause: an earlier alert must not hide a long cry the chain misses.
        pipeline = make_pipeline(_sieste, replace(config, pause_s=0.0))
        offsets = [alert.offset_s for alert in pipeline.feed(np.concatenate([padding[:lead], audio, padding[lead:]]))]
        end_s = LEAD_S + len(audio) / SAMPLE_RATE + TAIL_S
        detected[clip.label].append(any(LEAD_S <= offset <= end_s for offset in offsets))
        if clip.label == "cry":
            n_long, n_missed = missed_long_cries(list(clip.segments), offsets, LEAD_S)
            long_cries += n_long
            missed += n_missed
            if n_missed:
                missed_clips.append(clip.file.name)

    false_alerts = 0
    details: list[str] = []
    background_s = 0.0
    if backgrounds:
        pipeline = make_pipeline(_sieste, config)
        while background_s < background_target_s:
            for index in background_rng.permutation(len(backgrounds)):
                clip = backgrounds[index]
                gain = 10 ** (background_rng.uniform(-GAIN_RANGE_DB, GAIN_RANGE_DB) / 20)
                audio = np.clip(load_audio(clip.file) * gain, -1.0, 1.0).astype(np.float32)
                for alert in pipeline.feed(audio):
                    false_alerts += 1
                    net = ", scream net" if alert.via_scream_net else ""
                    details.append(f"{clip.file.name} ({alert.kind}{net}) at {alert.offset_s:.1f} s")
                background_s += len(audio) / SAMPLE_RATE
                if background_s >= background_target_s:
                    break

    return BenchReport(
        long_cries=long_cries,
        missed_long_cries=missed,
        false_alerts=false_alerts,
        background_s=background_s,
        false_alerts_per_2h=false_alerts_per_2h(false_alerts, background_s) if background_s else 0.0,
        recall_by_label={label: sum(hits) / len(hits) for label, hits in detected.items()},
        missed_clips=missed_clips,
        false_alert_details=details,
    )
