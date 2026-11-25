"""Sound format and alert event shared by the detection chain."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import numpy as np
from numpy.typing import NDArray

from marmotte.common.enums import SoundClass

SAMPLE_RATE = 16_000
"""Internal sample rate (Hz): the one YAMNet expects."""
WINDOW = 15_600
"""Samples in a YAMNet slice (0.975 s)."""
HOP = 7_800
"""Samples between two slices (0.4875 s): a slice is two hops."""

type Audio = NDArray[np.float32]
"""Mono sound at SAMPLE_RATE, values in [-1, 1]."""


@dataclass(frozen=True)
class AlertEvent:
    """An alert decided by the detection chain."""

    id: UUID
    kind: SoundClass
    at: datetime
    offset_s: float
    """Position in the audio stream, in seconds."""
    via_scream_net: bool
