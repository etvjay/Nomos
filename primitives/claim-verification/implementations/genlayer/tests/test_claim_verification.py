"""Direct-mode tests for Nomos Claim Verification v0.1.

Expected runner: genlayer-test direct fixtures (`direct_vm`, `direct_deploy`,
`direct_alice`) as used by the official GenLayer project boilerplate.
"""

import json
import pytest


CONTRACT = "primitives/claim-verification/implementations/genlayer/claim_verification.py"

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


def _mock_result(direct_vm, status: str, reason: str):
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


@pytest.mark.parametrize(
    "status,reason",
    [
        ("VERIFIED", "EVIDENCE_SUPPORTS_CLAIM"),
        ("CONFLICTED", "MATERIAL_CONFLICT"),
        ("INSUFFICIENT", "MISSING_ESSENTIAL_EVIDENCE"),
        ("UNDETERMINED", "EVIDENCE_AMBIGUOUS"),
    ],
)
def test_canonical_outcomes(direct_vm, direct_deploy, direct_alice, status, reason):
    direct_vm.sender = direct_alice
    _mock_result(direct_vm, status, reason)
    contract = direct_deploy(CONTRACT)

    result = _verify(contract)

    assert result["verification_id"] == "V1"
    assert result["claim_id"] == "C123"
    assert result["evidence_digest"] == "sha256:evidence-v1"
    assert result["status"] == status
    assert result["reason_code"] == reason
    assert contract.has_verification("V1") is True
    assert json.loads(contract.get_verification("V1"))["status"] == status


def test_verification_id_is_immutable(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    _mock_result(direct_vm, "VERIFIED", "EVIDENCE_SUPPORTS_CLAIM")
    contract = direct_deploy(CONTRACT)
    _verify(contract, "V1")

    with direct_vm.expect_revert("ClaimVerification: verification_id already exists"):
        _verify(contract, "V1")


def test_malformed_claim_rejected_before_llm(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)

    with direct_vm.expect_revert("ClaimVerification: malformed JSON"):
        contract.verify_claim(
            "V-bad",
            "C123",
            "sha256:evidence-v1",
            "not-json",
            EVIDENCE,
        )


def test_empty_identity_fields_rejected(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)

    with direct_vm.expect_revert("ClaimVerification: verification_id required"):
        contract.verify_claim("", "C123", "digest", CLAIM, EVIDENCE)

    with direct_vm.expect_revert("ClaimVerification: claim_id required"):
        contract.verify_claim("V1", "", "digest", CLAIM, EVIDENCE)

    with direct_vm.expect_revert("ClaimVerification: evidence_digest required"):
        contract.verify_claim("V1", "C123", "", CLAIM, EVIDENCE)


def test_inconsistent_status_reason_is_not_accepted(
    direct_vm, direct_deploy, direct_alice
):
    direct_vm.sender = direct_alice
    _mock_result(direct_vm, "VERIFIED", "MATERIAL_CONFLICT")
    contract = direct_deploy(CONTRACT)

    with pytest.raises(Exception):
        _verify(contract)


def test_invalid_evaluator_status_is_not_accepted(
    direct_vm, direct_deploy, direct_alice
):
    direct_vm.sender = direct_alice
    _mock_result(direct_vm, "APPROVED", "EVIDENCE_SUPPORTS_CLAIM")
    contract = direct_deploy(CONTRACT)

    with pytest.raises(Exception):
        _verify(contract)


def test_validator_accepts_same_bounded_financial_decision_despite_analysis_change(
    direct_vm, direct_deploy, direct_alice
):
    """Prose is non-canonical: validators may phrase analysis differently."""
    direct_vm.sender = direct_alice
    _mock_result(direct_vm, "VERIFIED", "EVIDENCE_SUPPORTS_CLAIM")
    contract = direct_deploy(CONTRACT)
    _verify(contract, "V-equivalent")

    direct_vm.clear_mocks()
    direct_vm.mock_llm(
        r".*",
        json.dumps(
            {
                "status": "VERIFIED",
                "reason_code": "EVIDENCE_SUPPORTS_CLAIM",
                "analysis": "different prose from another validator",
            }
        ),
    )

    assert direct_vm.run_validator() is True


def test_validator_rejects_material_decision_disagreement(
    direct_vm, direct_deploy, direct_alice
):
    """A leader VERIFIED result cannot be accepted by a CONFLICTED validator."""
    direct_vm.sender = direct_alice
    _mock_result(direct_vm, "VERIFIED", "EVIDENCE_SUPPORTS_CLAIM")
    contract = direct_deploy(CONTRACT)
    _verify(contract, "V-disagreement")

    # The validator independently sees/evaluates the same evidence differently.
    _mock_result(direct_vm, "CONFLICTED", "MATERIAL_CONFLICT")

    assert direct_vm.run_validator() is False


def test_validator_rejects_leader_error(
    direct_vm, direct_deploy, direct_alice
):
    """Leader failure is never treated as an affirmative verification."""
    direct_vm.sender = direct_alice
    _mock_result(direct_vm, "VERIFIED", "EVIDENCE_SUPPORTS_CLAIM")
    contract = direct_deploy(CONTRACT)
    _verify(contract, "V-leader-error")

    assert direct_vm.run_validator(leader_error=Exception("leader failed")) is False


def test_payload_size_limits_are_deterministic(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)

    oversized_claim = json.dumps({"payload": "x" * 16_384})
    with direct_vm.expect_revert("ClaimVerification: claim payload too large"):
        contract.verify_claim(
            "V-big-claim", "C123", "digest", oversized_claim, EVIDENCE
        )

    oversized_evidence = json.dumps({"payload": "x" * 32_768})
    with direct_vm.expect_revert("ClaimVerification: evidence payload too large"):
        contract.verify_claim(
            "V-big-evidence", "C123", "digest", CLAIM, oversized_evidence
        )
