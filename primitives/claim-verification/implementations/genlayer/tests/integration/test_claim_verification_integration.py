"""Claim Verification integration tests.

Requires a running GenLayer Studio / compatible GenLayer test environment.
Run with the GenLayer integration runner, for example:

    gltest primitives/claim-verification/implementations/genlayer/tests/integration/ -v -s

This file is intentionally not part of the direct-mode CI job. It exercises real
GenLayer transaction execution and nondeterministic consensus behavior.
"""

import json
import pytest
from gltest import get_contract_factory
from gltest.assertions import tx_execution_succeeded


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
        "invoice": {
            "number": "INV-42",
            "amount": "100000",
            "asset": "USD",
            "obligor": "Acme Buyer",
            "beneficiary": "Supplier A",
        },
        "delivery": {
            "status": "accepted",
            "reference": "DEL-42",
        },
    },
    sort_keys=True,
)


@pytest.mark.integration
def test_verified_claim_persists_canonical_decision():
    factory = get_contract_factory("ClaimVerification")
    contract = factory.deploy()

    tx = contract.verify_claim(
        args=[
            "V-INTEGRATION-001",
            "C123",
            "sha256:integration-evidence-v1",
            CLAIM,
            EVIDENCE,
        ],
        wait_interval=10000,
        wait_retries=20,
    )
    assert tx_execution_succeeded(tx)

    raw = contract.get_verification(args=["V-INTEGRATION-001"])
    decision = json.loads(raw)

    assert decision["verification_id"] == "V-INTEGRATION-001"
    assert decision["claim_id"] == "C123"
    assert decision["evidence_digest"] == "sha256:integration-evidence-v1"
    assert decision["status"] in {
        "VERIFIED",
        "CONFLICTED",
        "INSUFFICIENT",
        "UNDETERMINED",
    }
    assert decision["reason_code"] in {
        "EVIDENCE_SUPPORTS_CLAIM",
        "MATERIAL_CONFLICT",
        "MISSING_ESSENTIAL_EVIDENCE",
        "EVIDENCE_AMBIGUOUS",
    }

    expected_reason = {
        "VERIFIED": "EVIDENCE_SUPPORTS_CLAIM",
        "CONFLICTED": "MATERIAL_CONFLICT",
        "INSUFFICIENT": "MISSING_ESSENTIAL_EVIDENCE",
        "UNDETERMINED": "EVIDENCE_AMBIGUOUS",
    }[decision["status"]]
    assert decision["reason_code"] == expected_reason
    assert contract.has_verification(args=["V-INTEGRATION-001"]) is True
