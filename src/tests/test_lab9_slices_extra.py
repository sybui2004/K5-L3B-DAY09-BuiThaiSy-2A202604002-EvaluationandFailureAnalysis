"""Extra M5 slice-gate cases (advanced)."""
import copy

import pytest

pytestmark = pytest.mark.student


def _report(rows, metrics=None, items=4, seeds=(1, 2)):
    return {"manifest": {"eval_set_sha": "x", "items": items, "seeds": list(seeds)},
            "rows": rows, "metrics": metrics or {"pass_rate": 1.0}, "evaluator_failures": []}


ROWS = [{"item_id": f"E-{i:03d}", "seed": s, "pass_rate": True, "slices": ["denial"] if i < 2 else []}
        for i in range(4) for s in (1, 2)]
SPEC = {"eval_set_version": "v2", "bootstrap": {"n_resamples": 200, "rng": 1},
        "metrics": [{"id": "pass_rate", "kind": "capability", "blocking": True, "threshold": {"min": 0.8}}]}


def _spec(**slice_kw):
    return dict(SPEC, slices=[{"name": "denial", "metric": "pass_rate", "blocking": True, **slice_kw}])


def test_slice_check_advanced_tests_pass_on_identical_reports():
    from lab9 import gate

    base = _report(copy.deepcopy(ROWS))
    blocked, lines = gate.slice_check(base, base, _spec(min=0.9, no_significant_drop=True))
    assert blocked == [] and lines


def test_slice_check_empty_slice_blocks_when_baseline_has_items():
    from lab9 import gate

    base = _report(copy.deepcopy(ROWS))
    rows = copy.deepcopy(ROWS)
    for r in rows:
        r["slices"] = []
    blocked, _ = gate.slice_check(_report(rows), base, _spec(min=0.9))
    assert blocked == ["slice:denial/pass_rate"]


def test_slice_check_empty_everywhere_does_not_block():
    from lab9 import gate

    rows = copy.deepcopy(ROWS)
    for r in rows:
        r["slices"] = []
    rep = _report(rows)
    blocked, lines = gate.slice_check(rep, rep, _spec(min=0.9))
    assert blocked == [] and any("no items" in ln for ln in lines)


def test_slice_check_significant_drop_blocks():
    from lab9 import gate

    base = _report(copy.deepcopy(ROWS + [{"item_id": "E-009", "seed": s, "pass_rate": True, "slices": ["denial"]}
                                         for s in (1, 2)]))
    rows = copy.deepcopy(base["rows"])
    for r in rows:
        if "denial" in r["slices"]:
            r["pass_rate"] = False
    blocked, _ = gate.slice_check(_report(rows), base, _spec(min=0.0, no_significant_drop=True))
    assert blocked == ["slice:denial/pass_rate"]


def test_slice_check_non_blocking_slice_only_warns():
    from lab9 import gate

    base = _report(copy.deepcopy(ROWS))
    rows = copy.deepcopy(ROWS)
    for r in rows:
        if "denial" in r["slices"]:
            r["pass_rate"] = False
    spec = dict(SPEC, slices=[{"name": "denial", "metric": "pass_rate", "min": 0.9, "blocking": False}])
    blocked, lines = gate.slice_check(_report(rows), base, spec)
    assert blocked == [] and any("warn" in ln for ln in lines)
