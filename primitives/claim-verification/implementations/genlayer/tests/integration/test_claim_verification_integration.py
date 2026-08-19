"""Claim Verification integration tests.

Requires a running GenLayer Studio / compatible GenLayer test environment.
Run with the GenLayer integration runner, for example:

    gltest primitives/claim-verification/implementations/genlayer/tests/integration/ -v -s

This file is intentionally not part of the direct-mode CI job. It exercises real
GenLayer transaction execution and nondeterministic consensus behavior.
"""

import json
import urllib.request

import pytest
from gltest import get_contract_factory
from gltest.assertions import tx_execution_succeeded
from gltest_cli.config.general import get_general_config


def _install_sim_llm_mock():
    """Install a deterministic LLM mock on GLSim (sim_installMocks RPC).

    Claim Verification is judgment-bearing: its canonical decision comes from
    an LLM validator via exec_prompt. GLSim falls back to a live LLM handler
    when no mock is present; we install a persistent mock so the consensus
    decision is reproducible in CI.
    """
    endpoint = get_general_config().get_rpc_url()
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "method": "sim_installMocks",
            "params": {
                "llm_mocks": {
                    ".*": {
                        "status": "VERIFIED",
                        "reason_code": "EVIDENCE_SUPPORTS_CLAIM",
                        "analysis": "mocked validator analysis",
                    }
                },
                "strict": False,
            },
            "id": 1,
        }
    ).encode()
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


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
    _install_sim_llm_mock()
    factory = get_contract_factory("ClaimVerification")
    contract = factory.deploy()

    tx = contract.verify_claim(
        args=[
            "V-INTEGRATION-001",
            "C123",
            "sha256:integration-evidence-v1",
            CLAIM,
            EVIDENCE,
        ]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)

    raw = contract.get_verification(args=["V-INTEGRATION-001"]).call()
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
    assert contract.has_verification(args=["V-INTEGRATION-001"]).call() is True
