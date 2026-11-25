"""Bench manifest: the list of clips, their label, their license and their cry segments."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parents[3] / "bench"
"""`backend/bench/`: manifest, credits and clips of the published bench."""
BENCH_MANIFEST = BENCH_DIR / "manifest.toml"
"""List of the published bench sounds, with their label, license and cry segments."""
LOCAL_MANIFEST = BENCH_DIR / "local" / "manifest.toml"
"""Local bench (ignored by Git), for trials with recordings that are not free (videos…)."""

LICENSE_URLS = {
    "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "CC-BY-3.0": "https://creativecommons.org/licenses/by/3.0/",
    "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
}
"""Text of each accepted license, linked from the credits (CC BY asks for it)."""
FREE_LICENSES = frozenset(LICENSE_URLS)
"""Licenses accepted in the published bench: CC0 and CC BY only (D81)."""
BABY_LABELS = ("cry", "whimper", "babble", "laugh", "scream")
"""Labels of the baby sounds: each should give an alert."""
LABELS = (*BABY_LABELS, "background")
"""Every label a clip may have; backgrounds should give no alert."""


@dataclass(frozen=True)
class Clip:
    """One sound of the bench."""

    file: Path
    """Sound file (mono 16 kHz FLAC), resolved from the manifest folder."""
    label: str
    """One of `LABELS`."""
    tags: tuple[str, ...]
    """For backgrounds: "room" (quiet room), "music", "tv"…"""
    source: str
    """Page of the original sound (Freesound)."""
    author: str
    """Author of the original sound, as credited."""
    license: str
    """SPDX identifier of the license ("CC0-1.0", "CC-BY-4.0"…)."""
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
