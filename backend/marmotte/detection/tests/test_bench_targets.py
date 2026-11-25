"""Full bench of the detection with the real YAMNet model: the CI gate (P67)."""

import pytest

from marmotte.detection.bench.manifest import BENCH_MANIFEST
from marmotte.detection.bench.manifest import load_manifest
from marmotte.detection.bench.runner import MAX_FALSE_ALERTS_PER_2H
from marmotte.detection.bench.runner import make_yamnet_pipeline
from marmotte.detection.bench.runner import run_bench


@pytest.mark.bench
class TestBenchTargets:
    def test_bench_passes_the_ci_gate(self) -> None:
        """No long cry is missed, and backgrounds give no more false alerts than when the lot was tuned."""
        # GIVEN
        clips = load_manifest(BENCH_MANIFEST)
        # WHEN
        report = run_bench(clips, make_yamnet_pipeline)
        # THEN
        assert report.long_cries > 0, report.to_text()
        assert report.missed_long_cries == 0, report.to_text()
        assert report.false_alerts_per_2h <= MAX_FALSE_ALERTS_PER_2H, report.to_text()
        assert report.passes_ci_gate(), report.to_text()
