"""Direct-mode tests for Policy Envelope v0.1 judgment surface.

The canonical vector runner cannot register LLM mocks, so the
interpret_clause (judgment) vectors live here as direct tests.
Deterministic hard-limit vectors are fully covered by vectors/v0.1.json.

Run:
    python -m pytest primitives/policy-envelope/implementations/genlayer/tests/ -v
"""

import json

import pytest

CONTRACT = "primitives/policy-envelope/implementations/genlayer/policy_envelope.py"

ENVELOPE_ARGS = ("ENV1", "POLICYHASH-1", "1000", "USD", "0", "9999999999")


def _mock(direct_vm, decision):
    direct_vm.clear_mocks()
    direct_vm.mock_llm(
        r"You interpret one declared mandate clause.*",
        json.dumps({"decision": decision, "analysis": "mocked interpretation"}),
    )


def _setup_envelope(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    contract.create_envelope(*ENVELOPE_ARGS)
    return contract


def test_interpreted_admit(direct_vm, direct_deploy, direct_alice):
    contract = _setup_envelope(direct_vm, direct_deploy, direct_alice)
    contract.attach_mandate_clause("ENV1", "MC1", "Only vendor invoices related to project alpha are admissible")
    _mock(direct_vm, "ADMIT")

    result = json.loads(
        contract.interpret_clause("ENV1", "MC1", '{"vendor":"alpha-construction","memo":"project alpha invoice 7"}', "R-J1")
    )
    assert result["decision"] == "ADMIT"
    assert contract.get_clause_interpretation("R-J1") != ""


def test_interpreted_undetermined_is_not_approval(direct_vm, direct_deploy, direct_alice):
    """Canonical invariant: UNDETERMINED never becomes implicit approval."""
    contract = _setup_envelope(direct_vm, direct_deploy, direct_alice)
    contract.attach_mandate_clause("ENV1", "MC1", "Only vendor invoices related to project alpha are admissible")
    _mock(direct_vm, "UNDETERMINED")

    result = json.loads(
        contract.interpret_clause("ENV1", "MC1", '{"vendor":"beta-llc","memo":"unrelated"}', "R-J2")
    )
    assert result["decision"] == "UNDETERMINED"
    assert result["decision"] != "ADMIT"


def test_invalid_decision_rejected_by_leader_guard(direct_vm, direct_deploy, direct_alice):
    """Model output outside the bounded schema must not be accepted."""
    contract = _setup_envelope(direct_vm, direct_deploy, direct_alice)
    contract.attach_mandate_clause("ENV1", "MC1", "clause")
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r".*", json.dumps({"decision": "SURE_WHY_NOT"}))

    with pytest.raises(Exception):
        contract.interpret_clause("ENV1", "MC1", "{}", "R-J3")


def test_interpretation_cannot_widen_hard_limits(direct_vm, direct_deploy, direct_alice):
    """Even after clause ADMIT, deterministic evaluate_request still vetoes."""
    contract = _setup_envelope(direct_vm, direct_deploy, direct_alice)
    contract.attach_mandate_clause("ENV1", "MC1", "Vendor invoices for project alpha are admissible")
    _mock(direct_vm, "ADMIT")
    contract.interpret_clause("ENV1", "MC1", '{"vendor":"alpha"}', "R-J1")

    # Hard limit is 1000; interpreted approval cannot raise it.
    result = json.loads(
        contract.evaluate_request("ENV1", "RH", "5000", "USD", "ALPHA-VENDOR", "T", "5000000000")
    )
    assert result["decision"] == "DENY"
    assert result["reason_code"] == "AMOUNT_EXCEEDS_LIMIT"


def test_clause_belongs_to_envelope(direct_vm, direct_deploy, direct_alice):
    contract = _setup_envelope(direct_vm, direct_deploy, direct_alice)
    direct_vm.sender = direct_alice
    contract.create_envelope("ENV2", "P2", "500", "EUR", "0", "9999999999")
    contract.attach_mandate_clause("ENV2", "MC2", "clause for env2")
    _mock(direct_vm, "ADMIT")

    with pytest.raises(Exception):
        contract.interpret_clause("ENV1", "MC2", "{}", "R-X")


def test_duplicate_interpretation_id_rejected(direct_vm, direct_deploy, direct_alice):
    contract = _setup_envelope(direct_vm, direct_deploy, direct_alice)
    contract.attach_mandate_clause("ENV1", "MC1", "clause")
    _mock(direct_vm, "ADMIT")

    contract.interpret_clause("ENV1", "MC1", "{}", "R-DUP")
    with pytest.raises(Exception):
        contract.interpret_clause("ENV1", "MC1", "{}", "R-DUP")


def test_deterministic_evaluation_ignores_clause_state(direct_vm, direct_deploy, direct_alice):
    """evaluate_request never consults interpretations — pure hard limits."""
    contract = _setup_envelope(direct_vm, direct_deploy, direct_alice)
    contract.attach_mandate_clause("ENV1", "MC1", "clause")
    _mock(direct_vm, "DENY")  # even a DENY interpretation does not block admission
    contract.interpret_clause("ENV1", "MC1", "{}", "R-N1")

    result = json.loads(
        contract.evaluate_request("ENV1", "RN", "100", "USD", "A", "T", "5000000000")
    )
    assert result["decision"] == "ADMIT"
