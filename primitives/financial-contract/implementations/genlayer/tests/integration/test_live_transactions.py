"""Live end-to-end transaction test: deploy Nomos primitives on GLSim localnet
and execute REAL transactions through full Optimistic Democracy consensus.

Run with glsim active on :4000:
    source ~/nomos-venv312/bin/activate
    python -m pytest primitives/claim-verification/implementations/genlayer/tests/integration/test_claim_verification_integration.py primitives/proof-of-payable/implementations/genlayer/tests/integration/ -v
"""

import json

import pytest
from gltest import get_contract_factory
from gltest.assertions import tx_execution_succeeded


FC = "primitives/financial-contract/implementations/genlayer/financial_contract.py"
POP = "primitives/proof-of-payable/implementations/genlayer/proof_of_payable.py"
DAL = "primitives/dal/implementations/genlayer/dal.py"
DAA = "primitives/daa/implementations/genlayer/daa.py"
GAIA = "primitives/gaia/implementations/genlayer/gaia.py"


@pytest.mark.integration
def test_financial_contract_live_payment_cycle(get_contract_factory):
    """Open -> pay -> overpay-denied -> close -> terminal. Real txs, real state."""
    factory = get_contract_factory("FinancialContract", FC)
    contract = factory.deploy()

    tx = contract.open_contract(
        "FC-LIVE-1", "CREDITOR-X", "OBLIGOR-Y", "1000", "USD", "0", "9999999999", "PACT-LIVE-1"
    )
    assert tx_execution_succeeded(tx)

    # Payment 1 through consensus
    tx = contract.apply_payment("FC-LIVE-1", "PAY-1", "400", "5000000000")
    assert tx_execution_succeeded(tx)
    state = json.loads(contract.get_contract("FC-LIVE-1"))
    assert state["outstanding"] == "600"
    assert state["total_paid"] == "400"

    # Overpayment denied by consensus execution
    tx = contract.apply_payment("FC-LIVE-1", "PAY-BAD", "99999", "5000000001")
    assert tx_execution_succeeded(tx)  # tx succeeds; the CALL returns DENY decision
    state = json.loads(contract.get_contract("FC-LIVE-1"))
    assert state["outstanding"] == "600"  # unchanged — denial mutated nothing

    # Pay off fully -> CLOSED
    tx = contract.apply_payment("FC-LIVE-1", "PAY-2", "600", "5000000002")
    assert tx_execution_succeeded(tx)
    state = json.loads(contract.get_contract("FC-LIVE-1"))
    assert state["status"] == "CLOSED"
    assert state["outstanding"] == "0"


@pytest.mark.integration
def test_proof_of_payable_live_evidence_lifecycle(get_contract_factory):
    factory = get_contract_factory("ProofOfPayable", POP)
    contract = factory.deploy()

    tx = contract.open_claim("CL-LIVE-1", "5000", "INV-LIVE-9", "ACME")
    assert tx_execution_succeeded(tx)

    tx = contract.attach_evidence("CL-LIVE-1", "PRF-1", "sha256:live-evidence-1", '{"kind":"invoice"}')
    assert tx_execution_succeeded(tx)

    claim = json.loads(contract.get_claim("CL-LIVE-1"))
    assert claim["status"] == "EVIDENCED"
    assert claim["evidence_count"] == "1"

    tx = contract.attest_claim("CL-LIVE-1")
    assert tx_execution_succeeded(tx)
    claim = json.loads(contract.get_claim("CL-LIVE-1"))
    assert claim["status"] == "ATTESTED"

    tx = contract.settle_claim("CL-LIVE-1")
    assert tx_execution_succeeded(tx)
    claim = json.loads(contract.get_claim("CL-LIVE-1"))
    assert claim["status"] == "SETTLED"


@pytest.mark.integration
def test_dal_live_replay_protection(get_contract_factory):
    factory = get_contract_factory("Dal", DAL)
    contract = factory.deploy()

    tx = contract.open_lane("ISSUER-LIVE", "DOMAIN-LIVE", "9999999999")
    assert tx_execution_succeeded(tx)

    # first exercise authorized, nonce advances on-chain
    tx = contract.exercise("ISSUER-LIVE", "DOMAIN-LIVE", "1", "5000000000")
    assert tx_execution_succeeded(tx)
    lane = json.loads(contract.get_lane("ISSUER-LIVE", "DOMAIN-LIVE"))
    assert lane["nonce"] == "2"

    # replay of nonce 1 denied on-chain
    tx = contract.exercise("ISSUER-LIVE", "DOMAIN-LIVE", "1", "5000000001")
    assert tx_execution_succeeded(tx)
    lane = json.loads(contract.get_lane("ISSUER-LIVE", "DOMAIN-LIVE"))
    assert lane["nonce"] == "2"  # replay advanced nothing


@pytest.mark.integration
def test_gaia_live_case_resolution_gate(get_contract_factory):
    factory = get_contract_factory("Gaia", GAIA)
    contract = factory.deploy()

    tx = contract.open_case("CASE-LIVE", "settlement-mismatch", "SETTLE-LIVE", "{}")
    assert tx_execution_succeeded(tx)

    tx = contract.classify_case(
        "CASE-LIVE", "CLS-1",
        '[{"type":"reconcile"},{"type":"manual_review"}]',
    )
    assert tx_execution_succeeded(tx)

    # premature resolution rejected on-chain
    tx = contract.resolve_case("CASE-LIVE", "sha256:premature")
    assert tx_execution_succeeded(tx)  # call raises inside -> check status unchanged
    case = json.loads(contract.get_case("CASE-LIVE"))
    assert case["status"] in ("CLASSIFIED", "OPEN")

    # discharge both obligations
    tx = contract.discharge_obligation("CLS-1-O0", "sha256:evd-1")
    assert tx_execution_succeeded(tx)
    tx = contract.waive_obligation("CLS-1-O1", "runbook 7.2")
    assert tx_execution_succeeded(tx)

    tx = contract.resolve_case("CASE-LIVE", "sha256:resolved")
    assert tx_execution_succeeded(tx)
    case = json.loads(contract.get_case("CASE-LIVE"))
    assert case["status"] == "RESOLVED"
