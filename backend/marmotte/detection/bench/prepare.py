"""Add a sound to the bench: convert it to mono 16 kHz FLAC, list it in the manifest and the credits."""

import json
import re
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import soundfile as sf

from marmotte.detection.audio import to_mono_16k
from marmotte.detection.bench.manifest import LICENSE_URLS
from marmotte.detection.bench.manifest import Clip
from marmotte.detection.bench.manifest import check_label
from marmotte.detection.bench.manifest import check_license
from marmotte.detection.types import SAMPLE_RATE

CREDITS_HEADER = """# Crédits des sons

Sons sous licence libre (CC0 ou CC BY) utilisés par les tests et le banc d'essai de la détection.
Les sons CC0 n'exigent pas de crédit : ils sont listés pour la traçabilité. Chemins relatifs à `backend/`.

| Fichier | Son d'origine | Auteur | Licence | Modification |
|---|---|---|---|---|
"""
"""Start of `CREDITS.md`, written when the bench has no credits file yet."""


def parse_segments(text: str) -> list[tuple[float, float]]:
    """Read segments written as "0:12.5,20:31"."""
    segments = []
    for part in filter(None, (p.strip() for p in text.split(","))):
        start, end = (float(value) for value in part.split(":"))
        if end <= start:
            raise ValueError(f"Segment {part}: the end must come after the start")
        segments.append((start, end))
    return segments


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "clip"


def prepare_clip(
    input_path: Path,
    bench_dir: Path,
    *,
    label: str,
    source_url: str,
    author: str,
    license: str,
    segments: Sequence[tuple[float, float]] = (),
    tags: Sequence[str] = (),
    name: str | None = None,
    title: str | None = None,
) -> Clip:
    """Convert `input_path` into `bench_dir/clips/`, then add it to the manifest and the credits."""
    check_license(license)
    check_label(label)
    data, rate = sf.read(input_path, dtype="float32", always_2d=True)
    audio = to_mono_16k(np.asarray(data, dtype=np.float32), rate)
    output = bench_dir / "clips" / f"{_slug(name or input_path.stem)}.flac"
    if output.exists():
        raise FileExistsError(f"{output} already exists: choose another --name")
    output.parent.mkdir(parents=True, exist_ok=True)
    sf.write(output, audio, SAMPLE_RATE, subtype="PCM_16")

    relative = output.relative_to(bench_dir).as_posix()
    entry = (
        "\n[[clip]]\n"
        f"file = {json.dumps(relative)}\n"
        f"label = {json.dumps(label)}\n"
        f"tags = {json.dumps(list(tags))}\n"
        f"source = {json.dumps(source_url)}\n"
        f"author = {json.dumps(author)}\n"
        f"license = {json.dumps(license)}\n"
        f"segments = {json.dumps([[start, end] for start, end in segments])}\n"
    )
    with (bench_dir / "manifest.toml").open("a") as f:
        f.write(entry)

    credits_path = bench_dir / "CREDITS.md"
    if not credits_path.exists():
        credits_path.write_text(CREDITS_HEADER)
    origin = f"[{title}]({source_url})" if title else source_url
    with credits_path.open("a") as f:
        license_link = f"[{license}]({LICENSE_URLS[license]})"
        f.write(f"| `{bench_dir.name}/{relative}` | {origin} | {author} | {license_link} | mono 16 kHz |\n")

    return Clip(output, label, tuple(tags), source_url, author, license, tuple(segments))
