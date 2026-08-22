"""Partner-B direct tests — EXP-CONV-004 (claim-verification SEMANTIC lane).

Replays the canonical vectors and the adversarial surface against the
independent Partner-B build and asserts convergence on equivalence fields
{status, reason_code} with Partner A's recorded expectations.

Run:
    python -m pytest convergence/experiments/EXP-CONV-004/ -v
"""

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
LANE_B = "convergence/experiments/EXP-CONV-004/lane-b/claim_verification_b.py"
VECTORS = REPO / "primitives/claim-verification/vectors/v0.1.json"

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


def _mock(direct_vm, status, reason):
    direct_vm.clear_mocks()
    direct_vm.mock_llm(
        r".*",
        json.dumps(
            {
                "status": status,
                "reason_code": reason,
                "analysis": "lane-b independent analysis prose",
            }
        ),
    )


def _verify(contract, vid="VB-1"):
    return json.loads(
        contract.verify_claim(
            vid, "C123", "sha256:evidence-v1", CLAIM, EVIDENCE
        )
    )


@pytest.mark.parametrize(
    "vid,status,reason",
    [
        ("cv-verified-001", "VERIFIED", "EVIDENCE_SUPPORTS_CLAIM"),
        ("cv-conflicted-001", "CONFLICTED", "MATERIAL_CONFLICT"),
        ("cv-insufficient-001", "INSUFFICIENT", "MISSING_ESSENTIAL_EVIDENCE"),
        ("cv-undetermined-001", "UNDETERMINED", "EVIDENCE_AMBIGUOUS"),
    ],
)
def test_lane_b_converges_on_canonical_vectors(
    direct_vm, direct_deploy, direct_alice, vid, status, reason
):
    vectors = {v["id"]: v for v in json.loads(VECTORS.read_text())["vectors"]}
    assert vectors[vid]["expected"] == {"status": status, "reason_code": reason}

    direct_vm.sender = direct_alice
    _mock(direct_vm, status, reason)
    contract = direct_deploy(LANE_B)

    result = _verify(contract, f"VB-{vid}")

    # Equivalence fields must match the canonical expectation exactly.
    assert result["status"] == status
    assert result["reason_code"] == reason
    assert contract.has_verification(f"VB-{vid}") is True


def test_lane_b_rejects_duplicate_verification_id(
    direct_vm, direct_deploy, direct_alice
):
    direct_vm.sender = direct_alice
    _mock(direct_vm, "VERIFIED", "EVIDENCE_SUPPORTS_CLAIM")
    contract = direct_deploy(LANE_B)

    _verify(contract, "VB-dup")
    with pytest.raises(Exception):
        _verify(contract, "VB-dup")


def test_lane_b_rejects_malformed_json_before_llm(
    direct_vm, direct_deploy, direct_alice
):
    direct_vm.sender = direct_alice
    contract = direct_deploy(LANE_B)

    with pytest.raises(Exception):
        contract.verify_claim(
            "VB-bad", "C123", "digest", "not-json", EVIDENCE
        )


def test_lane_b_rejects_status_reason_mismatch(
    direct_vm, direct_deploy, direct_alice
):
    direct_vm.sender = direct_alice
    _mock(direct_vm, "VERIFIED", "MATERIAL_CONFLICT")  # inconsistent pairing
    contract = direct_deploy(LANE_B)

    with pytest.raises(Exception):
        _verify(contract, "VB-mismatch")


def test_lane_b_undetermined_is_not_approval(
    direct_vm, direct_deploy, direct_alice
):
    """Canonical invariant: UNDETERMINED is a distinct non-approving state."""
    direct_vm.sender = direct_alice
    _mock(direct_vm, "UNDETERMINED", "EVIDENCE_AMBIGUOUS")
    contract = direct_deploy(LANE_B)

    result = _verify(contract, "VB-und")
    assert result["status"] == "UNDETERMINED"
    assert result["status"] != "VERIFIED"


def test_lane_b_decision_binds_claim_and_digest(
    direct_vm, direct_deploy, direct_alice
):
    direct_vm.sender = direct_alice
    _mock(direct_vm, "VERIFIED", "EVIDENCE_SUPPORTS_CLAIM")
    contract = direct_deploy(LANE_B)

    result = _verify(contract, "VB-bind")
    assert result["verification_id"] == "VB-bind"
    assert result["claim_id"] == "C123"
    assert result["evidence_digest"] == "sha256:evidence-v1"
