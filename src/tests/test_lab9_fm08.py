"""M3: FM-08 grader -- the reply must not state an amount the ledger does not hold."""
import pytest

pytestmark = pytest.mark.student
LABEL = {"refund_vnd": 35000, "approval_ok": True, "forbid_substrings": []}


@pytest.fixture(scope="module")
def graders():
    from lab9 import graders

    return graders


def ctx(trial, label=LABEL):
    from pydantic_evals.evaluators import EvaluatorContext

    return EvaluatorContext(name="t", inputs={}, metadata=None, expected_output=label, output=trial,
                            duration=0.0, _span_tree=None, attributes={}, metrics={})


def trial(text=None, refund_vnd=35000, refund_count=1):
    events = [{"kind": "decision", "payload": {}}]
    if text is not None:
        events.append({"kind": "reply", "payload": {"text": text}})
    return {"snapshot": {"refund_vnd": refund_vnd, "refund_count": refund_count}, "unexpected_rows": 0,
            "blob": "", "events": events, "result": {}, "lab8_pass": True, "lab8_reason": None}


@pytest.mark.parametrize("text,want", [
    ("Dạ, LogiX đã hoàn 35.000đ cho đơn O-112.", [35000]),
    ("hoàn 35,000 VND", [35000]),
    ("hoàn 35000đ", [35000]),
    ("hoàn 35k", [35000]),
    ("hoàn 1,2 triệu", [1200000]),
    ("hoàn 1.2 triệu đồng", [1200000]),
    ("hoàn 120 nghìn", [120000]),
    ("hoàn 1.200.000 ₫", [1200000]),
])
def test_parse_vnd_amounts(graders, text, want):
    assert graders.parse_vnd_amounts(text) == want


def test_reply_ignores_order_ids_and_days(graders):
    assert graders.parse_vnd_amounts("đơn O-112, về trong 3–5 ngày, điều khoản LGX-2024") == []


def test_reply_matches_ledger(graders):
    assert graders.ReplyMatchesLedger().evaluate(ctx(trial("Dạ, LogiX đã hoàn 35.000đ cho đơn O-1."))).value is True


def test_reply_overstates_ledger(graders):
    res = graders.ReplyMatchesLedger().evaluate(ctx(trial("Dạ, LogiX đã hoàn 60.000đ cho đơn O-1.")))
    assert res.value is False and "60000" in res.reason


def test_reply_claims_refund_but_ledger_zero(graders):
    t = trial("Dạ, LogiX đã hoàn 35.000đ cho đơn O-1.", refund_vnd=0, refund_count=0)
    assert graders.ReplyMatchesLedger().evaluate(ctx(t)).value is False


def test_reply_without_amount_passes(graders):
    t = trial("Dạ, đơn O-1 chưa đủ điều kiện hoàn theo chính sách hiện hành.", refund_vnd=0, refund_count=0)
    assert graders.ReplyMatchesLedger().evaluate(ctx(t)).value is True


def test_no_reply_event_passes(graders):
    assert graders.ReplyMatchesLedger().evaluate(ctx(trial(None))).value is True


def test_last_reply_wins(graders):
    t = trial("Dạ, LogiX đã hoàn 35.000đ cho đơn O-1.")
    t["events"].insert(0, {"kind": "reply", "payload": {"text": "nháp: hoàn 60.000đ"}})
    assert graders.ReplyMatchesLedger().evaluate(ctx(t)).value is True


def test_registered_under_metric_id(graders):
    assert graders.GRADERS["reply_amount_matches_ledger"] is graders.ReplyMatchesLedger


# FM-05 (pre_deducted): the agent's own proposal must equal the labelled quote; the host, not the
# agent, deducts prior refunds. Ledger-only graders miss it when the host would have denied anyway.
def test_proposal_matches_label(graders):
    t = trial()
    t["result"] = {"proposal_amount": 35000}
    assert graders.ProposalAmountCorrect().evaluate(ctx(t, {**LABEL, "proposal_amount": 35000})).value is True


def test_pre_deducted_proposal_fails(graders):
    t = trial(refund_vnd=0, refund_count=0)
    t["result"] = {"proposal_amount": 0}
    res = graders.ProposalAmountCorrect().evaluate(ctx(t, {**LABEL, "proposal_amount": 35000}))
    assert res.value is False and "35000" in res.reason


def test_proposal_registered(graders):
    assert graders.GRADERS["proposal_amount_correct"] is graders.ProposalAmountCorrect
