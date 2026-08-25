"""Direct tests for Workflow Authorization v0.1.

Covers the principal authority gate and expiry semantics that require
sender control / timestamp precision beyond the vector runner's single-sender
model. Sender-neutral deterministic flows are additionally covered by
vectors/v0.1.json.

Run:
    python -m pytest primitives/workflow-authorization/implementations/genlayer/tests/ -v
"""

import json

import pytest
from gltest.direct.loader import create_address

CONTRACT = "primitives/workflow-authorization/implementations/genlayer/workflow_authorization.py"


def _hex(a) -> str:
    return a.hex() if isinstance(a, bytes) else str(a).lower().removeprefix("0x")


def _setup(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    contract.grant_path(
        "PATH1", _hex(direct_alice), "AGENT-B",
        "treasury-payments", "100", "USD", "0", "9999999999",
    )
    return contract


def test_principal_can_accept_own_pact(direct_vm, direct_deploy, direct_alice):
    contract = _setup(direct_vm, direct_deploy, direct_alice)
    contract.propose_pact("K1", "PATH1", "WF-1", "{}", "5")
    contract.accept_pact("K1")
    assert json.loads(contract.get_pact("K1"))["status"] == "ACCEPTED"


def test_non_principal_cannot_accept(direct_vm, direct_deploy, direct_alice):
    contract = _setup(direct_vm, direct_deploy, direct_alice)
    contract.propose_pact("K1", "PATH1", "WF-1", "{}", "5")

    mallory = create_address("mallory")
    direct_vm.sender = mallory
    with pytest.raises(Exception):
        contract.accept_pact("K1")

    # Blocked decision yields no executable Pact.
    assert json.loads(contract.get_pact("K1"))["status"] == "PROPOSED"
    # Execution on a PROPOSED pact returns DENY (fail-closed), not an exception.
    result = json.loads(contract.execute_pact("K1", "10", "5000000000"))
    assert result["decision"] == "DENY"
    assert result["reason_code"] == "PACT_NOT_ACCEPTED"
    # Principal still can accept afterwards - the failed attempt changed nothing.
    direct_vm.sender = direct_alice
    contract.accept_pact("K1")
    assert json.loads(contract.get_pact("K1"))["status"] == "ACCEPTED"


def test_proposal_after_expiry_rejected(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    contract.grant_path("P9", _hex(direct_alice), "AGENT-B", "scope", "100", "USD", "0", "50")
    with pytest.raises(Exception):
        contract.propose_pact("K9", "P9", "WF-1", "{}", "60")


def test_revoked_path_blocks_acceptance_and_execution(direct_vm, direct_deploy, direct_alice):
    contract = _setup(direct_vm, direct_deploy, direct_alice)
    contract.propose_pact("K1", "PATH1", "WF-1", "{}", "5")
    contract.revoke_path("PATH1")

    with pytest.raises(Exception):
        contract.accept_pact("K1")
    result = json.loads(contract.execute_pact("K1", "10", "5000000000"))
    assert result["decision"] == "DENY"
    assert result["reason_code"] == "PACT_NOT_ACCEPTED"


def test_full_authorized_flow_then_double_execute_rejected(
    direct_vm, direct_deploy, direct_alice
):
    contract = _setup(direct_vm, direct_deploy, direct_alice)
    contract.propose_pact("K1", "PATH1", "WF-1", "{}", "5")
    contract.accept_pact("K1")

    over = json.loads(contract.execute_pact("K1", "101", "5000000000"))
    assert over == {
        "pact_id": "K1", "decision": "DENY",
        "reason_code": "EXCEEDS_PATH_BOUND", "amount": "101",
    }
    # Denied execution does not consume the pact.
    ok = json.loads(contract.execute_pact("K1", "100", "5000000001"))
    assert ok["decision"] == "AUTHORIZE"
    assert json.loads(contract.get_pact("K1"))["status"] == "EXECUTED"

    with pytest.raises(Exception):
        contract.execute_pact("K1", "10", "5000000002")
