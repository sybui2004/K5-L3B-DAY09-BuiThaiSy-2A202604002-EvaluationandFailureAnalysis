"""M7 integrity / ratchet cases beyond the public vectors. Each test breaks exactly one property."""
import copy
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.student

ROWS = [{"item_id": f"E-{i:03d}", "seed": s, "pass_rate": True, "slices": ["denial"] if i < 2 else []}
        for i in range(4) for s in (1, 2)]
SPEC = {"eval_set_version": "v2", "metric_spec_version": "2.0",
        "metrics": [{"id": "pass_rate", "kind": "capability", "blocking": True,
                     "threshold": {"min": 0.8, "no_significant_drop": True}}],
        "slices": [{"name": "denial", "metric": "pass_rate", "min": 0.9, "no_significant_drop": True, "blocking": True}]}


def _report(rows=None, metrics=None, seeds=(1, 2), items=4, failures=()):
    rows = copy.deepcopy(ROWS if rows is None else rows)
    return {"manifest": {"eval_set_sha": "x", "items": items, "seeds": list(seeds), "metric_spec_version": "2.0"},
            "rows": rows, "metrics": metrics or {"pass_rate": 1.0}, "evaluator_failures": list(failures)}


@pytest.fixture(scope="module")
def gate():
    from lab9 import gate

    return gate


BASE = _report()


def test_clean_report_has_no_problems(gate):
    assert gate.integrity_check(_report(), BASE, SPEC, SPEC) == []


def test_integrity_flags_inf_metric(gate):
    assert gate.integrity_check(_report(metrics={"pass_rate": float("inf")}), BASE, SPEC)


def test_integrity_flags_duplicate_rows(gate):
    rows = copy.deepcopy(ROWS)
    rows[-1] = copy.deepcopy(rows[0])          # same count, one (item, seed) twice, one missing
    assert gate.integrity_check(_report(rows), BASE, SPEC)


def test_integrity_flags_duplicate_rows_even_when_count_and_set_look_fine(gate):
    rows = copy.deepcopy(ROWS) + [copy.deepcopy(ROWS[0])]
    assert any("duplicate" in p for p in gate.integrity_check(_report(rows, items=4), BASE, SPEC))


def test_integrity_flags_cherry_picked_seeds(gate):
    rows = [r for r in ROWS if r["seed"] == 1]
    assert gate.integrity_check(_report(rows, seeds=(1,)), BASE, SPEC)


def test_integrity_flags_evaluator_failures_on_green_run(gate):
    assert gate.integrity_check(_report(failures=["E-000@1:ApprovalBypass:boom"]), BASE, SPEC)


def test_integrity_flags_none_in_graded_row(gate):
    rows = copy.deepcopy(ROWS)
    rows[3]["pass_rate"] = None
    assert gate.integrity_check(_report(rows), BASE, SPEC)


def test_integrity_flags_missing_graded_key(gate):
    rows = copy.deepcopy(ROWS)
    del rows[3]["pass_rate"]
    assert gate.integrity_check(_report(rows), BASE, SPEC)


def test_integrity_flags_metrics_not_matching_rows(gate):
    rows = copy.deepcopy(ROWS)
    rows[0]["pass_rate"] = False
    assert any("recomputed" in p for p in gate.integrity_check(_report(rows, {"pass_rate": 1.0}), BASE, SPEC))


def test_integrity_flags_blocking_removed(gate):
    loose = copy.deepcopy(SPEC)
    loose["metrics"][0]["blocking"] = False
    assert gate.integrity_check(_report(), BASE, loose, SPEC)


def test_integrity_flags_metric_removed_from_spec(gate):
    loose = copy.deepcopy(SPEC)
    loose["metrics"] = []
    assert gate.integrity_check(_report(), BASE, loose, SPEC)


def test_integrity_flags_dropped_no_significant_drop(gate):
    loose = copy.deepcopy(SPEC)
    del loose["metrics"][0]["threshold"]["no_significant_drop"]
    assert gate.integrity_check(_report(), BASE, loose, SPEC)


def test_integrity_flags_max_raised(gate):
    base_spec = copy.deepcopy(SPEC)
    base_spec["metrics"].append({"id": "approval_bypass", "kind": "safety", "blocking": True, "threshold": {"max": 0}})
    loose = copy.deepcopy(base_spec)
    loose["metrics"][1]["threshold"]["max"] = 1
    assert gate.integrity_check(_report(), BASE, loose, base_spec)


@pytest.mark.parametrize("mutate", [
    lambda sp: sp.update(slices=[]),
    lambda sp: sp["slices"][0].update(min=0.5),
    lambda sp: sp["slices"][0].pop("no_significant_drop"),
    lambda sp: sp["slices"][0].update(blocking=False),
])
def test_integrity_flags_slice_removed_or_loosened(gate, mutate):
    loose = copy.deepcopy(SPEC)
    mutate(loose)
    assert gate.integrity_check(_report(), BASE, loose, SPEC)


def test_stricter_spec_is_allowed(gate):
    strict = copy.deepcopy(SPEC)
    strict["metrics"][0]["threshold"]["min"] = 0.9
    strict["slices"][0]["min"] = 0.95
    assert gate.integrity_check(_report(), BASE, strict, SPEC) == []


def test_integrity_flags_slice_tag_relabel(gate):
    rows = copy.deepcopy(ROWS)
    for r in rows:
        if r["item_id"] == "E-000":
            r["slices"] = []
    assert gate.integrity_check(_report(rows), BASE, SPEC)


def test_integrity_flags_spec_version_mismatch(gate):
    rep = _report()
    rep["manifest"]["metric_spec_version"] = "1.0"
    assert gate.integrity_check(rep, BASE, SPEC)


def test_ratchet_skipped_across_eval_set_versions(gate):
    v1 = copy.deepcopy(SPEC)
    v1["eval_set_version"] = "v1"
    v1["metrics"][0]["threshold"]["min"] = 0.95
    assert gate.integrity_check(_report(), BASE, SPEC, v1) == []


def test_integrity_clean_on_real_baseline_shape(gate):
    from lab9.eval import load_spec

    path = Path("reports/baseline_v2.json")
    if not path.is_file():
        pytest.skip("baseline_v2 not generated")
    base = json.loads(path.read_text(encoding="utf-8"))
    spec = load_spec(Path("config/metric_spec_v2.yaml"))
    assert gate.integrity_check(base, base, spec, spec) == []
