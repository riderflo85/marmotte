"""Sound classifier: the model behind a small interface (one slice in, retained category scores out)."""

import csv
from collections.abc import Mapping
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

import numpy as np
from ai_edge_litert.interpreter import Interpreter
from numpy.typing import NDArray

from marmotte.common.enums import SoundClass
from marmotte.detection.types import WINDOW
from marmotte.detection.types import Audio

DEFAULT_CLASS_MAP = Path(__file__).parent / "data" / "yamnet_class_map.csv"
"""YAMNet class names, from tensorflow/models (research/audioset/yamnet, Apache 2.0)."""

YAMNET_NAMES: dict[SoundClass, tuple[str, ...]] = {
    # "Crying, sobbing" often scores above "Baby cry" on real cries: with it, no long cry is missed on the bench.
    SoundClass.CRY: ("Baby cry, infant cry", "Crying, sobbing"),
    SoundClass.WHIMPER: ("Whimper",),
    SoundClass.BABBLE: ("Babbling",),
    SoundClass.LAUGH: ("Baby laughter",),
    SoundClass.SCREAM: ("Screaming",),
}
"""YAMNet names grouped in each retained category, matched by name (never by number)."""


class Classifier(Protocol):
    """Give the retained category scores of one slice of WINDOW samples."""

    def scores(self, window: Audio) -> Mapping[SoundClass, float]:
        """Scores in [0, 1], by category."""
        ...


def load_class_names(path: Path) -> list[str]:
    """Read the display names of a YAMNet class map, in index order."""
    with path.open(newline="") as f:
        return [row["display_name"] for row in csv.DictReader(f)]


def class_indices(
    class_names: Sequence[str], names_by_class: Mapping[SoundClass, tuple[str, ...]]
) -> dict[SoundClass, tuple[int, ...]]:
    """Find the model output index of each retained name, by exact match."""
    indices: dict[SoundClass, tuple[int, ...]] = {}
    for sound_class, names in names_by_class.items():
        missing = [name for name in names if name not in class_names]
        if missing:
            raise ValueError(f"Not in the class map: {', '.join(missing)}")
        indices[sound_class] = tuple(class_names.index(name) for name in names)
    return indices


def retained_scores(raw: NDArray[np.float32], indices: Mapping[SoundClass, tuple[int, ...]]) -> dict[SoundClass, float]:
    """Keep the retained categories; a category gets the highest score of its names."""
    return {sound_class: float(max(raw[i] for i in group)) for sound_class, group in indices.items()}


class YamnetClassifier:
    """YAMNet (classification variant) run with LiteRT."""

    def __init__(self, model_path: Path, class_map: Path = DEFAULT_CLASS_MAP, num_threads: int = 1) -> None:
        self._indices = class_indices(load_class_names(class_map), YAMNET_NAMES)
        self._interpreter = Interpreter(model_path=str(model_path), num_threads=num_threads)
        self._interpreter.allocate_tensors()
        self._input = self._interpreter.get_input_details()[0]["index"]
        self._output = self._interpreter.get_output_details()[0]["index"]

    def scores(self, window: Audio) -> dict[SoundClass, float]:
        if window.shape != (WINDOW,):
            raise ValueError(f"YAMNet needs {WINDOW} samples, got {window.shape}")
        self._interpreter.set_tensor(self._input, window.astype(np.float32, copy=False))
        self._interpreter.invoke()
        return retained_scores(self._interpreter.get_tensor(self._output)[0], self._indices)
