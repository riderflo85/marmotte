"""Replay the bench through the detection chain and measure missed cries and false alerts (D81)."""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field
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
DETECTION_BUDGET_S = 8.0
LEAD_S = 10.0
"""Quiet room before each baby sound: the noise floor settles (the 30 s countdown does it in real life)."""
TAIL_S = 5.0
BACKGROUND_TARGET_S = 7_200.0
GAIN_RANGE_DB = 6.0
BENCH_START = datetime(2026, 1, 1, tzinfo=UTC)
"""Fixed start: reproducible alert times."""

type PipelineFactory = Callable[[Callable[[], Mode]], DetectionPipeline]


def missed_long_cries(
    segments: list[tuple[float, float]],
    alert_offsets: list[float],
    shift_s: float,
    long_s: float = LONG_CRY_S,
    budget_s: float = DETECTION_BUDGET_S,
    pause_s: float = 0.0,
) -> tuple[int, int]:
    """Count the cries longer than `long_s`, and those with no alert within `budget_s` of their onset.

    An alert less than `pause_s` before the onset counts too: the parent was just notified, and the
    anti-burst pause holds the next alert back on purpose.
    Segments are relative to the clip, which starts `shift_s` seconds into the stream.
    """
    long_cries = [(start + shift_s, end + shift_s) for start, end in segments if end - start > long_s]
    missed = sum(
        not any(onset - pause_s <= offset <= onset + budget_s for offset in alert_offsets) for onset, _ in long_cries
    )
    return len(long_cries), missed


def false_alerts_per_2h(n_alerts: int, seconds: float) -> float:
    """Scale a number of false alerts to a two-hour nap."""
    return n_alerts * 7_200.0 / seconds


@dataclass
class BenchReport:
    """Results of the bench, and the D81 targets."""

    long_cries: int
    missed_long_cries: int
    false_alerts: int
    background_s: float
    false_alerts_per_2h: float
    recall_by_label: dict[str, float]
    missed_clips: list[str] = field(default_factory=list)
    false_alert_details: list[str] = field(default_factory=list)

    def meets_targets(self) -> bool:
        """D81: no long cry missed, at most one false alert per two hours, measured on enough sound."""
        measured = self.long_cries > 0 and self.background_s >= BACKGROUND_TARGET_S
        return measured and self.missed_long_cries == 0 and self.false_alerts_per_2h <= 1.0

    def to_text(self) -> str:
        lines = [
            f"Long cries (> {LONG_CRY_S:g} s): {self.long_cries}, missed: {self.missed_long_cries}",
            f"False alerts: {self.false_alerts} in {self.background_s / 3600:.2f} h"
            f" = {self.false_alerts_per_2h:.2f} per 2 h",
            "Recall by label: "
            + ", ".join(f"{label} {recall:.0%}" for label, recall in sorted(self.recall_by_label.items())),
            *(f"  missed: {name}" for name in self.missed_clips),
            *(f"  false alert: {detail}" for detail in self.false_alert_details),
            "Targets (D81): " + ("met" if self.meets_targets() else "NOT met"),
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
    """A pipeline with the real YAMNet (loaded once) and a fixed start time."""
    return DetectionPipeline(_yamnet_classifier(), config or DetectionConfig(), mode_provider, BENCH_START)


def _sieste() -> Mode:
    return Mode.SIESTE


def run_bench(clips: list[Clip], make_pipeline: PipelineFactory, seed: int = 42) -> BenchReport:
    """Replay each baby sound between quiet room sounds, then at least two hours of backgrounds."""
    rng = np.random.default_rng(seed)
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
        padding = np.resize(load_audio(rooms[rng.integers(len(rooms))].file), lead + int(TAIL_S * SAMPLE_RATE))
        audio = load_audio(clip.file)
        pipeline = make_pipeline(_sieste)
        offsets = [alert.offset_s for alert in pipeline.feed(np.concatenate([padding[:lead], audio, padding[lead:]]))]
        end_s = LEAD_S + len(audio) / SAMPLE_RATE + TAIL_S
        detected[clip.label].append(any(LEAD_S <= offset <= end_s for offset in offsets))
        if clip.label == "cry":
            n_long, n_missed = missed_long_cries(list(clip.segments), offsets, LEAD_S, pause_s=pipeline.config.pause_s)
            long_cries += n_long
            missed += n_missed
            if n_missed:
                missed_clips.append(clip.file.name)

    false_alerts = 0
    details: list[str] = []
    background_s = 0.0
    if backgrounds:
        pipeline = make_pipeline(_sieste)
        while background_s < BACKGROUND_TARGET_S:
            for index in rng.permutation(len(backgrounds)):
                clip = backgrounds[index]
                gain = 10 ** (rng.uniform(-GAIN_RANGE_DB, GAIN_RANGE_DB) / 20)
                audio = np.clip(load_audio(clip.file) * gain, -1.0, 1.0).astype(np.float32)
                for alert in pipeline.feed(audio):
                    false_alerts += 1
                    net = ", scream net" if alert.via_scream_net else ""
                    details.append(f"{clip.file.name} ({alert.kind}{net}) at {alert.offset_s:.1f} s")
                background_s += len(audio) / SAMPLE_RATE
                if background_s >= BACKGROUND_TARGET_S:
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
