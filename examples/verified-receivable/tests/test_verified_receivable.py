"""Direct-mode tests for the verified-receivable composition (EXP-CONV-002, lane D).

Proves the composition gate: capital is reserved against a claim only AFTER a
VERIFIED Claim Verification decision exists for that claim. Non-VERIFIED and
missing decisions are rejected before the encumbrance primitive is touched.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "implementations" / "genlayer"),
)

from verified_receivable import VerifiedReceivable

CONTRACT_CV = (
    "primitives/claim-verification/implementations/genlayer/claim_verification.py"
)
CONTRACT_CE = (
    "primitives/claim-encumbrance/implementations/genlayer/claim_encumbrance.py"
)

CLAIM = json.dumps(
    {
        "claim_id": "C123",
        "kind": "invoice",
        "amount": "100000",
        "asset": "USD",
        "obligor": "Acme Buyer",
        "beneficiary": "Supplier A",
    },
    sort_keys=True,
)

EVIDENCE = json.dumps(
    {
        "invoice": {"number": "INV-42", "amount": "100000"},
        "delivery": {"status": "accepted"},
    },
    sort_keys=True,
)


def _mock_result(direct_vm, status, reason):
    direct_vm.clear_mocks()
    direct_vm.mock_llm(
        r".*",
        json.dumps(
            {
                "status": status,
                "reason_code": reason,
                "analysis": "mocked validator analysis",
            }
        ),
    )


def _verify(contract, verification_id="V1"):
    return json.loads(
        contract.verify_claim(
            verification_id,
            "C123",
            "sha256:evidence-v1",
            CLAIM,
            EVIDENCE,
        )
    )


def _reset_single_contract_guard():
    """GenLayer SDK allows only one gl.Contract subclass per process; the
    direct-mode harness loads each primitive in the same process, so reset the
    module-level guard before deploying the second primitive."""
    import genlayer.gl.genvm_contracts as gc

    gc.__known_contract__ = None


def _compose(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    verification = direct_deploy(CONTRACT_CV)
    _reset_single_contract_guard()
    encumbrance = direct_deploy(CONTRACT_CE)
    return verification, encumbrance, VerifiedReceivable(verification, encumbrance)


def test_verified_decision_reserves_and_updates_balance(
    direct_vm, direct_deploy, direct_alice
):
    verification, encumbrance, app = _compose(
        direct_vm, direct_deploy, direct_alice
    )

    _mock_result(direct_vm, "VERIFIED", "EVIDENCE_SUPPORTS_CLAIM")
    decision = _verify(verification)
    assert decision["status"] == "VERIFIED"

    app.prepare_claim("C123", "1000")
    record = app.reserve_against_verified_claim("V1", "C123", "R1", "400")

    assert record == {
        "reservation_id": "R1",
        "claim_id": "C123",
        "amount": "400",
        "status": "RESERVED",
    }
    assert app.financeable_balance("C123") == {
        "financeable_amount": "1000",
        "active_encumbrances": "400",
    }
    assert encumbrance.active_encumbrances("C123") == "400"


@pytest.mark.parametrize(
    "status,reason",
    [
        ("CONFLICTED", "MATERIAL_CONFLICT"),
        ("INSUFFICIENT", "MISSING_ESSENTIAL_EVIDENCE"),
        ("UNDETERMINED", "EVIDENCE_AMBIGUOUS"),
    ],
)
def test_non_verified_decision_rejects_reserve(
    direct_vm, direct_deploy, direct_alice, status, reason
):
    verification, encumbrance, app = _compose(
        direct_vm, direct_deploy, direct_alice
    )

    _mock_result(direct_vm, status, reason)
    decision = _verify(verification)
    assert decision["status"] == status

    app.prepare_claim("C123", "1000")

    with direct_vm.expect_revert("VerifiedReceivable: decision not VERIFIED"):
        app.reserve_against_verified_claim("V1", "C123", "R1", "400")

    assert encumbrance.get_encumbrance("R1") == ""
    assert encumbrance.active_encumbrances("C123") == "0"


def test_missing_verification_rejects_reserve(
    direct_vm, direct_deploy, direct_alice
):
    verification, encumbrance, app = _compose(
        direct_vm, direct_deploy, direct_alice
    )

    assert verification.has_verification("V-missing") is False

    app.prepare_claim("C123", "1000")

    with direct_vm.expect_revert("VerifiedReceivable: no verification decision"):
        app.reserve_against_verified_claim("V-missing", "C123", "R1", "400")

    assert encumbrance.get_encumbrance("R1") == ""
    assert encumbrance.active_encumbrances("C123") == "0"


def test_verified_decision_for_other_claim_rejects_reserve(
    direct_vm, direct_deploy, direct_alice
):
    verification, encumbrance, app = _compose(
        direct_vm, direct_deploy, direct_alice
    )

    _mock_result(direct_vm, "VERIFIED", "EVIDENCE_SUPPORTS_CLAIM")
    _verify(verification, "V1")

    app.prepare_claim("C456", "1000")

    with direct_vm.expect_revert("does not match target claim_id"):
        app.reserve_against_verified_claim("V1", "C456", "R1", "400")

    assert encumbrance.get_encumbrance("R1") == ""
    assert encumbrance.active_encumbrances("C456") == "0"