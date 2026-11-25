"""Bench manifest: the list of clips, their label, their license and their cry segments."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parents[3] / "bench"
"""`backend/bench/`: manifest, credits and clips of the published bench."""
BENCH_MANIFEST = BENCH_DIR / "manifest.toml"
LOCAL_MANIFEST = BENCH_DIR / "local" / "manifest.toml"
"""Local bench (ignored by Git), for trials with recordings that are not free (videos…)."""

LICENSE_URLS = {
    "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "CC-BY-3.0": "https://creativecommons.org/licenses/by/3.0/",
    "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
}
"""Text of each accepted license, linked from the credits (CC BY asks for it)."""
FREE_LICENSES = frozenset(LICENSE_URLS)
BABY_LABELS = ("cry", "whimper", "babble", "laugh", "scream")
LABELS = (*BABY_LABELS, "background")


@dataclass(frozen=True)
class Clip:
    """One sound of the bench."""

    file: Path
    label: str
    tags: tuple[str, ...]
    """For backgrounds: "room" (quiet room), "music", "tv"…"""
    source: str
    author: str
    license: str
    segments: tuple[tuple[float, float], ...]
    """For baby sounds: [start, end] of each crying episode, in seconds."""


def check_license(license_id: str) -> None:
    """Refuse any license but CC0 and CC BY (D81)."""
    if license_id not in FREE_LICENSES:
        raise ValueError(f"License {license_id} refused: only {', '.join(sorted(FREE_LICENSES))}")


def check_label(label: str) -> None:
    """Refuse an unknown label."""
    if label not in LABELS:
        raise ValueError(f"Unknown label {label}: expected one of {', '.join(LABELS)}")


def load_manifest(path: Path, any_license: bool = False) -> list[Clip]:
    """Read a manifest; clip files are relative to it. `any_license` is for the local bench only."""
    with path.open("rb") as f:
        entries = tomllib.load(f).get("clip", [])
    clips: list[Clip] = []
    for entry in entries:
        check_label(entry["label"])
        if not any_license:
            check_license(entry["license"])
        clips.append(
            Clip(
                file=path.parent / entry["file"],
                label=entry["label"],
                tags=tuple(entry.get("tags", [])),
                source=entry["source"],
                author=entry["author"],
                license=entry["license"],
                segments=tuple((float(start), float(end)) for start, end in entry.get("segments", [])),
            )
        )
    return clips
