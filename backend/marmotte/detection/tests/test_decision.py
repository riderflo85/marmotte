from marmotte.common.enums import SoundClass
from marmotte.detection.decision import AntiBurst
from marmotte.detection.decision import ScreamNet
from marmotte.detection.decision import SlidingWindowDecider

CRY = SoundClass.CRY
BABBLE = SoundClass.BABBLE
SCREAM = SoundClass.SCREAM
HOP_S = 0.4875


class TestSlidingWindowDecider:
    def test_needs_k_positive_slices_among_last_n(self) -> None:
        """Two cry slices among the last four decide a cry, not one."""
        # GIVEN
        decider = SlidingWindowDecider(threshold=0.3)
        # WHEN
        decisions = [decider.push({CRY: 0.9}), decider.push({CRY: 0.1}), decider.push({CRY: 0.8})]
        # THEN
        assert decisions == [None, None, CRY]

    def test_forgets_slices_older_than_n(self) -> None:
        """A positive slice older than the last four no longer counts."""
        # GIVEN
        decider = SlidingWindowDecider(threshold=0.3)
        decider.push({CRY: 0.9})
        for _ in range(4):
            decider.push({})
        # WHEN
        decision = decider.push({CRY: 0.9})
        # THEN
        assert decision is None

    def test_score_equal_to_threshold_is_positive(self) -> None:
        """A score equal to the threshold counts (YAMNet scores are coarse: 0.5 happens)."""
        # GIVEN
        decider = SlidingWindowDecider(threshold=0.5)
        decider.push({CRY: 0.5})
        # WHEN
        decision = decider.push({CRY: 0.5})
        # THEN
        assert decision == CRY

    def test_prefers_cry_on_tie(self) -> None:
        """When several baby categories qualify, the cry wins."""
        # GIVEN
        decider = SlidingWindowDecider(threshold=0.3)
        decider.push({CRY: 0.9, BABBLE: 0.9})
        # WHEN
        decision = decider.push({CRY: 0.9, BABBLE: 0.9})
        # THEN
        assert decision == CRY

    def test_scream_is_not_a_baby_class(self) -> None:
        """Screams are left to the scream net: the decider ignores them."""
        # GIVEN
        decider = SlidingWindowDecider(threshold=0.3)
        decider.push({SCREAM: 0.9})
        # WHEN
        decision = decider.push({SCREAM: 0.9})
        # THEN
        assert decision is None


class TestScreamNet:
    def test_fires_at_once_on_scream_score(self) -> None:
        """A scream recognized by the model fires at once."""
        # GIVEN
        net = ScreamNet()
        # WHEN
        fired = net.push(0.8)
        # THEN
        assert fired

    def test_ignores_scores_below_threshold(self) -> None:
        """A weak scream score does not fire."""
        # GIVEN
        net = ScreamNet()
        # WHEN
        fired = [net.push(0.4) for _ in range(10)]
        # THEN
        assert not any(fired)

    def test_fires_once_per_episode(self) -> None:
        """A long scream fires once; once the score falls back, the net is armed again."""
        # GIVEN
        net = ScreamNet()
        # WHEN
        first_episode = [net.push(0.8) for _ in range(10)]
        net.push(0.1)
        second_episode = [net.push(0.8) for _ in range(3)]
        # THEN
        assert first_episode.count(True) == 1
        assert second_episode.count(True) == 1


class TestAntiBurst:
    def test_blocks_during_pause_but_not_screams(self) -> None:
        """After an alert, others wait for the pause, except those of the scream net."""
        # GIVEN
        anti_burst = AntiBurst(pause_s=60.0)
        # WHEN
        allowed = [
            anti_burst.allow(0.0, via_scream_net=False),
            anti_burst.allow(30.0, via_scream_net=False),
            anti_burst.allow(31.0, via_scream_net=True),
            anti_burst.allow(61.0, via_scream_net=False),
        ]
        # THEN
        assert allowed == [True, False, True, True]

    def test_scream_net_alerts_have_their_own_pause(self) -> None:
        """A scream net alert passes the cry pause, but does not ring again within its own pause."""
        # GIVEN
        anti_burst = AntiBurst(pause_s=60.0)
        # WHEN
        allowed = [
            anti_burst.allow(0.0, via_scream_net=True),
            anti_burst.allow(10.0, via_scream_net=False),
            anti_burst.allow(30.0, via_scream_net=True),
            anti_burst.allow(61.0, via_scream_net=True),
        ]
        # THEN
        assert allowed == [True, True, False, True]

    def test_pause_counts_from_last_allowed_alert(self) -> None:
        """A blocked alert does not restart the pause."""
        # GIVEN
        anti_burst = AntiBurst(pause_s=60.0)
        anti_burst.allow(0.0, via_scream_net=False)
        anti_burst.allow(59.0, via_scream_net=False)
        # WHEN
        allowed = anti_burst.allow(60.0, via_scream_net=False)
        # THEN
        assert allowed
