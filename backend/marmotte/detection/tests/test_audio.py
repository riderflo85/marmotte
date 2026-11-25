from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from marmotte.detection.audio import AlsaSource
from marmotte.detection.audio import ArraySource
from marmotte.detection.audio import WavFileSource
from marmotte.detection.audio import to_mono_16k
from marmotte.detection.types import HOP


def _write_stereo_48k(path: Path, seconds: float) -> Path:
    """Write a 48 kHz stereo FLAC file: 0.5 on the left channel, -0.5 on the right one."""
    n = int(48_000 * seconds)
    data = np.stack([np.full(n, 0.5), np.full(n, -0.5)], axis=1).astype(np.float32)
    sf.write(path, data, 48_000)
    return path


class TestToMono16k:
    def test_downmixes_and_resamples(self) -> None:
        """Stereo 48 kHz becomes mono 16 kHz float32, with the same level."""
        # GIVEN
        stereo_48k = np.ones((48_000, 2), dtype=np.float32) * 0.5
        # WHEN
        out = to_mono_16k(stereo_48k, 48_000)
        # THEN
        assert out.dtype == np.float32
        assert out.shape == (16_000,)
        assert np.allclose(out[100:-100], 0.5, atol=1e-3)

    def test_cleans_nan_and_clips(self) -> None:
        """NaN becomes silence and values outside [-1, 1] are clipped."""
        # GIVEN
        damaged = np.array([np.nan, 2.0, -3.0, 0.25], dtype=np.float32)
        # WHEN
        out = to_mono_16k(damaged, 16_000)
        # THEN
        assert out.tolist() == [0.0, 1.0, -1.0, 0.25]

    def test_infinities_do_not_spread_through_resampling(self) -> None:
        """An infinite value at 48 kHz leaves only finite values once resampled."""
        # GIVEN
        damaged = np.zeros(4_800, dtype=np.float32)
        damaged[2_400] = np.inf
        # WHEN
        out = to_mono_16k(damaged, 48_000)
        # THEN
        assert np.isfinite(out).all()
        assert out.shape == (1_600,)


class TestArraySource:
    def test_serves_chunks_then_ends(self) -> None:
        """The samples come back in chunks, the last one padded with zeros, then None."""
        # GIVEN
        src = ArraySource(np.arange(1, 6, dtype=np.float32))
        # WHEN
        first, second, third = src.read(3), src.read(3), src.read(3)
        # THEN
        assert first is not None
        assert first.tolist() == [1.0, 2.0, 3.0]
        assert second is not None
        assert second.tolist() == [4.0, 5.0, 0.0]
        assert third is None


class TestWavFileSource:
    def test_reads_then_ends(self, tmp_path: Path) -> None:
        """A 1 s stereo 48 kHz file gives one second of mono 16 kHz, then None."""
        # GIVEN
        src = WavFileSource(_write_stereo_48k(tmp_path / "one_second.flac", 1.0))
        # WHEN
        chunk = src.read(16_000)
        # THEN
        assert chunk is not None
        assert chunk.shape == (16_000,)
        assert np.allclose(chunk[100:-100], 0.0, atol=1e-3)  # mean of 0.5 and -0.5
        assert src.read(16_000) is None

    def test_loops(self, tmp_path: Path) -> None:
        """With loop=True, the file starts again instead of ending."""
        # GIVEN
        src = WavFileSource(_write_stereo_48k(tmp_path / "one_second.flac", 1.0), loop=True)
        # WHEN
        chunks = [src.read(16_000) for _ in range(3)]
        # THEN
        assert all(chunk is not None and chunk.shape == (16_000,) for chunk in chunks)


@pytest.mark.hardware
class TestAlsaSource:
    def test_reads_shared_micro(self) -> None:
        """The shared micro of the Pi gives one hop of mono samples."""
        # GIVEN
        src = AlsaSource()
        # WHEN
        chunk = src.read(HOP)
        # THEN
        assert chunk is not None
        assert chunk.shape == (HOP,)
