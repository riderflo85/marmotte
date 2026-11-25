"""Audio sources: arrays, sound files and the shared ALSA micro, all as mono 16 kHz float32."""

import logging
from math import gcd
from pathlib import Path
from typing import Protocol

import numpy as np
import soundfile as sf
from numpy.typing import NDArray
from scipy.signal import resample_poly

from marmotte.detection.types import HOP
from marmotte.detection.types import SAMPLE_RATE
from marmotte.detection.types import Audio

logger = logging.getLogger(__name__)


def clean_samples(data: NDArray[np.floating]) -> NDArray[np.floating]:
    """Replace NaN and infinities with silence and clip to [-1, 1]."""
    return np.clip(np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0), -1.0, 1.0)


def to_mono_16k(data: NDArray[np.floating], rate: int) -> Audio:
    """Convert samples (frames, or frames x channels) at `rate` Hz to the internal format.

    Channels are averaged; damaged values are cleaned before resampling so they cannot spread.
    """
    samples = clean_samples(np.asarray(data, dtype=np.float64))
    if samples.ndim == 2:
        samples = samples.mean(axis=1)
    if rate != SAMPLE_RATE:
        divisor = gcd(SAMPLE_RATE, rate)
        samples = resample_poly(samples, SAMPLE_RATE // divisor, rate // divisor)
    return clean_samples(samples).astype(np.float32)


class AudioSource(Protocol):
    """A stream of mono 16 kHz float32 sound."""

    def read(self, n: int) -> Audio | None:
        """Return the next `n` samples, or None at the end of the stream."""
        ...

    def close(self) -> None:
        """Release the device behind the stream, if any."""
        ...


class ArraySource:
    """Serve samples already in memory, padding the last chunk with zeros."""

    def __init__(self, samples: Audio, loop: bool = False) -> None:
        self._samples = samples
        self._loop = loop
        self._position = 0

    def read(self, n: int) -> Audio | None:
        total = len(self._samples)
        if total == 0 or (self._position >= total and not self._loop):
            return None
        if self._loop:
            indices = (self._position + np.arange(n)) % total
            self._position = (self._position + n) % total
            return self._samples[indices]
        chunk = self._samples[self._position : self._position + n]
        self._position += n
        if len(chunk) < n:
            chunk = np.concatenate([chunk, np.zeros(n - len(chunk), dtype=np.float32)])
        return chunk

    def close(self) -> None:
        """Nothing to release: the samples are in memory."""


class WavFileSource(ArraySource):
    """Read a whole sound file (WAV, FLAC…) once, then serve it in chunks."""

    def __init__(self, path: Path, loop: bool = False) -> None:
        data, rate = sf.read(path, dtype="float32", always_2d=True)
        super().__init__(to_mono_16k(np.asarray(data, dtype=np.float32), rate), loop=loop)


class AlsaSource:
    """Read an ALSA device in stereo at 16 kHz and keep one channel.

    The INMP441 micro only sends on the left channel: asking `plug` for mono would average it
    with the silent right channel (-6 dB).
    """

    def __init__(self, device: str = "micro", block: int = HOP, channel: int = 0) -> None:
        # Imported here: PortAudio is only needed with a real micro (absent in CI).
        import sounddevice

        self._channel = channel
        self._stream = sounddevice.InputStream(
            device=device, channels=2, samplerate=SAMPLE_RATE, dtype="float32", blocksize=block
        )
        self._stream.start()

    def read(self, n: int) -> Audio | None:
        data, overflowed = self._stream.read(n)
        if overflowed:
            logger.warning("ALSA input overflowed: samples were lost")
        return clean_samples(data[:, self._channel]).astype(np.float32)

    def close(self) -> None:
        """Stop and close the ALSA stream."""
        self._stream.close()
