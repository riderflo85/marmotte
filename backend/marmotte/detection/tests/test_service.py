import io
import json
import subprocess
import sys
from datetime import UTC
from datetime import datetime
from pathlib import Path
from uuid import UUID

import numpy as np
import pytest
import soundfile as sf

from marmotte.common.enums import Mode
from marmotte.common.enums import SoundClass
from marmotte.detection.audio import ArraySource
from marmotte.detection.pipeline import DetectionConfig
from marmotte.detection.pipeline import DetectionPipeline
from marmotte.detection.service import run
from marmotte.detection.sinks import JsonLinesSink
from marmotte.detection.tests.fakes import loud_is_cry
from marmotte.detection.tests.test_pipeline import noise
from marmotte.detection.types import AlertEvent

FIXTURES = Path(__file__).parent / "fixtures"
START = datetime(2026, 1, 1, tzinfo=UTC)


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run `python -m marmotte.detection` with the given arguments."""
    return subprocess.run(
        [sys.executable, "-m", "marmotte.detection", *args], capture_output=True, text=True, check=False, timeout=120
    )


class TestJsonLinesSink:
    def test_writes_one_json_object_per_line(self) -> None:
        """An alert becomes one line of JSON, with plain types."""
        # GIVEN
        stream = io.StringIO()
        event = AlertEvent(UUID(int=1), SoundClass.CRY, datetime(2026, 1, 1, 0, 0, 21, tzinfo=UTC), 21.0, False)
        # WHEN
        JsonLinesSink(stream).emit(event)
        # THEN
        assert json.loads(stream.getvalue()) == {
            "id": "00000000-0000-0000-0000-000000000001",
            "kind": "cry",
            "at": "2026-01-01T00:00:21+00:00",
            "offset_s": 21.0,
            "via_scream_net": False,
        }
        assert stream.getvalue().endswith("\n")


class TestRun:
    def test_prints_alerts_as_json_lines(self, capsys: pytest.CaptureFixture[str]) -> None:
        """run() reads the source to its end and sends each alert to the sink."""
        # GIVEN
        cry_signal = np.concatenate([noise(20, -55), noise(15, -35, seed=1)])
        p = DetectionPipeline(loud_is_cry(-45), DetectionConfig(), lambda: Mode.SIESTE, START)
        # WHEN
        run(ArraySource(cry_signal), p, JsonLinesSink(sys.stdout))
        # THEN
        lines = capsys.readouterr().out.splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["kind"] == "cry"


class TestCommandLine:
    def test_needs_a_source(self) -> None:
        """Without --wav or --alsa, the command stops with a usage error."""
        # WHEN
        result = _cli()
        # THEN
        assert result.returncode == 2
        assert "--wav" in result.stderr

    @pytest.mark.model
    def test_alerts_from_a_file(self, tmp_path: Path) -> None:
        """The deliverable of lot 2: alerts from a sound file, with the real model."""
        # GIVEN
        cry, rate = sf.read(FIXTURES / "cry_cc0.flac", dtype="float32")
        sf.write(tmp_path / "nap.flac", np.concatenate([noise(10, -60), cry, cry, cry, noise(3, -60)]), rate)
        # WHEN
        result = _cli("--wav", str(tmp_path / "nap.flac"))
        # THEN
        assert result.returncode == 0, result.stderr
        alerts = [json.loads(line) for line in result.stdout.splitlines()]
        assert alerts
        assert alerts[0]["kind"] == "cry"
        assert 10.0 <= alerts[0]["offset_s"] <= 18.0
