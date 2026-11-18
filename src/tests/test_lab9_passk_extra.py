"""Extra M6 edge cases for pass@k / pass^k."""
import pytest

pytestmark = pytest.mark.student


@pytest.fixture(scope="module")
def stats():
    from lab9 import stats

    return stats


@pytest.mark.parametrize("args", [(5, -1, 1), (0, 0, 1), (5, 2, -1), (5, 6, 1), (3, 1, 4), (5, 2, 0)])
def test_pass_k_rejects_more_bad_args(stats, args):
    for fn in (stats.pass_at_k, stats.pass_hat_k):
        with pytest.raises(ValueError):
            fn(*args)


def test_pass_hat_le_pass_at(stats):
    assert stats.pass_hat_k(10, 6, 3) <= 0.6 <= stats.pass_at_k(10, 6, 3)


def test_pass_at_k_certain_when_too_few_failures(stats):
    assert stats.pass_at_k(5, 3, 3) == 1.0
