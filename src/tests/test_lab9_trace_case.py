"""Regression test from docs/trace_case.md: seeded_regression C-002@11 (FM-03 ticket_trust).

First wrong step is event #3 `model_override {"delay_days": 5}`: the ticket's delay replaced the DB fact.
The same claim@seed on `fixed` must stay clean."""
import pytest

pytestmark = pytest.mark.student


def _grade(shape):
    from pydantic_evals.evaluators import EvaluatorContext

    from lab9.graders import DbFactKept, RefundAmountCorrect
    from lab9.trace_case import investigate

    case = investigate(shape, "C-002", 11)
    ctx = EvaluatorContext(name="t", inputs={}, metadata=None, expected_output=case["label"], output=case["trial"],
                           duration=0.0, _span_tree=None, attributes={}, metrics={})
    return case["trial"], DbFactKept().evaluate(ctx).value, RefundAmountCorrect().evaluate(ctx).value


def test_c002_seed11_caught_on_seeded_regression():
    trial, db_fact_kept, amount_ok = _grade("seeded_regression")
    kinds = [e.get("kind") for e in trial["events"]]
    assert kinds.index("model_override") < kinds.index("quote")   # override happens before the money is computed
    assert db_fact_kept is False
    assert amount_ok is False


def test_c002_seed11_clean_on_fixed():
    trial, db_fact_kept, amount_ok = _grade("fixed")
    assert "model_override" not in [e.get("kind") for e in trial["events"]]
    assert db_fact_kept is True
    assert amount_ok is True
