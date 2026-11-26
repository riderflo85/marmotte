"""Bench commands: `prepare` adds a sound, `run` replays the bench with YAMNet (exit code 1 if the CI gate fails)."""

import argparse
import sys
from pathlib import Path

from marmotte.common.enums import Sensitivity
from marmotte.detection.bench.manifest import BENCH_DIR
from marmotte.detection.bench.manifest import BENCH_MANIFEST
from marmotte.detection.bench.manifest import LABELS
from marmotte.detection.bench.manifest import LOCAL_MANIFEST
from marmotte.detection.bench.manifest import load_manifest
from marmotte.detection.bench.prepare import parse_segments
from marmotte.detection.bench.prepare import prepare_clip
from marmotte.detection.bench.runner import make_yamnet_pipeline
from marmotte.detection.bench.runner import run_bench
from marmotte.detection.pipeline import DetectionConfig


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m marmotte.detection.bench", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser("prepare", help="convert a sound and add it to the bench")
    prepare.add_argument("input", type=Path, metavar="INPUT")
    prepare.add_argument("--label", required=True, choices=LABELS)
    prepare.add_argument("--source", required=True, metavar="URL")
    prepare.add_argument("--author", required=True)
    prepare.add_argument("--license", required=True, metavar="LICENSE", help="CC0-1.0, CC-BY-3.0 or CC-BY-4.0")
    prepare.add_argument("--segments", default="", help='crying episodes, e.g. "0:12.5,20:31" (seconds)')
    prepare.add_argument("--tags", default="", help='e.g. "room" or "music,party"')
    prepare.add_argument("--name", help="name of the clip file (default: from INPUT)")
    prepare.add_argument("--title", help="title of the original sound, for the credits")
    prepare.add_argument("--bench-dir", type=Path, default=BENCH_DIR, metavar="PATH")

    run = commands.add_parser("run", help="replay the bench and print the report")
    run.add_argument("--manifest", type=Path, default=BENCH_MANIFEST, metavar="PATH")
    run.add_argument("--local", action="store_true", help=f"add the local bench ({LOCAL_MANIFEST})")
    run.add_argument("--sensitivity", choices=[s.value for s in Sensitivity], default=Sensitivity.MEDIUM.value)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.command == "prepare":
        clip = prepare_clip(
            args.input,
            args.bench_dir,
            label=args.label,
            source_url=args.source,
            author=args.author,
            license=args.license,
            segments=parse_segments(args.segments),
            tags=[tag.strip() for tag in args.tags.split(",") if tag.strip()],
            name=args.name,
            title=args.title,
        )
        print(f"Added {clip.file}")
        return 0
    clips = load_manifest(args.manifest)
    if args.local:
        clips += load_manifest(LOCAL_MANIFEST, any_license=True)
    sensitivity = Sensitivity(args.sensitivity)
    report = run_bench(clips, make_yamnet_pipeline, config=DetectionConfig(sensitivity=sensitivity))
    print(f"Sensitivity: {sensitivity}")
    print(report.to_text())
    return 0 if report.passes_ci_gate() else 1


if __name__ == "__main__":
    sys.exit(main())
