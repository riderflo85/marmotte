"""Detection service loop: read a source, feed the pipeline, send the alerts."""

import logging

from marmotte.detection.audio import AudioSource
from marmotte.detection.pipeline import DetectionPipeline
from marmotte.detection.sinks import AlertSink
from marmotte.detection.types import HOP
from marmotte.detection.types import SAMPLE_RATE

logger = logging.getLogger(__name__)


def run(source: AudioSource, pipeline: DetectionPipeline, sink: AlertSink, stats_every_s: float | None = None) -> None:
    """Read `source` hop by hop until its end; log the pipeline stats every `stats_every_s` seconds of sound."""
    elapsed_s = 0.0
    next_stats_s = stats_every_s
    while (chunk := source.read(HOP)) is not None:
        for event in pipeline.feed(chunk):
            sink.emit(event)
        elapsed_s += len(chunk) / SAMPLE_RATE
        if stats_every_s is not None and next_stats_s is not None and elapsed_s >= next_stats_s:
            stats = pipeline.stats
            logger.info(
                "level %.1f dBFS, floor %.1f dBFS, mic silent: %s, last alert: %s",
                stats.level_db,
                stats.floor_db,
                stats.mic_silent,
                stats.last_alert.kind if stats.last_alert else None,
            )
            next_stats_s += stats_every_s
