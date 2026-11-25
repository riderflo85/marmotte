"""Command line of the detection service: `python -m marmotte.detection --wav FILE` or `--alsa DEVICE`.

Alerts are printed as JSON lines; the stats are logged on the error output every 10 seconds.
The mode is fixed to `sieste` (lot 4 plugs in the real mode).
"""

import argparse
import contextlib
import logging
import sys
from datetime import UTC
from datetime import datetime
from pathlib import Path

from marmotte.common.enums import Mode
from marmotte.common.enums import Sensitivity
from marmotte.detection.audio import AlsaSource
from marmotte.detection.audio import AudioSource
from marmotte.detection.audio import WavFileSource
from marmotte.detection.classifier import YamnetClassifier
from marmotte.detection.model_files import DEFAULT_MODELS_DIR
from marmotte.detection.model_files import ensure_yamnet
from marmotte.detection.pipeline import DetectionConfig
from marmotte.detection.pipeline import DetectionPipeline
from marmotte.detection.service import run
from marmotte.detection.sinks import JsonLinesSink

STATS_EVERY_S = 10.0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m marmotte.detection", description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--wav", type=Path, metavar="PATH", help="sound file to read (WAV, FLAC…)")
    source.add_argument("--alsa", metavar="DEVICE", help="ALSA device to listen to (e.g. micro)")
    parser.add_argument("--loop", action="store_true", help="read the sound file again and again")
    parser.add_argument("--sensitivity", choices=[s.value for s in Sensitivity], default=Sensitivity.MEDIUM.value)
    parser.add_argument("--models-dir", type=Path, default=DEFAULT_MODELS_DIR, metavar="PATH")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(levelname)s %(message)s")
    source: AudioSource = WavFileSource(args.wav, loop=args.loop) if args.wav else AlsaSource(args.alsa)
    pipeline = DetectionPipeline(
        YamnetClassifier(ensure_yamnet(args.models_dir)),
        DetectionConfig(sensitivity=Sensitivity(args.sensitivity)),
        lambda: Mode.SIESTE,
        datetime.now(UTC),
    )
    # Ctrl+C stops listening without a traceback.
    with contextlib.suppress(KeyboardInterrupt):
        run(source, pipeline, JsonLinesSink(sys.stdout), stats_every_s=STATS_EVERY_S)
    return 0


if __name__ == "__main__":
    sys.exit(main())
