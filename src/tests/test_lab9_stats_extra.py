"""Extra M2 edge cases beyond the public vectors."""
import pytest

pytestmark = pytest.mark.student


@pytest.fixture(scope="module")
def stats():
    from lab9 import stats

    return stats


def test_kappa_undefined_for_constant_fail_judge(stats):
    with pytest.raises(ValueError):
        stats.cohen_kappa(["FAIL"] * 4, ["FAIL"] * 4)


def test_precision_recall_zero_denominator(stats):
    assert stats.precision_recall(["PASS", "PASS"], ["PASS", "PASS"]) == (0.0, 0.0)


def test_rogan_gladen_clips_high(stats):
    assert stats.rogan_gladen(1.0, 0.8, 0.9) == 1.0


def test_labels_are_normalised(stats):
    assert stats.confusion([" fail", "pass "], ["FAIL", "PASS"]) == {"tp": 1, "fp": 0, "fn": 0, "tn": 1}
