"""Full bench of the detection with the real YAMNet model (D81 targets)."""

import pytest

from marmotte.detection.bench.manifest import BENCH_MANIFEST
from marmotte.detection.bench.manifest import load_manifest
from marmotte.detection.bench.runner import make_yamnet_pipeline
from marmotte.detection.bench.runner import run_bench


@pytest.mark.bench
class TestBenchTargets:
    def test_bench_meets_d81_targets(self) -> None:
        """No long cry is missed and backgrounds give at most one false alert per 2 h."""
        # GIVEN
        clips = load_manifest(BENCH_MANIFEST)
        # WHEN
        report = run_bench(clips, make_yamnet_pipeline)
        # THEN
        assert report.long_cries > 0, report.to_text()
        assert report.missed_long_cries == 0, report.to_text()
        assert report.false_alerts_per_2h <= 1.0, report.to_text()
        assert report.meets_targets(), report.to_text()
