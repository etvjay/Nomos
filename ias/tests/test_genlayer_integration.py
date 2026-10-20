from datetime import datetime, timezone
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest

from integration.receipts import (
    ReceiptError,
    bind_proposal,
    validate_adjudication_receipt,
)


NOW = datetime(2026, 8, 30, tzinfo=timezone.utc)


def receipt(status="ACCEPTED", **overrides):
    value = {
        "decision_id": "DEC-1",
        "source_contract": "0xabc",
        "question_hash": "sha256:question",
        "evidence_hash": "sha256:evidence",
        "decision_status": status,
        "equivalence_mode": "comparative",
        "policy_version": "IAS-1",
        "created_at": "2026-08-29T00:00:00Z",
        "expires_at": "2026-09-01T00:00:00Z",
    }
    value.update(overrides)
    return value


def proposal(**overrides):
    value = {
        "proposal_id": "PROP-1",
        "decision_id": "DEC-1",
        "policy_version": "IAS-1",
    }
    value.update(overrides)
    return value


def test_accepted_receipt_is_actionable():
    result = validate_adjudication_receipt(receipt(), now=NOW)
    assert result["decision_status"] == "ACCEPTED"
    assert result["actionability"] == "ACTIONABLE"


@pytest.mark.parametrize("status", ["REJECTED", "UNDETERMINED"])
def test_non_accepted_receipts_are_recorded_but_not_actionable(status):
    result = validate_adjudication_receipt(receipt(status), now=NOW)
    assert result["actionability"] == "NON_ACTIONABLE"
    with pytest.raises(ReceiptError, match="only ACCEPTED"):
        bind_proposal(receipt(status), proposal(), now=NOW)


def test_expired_receipt_fails_closed():
    with pytest.raises(ReceiptError, match="expired"):
        validate_adjudication_receipt(
            receipt(expires_at="2026-08-29T12:00:00Z"), now=NOW
        )


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"evidence_hash": ""}, "missing or invalid evidence_hash"),
        ({"equivalence_mode": "free_form"}, "invalid equivalence_mode"),
        ({"policy_version": ""}, "missing or invalid policy_version"),
    ],
)
def test_receipt_required_fields_and_schema(overrides, message):
    with pytest.raises(ReceiptError, match=message):
        validate_adjudication_receipt(receipt(**overrides), now=NOW)


def test_proposal_must_bind_decision_and_policy():
    with pytest.raises(ReceiptError, match="decision_id mismatch"):
        bind_proposal(receipt(), proposal(decision_id="DEC-OTHER"), now=NOW)
    with pytest.raises(ReceiptError, match="policy_version mismatch"):
        bind_proposal(receipt(), proposal(policy_version="IAS-OTHER"), now=NOW)


def test_valid_proposal_is_created_in_proposed_state():
    result = bind_proposal(receipt(), proposal(), now=NOW)
    assert result == {
        "proposal_id": "PROP-1",
        "decision_id": "DEC-1",
        "policy_version": "IAS-1",
        "status": "PROPOSED",
    }
