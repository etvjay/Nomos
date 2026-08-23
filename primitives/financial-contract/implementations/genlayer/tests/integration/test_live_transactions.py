"""Live end-to-end transaction tests on GLSim localnet.

Deploys Nomos primitives and executes REAL transactions through full
GenLayer consensus. Requires glsim on :4000.

Run:
    source ~/nomos-venv312/bin/activate
    gltest primitives/financial-contract/implementations/genlayer/tests/integration/test_live_transactions.py -v
"""

import json

from gltest import get_contract_factory
from gltest.assertions import tx_execution_succeeded


def test_financial_contract_live_payment_cycle():
    """Open -> pay -> overpay-denied -> close -> terminal. Real txs, real state."""
    factory = get_contract_factory(contract_file_path="financial_contract.py")
    contract = factory.deploy()

    tx = contract.open_contract(
        args=["FC-LIVE-1", "CREDITOR-X", "OBLIGOR-Y", "1000", "USD", "0", "9999999999", "PACT-LIVE-1"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)

    tx = contract.apply_payment(
        args=["FC-LIVE-1", "PAY-1", "400", "5000000000"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)
    state = json.loads(contract.get_contract(args=["FC-LIVE-1"]).call())
    assert state["outstanding"] == "600"
    assert state["total_paid"] == "400"

    # Overpayment: tx succeeds, call returns DENY decision; nothing mutated.
    tx = contract.apply_payment(
        args=["FC-LIVE-1", "PAY-BAD", "99999", "5000000001"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)
    state = json.loads(contract.get_contract(args=["FC-LIVE-1"]).call())
    assert state["outstanding"] == "600"

    # Pay off fully -> CLOSED
    tx = contract.apply_payment(
        args=["FC-LIVE-1", "PAY-2", "600", "5000000002"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)
    state = json.loads(contract.get_contract(args=["FC-LIVE-1"]).call())
    assert state["status"] == "CLOSED"
    assert state["outstanding"] == "0"


def test_proof_of_payable_live_evidence_lifecycle():
    factory = get_contract_factory(contract_file_path="proof_of_payable.py")
    contract = factory.deploy()

    tx = contract.open_claim(
        args=["CL-LIVE-1", "5000", "INV-LIVE-9", "ACME"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)

    tx = contract.attach_evidence(
        args=["CL-LIVE-1", "PRF-1", "sha256:live-evidence-1", '{"kind":"invoice"}']
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)

    claim = json.loads(contract.get_claim(args=["CL-LIVE-1"]).call())
    assert claim["status"] == "EVIDENCED"
    assert claim["evidence_count"] == "1"

    tx = contract.attest_claim(args=["CL-LIVE-1"]).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)
    claim = json.loads(contract.get_claim(args=["CL-LIVE-1"]).call())
    assert claim["status"] == "ATTESTED"

    tx = contract.settle_claim(args=["CL-LIVE-1"]).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)
    claim = json.loads(contract.get_claim(args=["CL-LIVE-1"]).call())
    assert claim["status"] == "SETTLED"


def test_dal_live_replay_protection():
    factory = get_contract_factory(contract_file_path="dal.py")
    contract = factory.deploy()

    tx = contract.open_lane(
        args=["ISSUER-LIVE", "DOMAIN-LIVE", "9999999999"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)

    tx = contract.exercise(
        args=["ISSUER-LIVE", "DOMAIN-LIVE", "1", "5000000000"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)
    lane = json.loads(contract.get_lane(args=["ISSUER-LIVE", "DOMAIN-LIVE"]).call())
    assert lane["nonce"] == "2"

    # Replay of nonce 1 denied on-chain; nonce unchanged.
    tx = contract.exercise(
        args=["ISSUER-LIVE", "DOMAIN-LIVE", "1", "5000000001"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)
    lane = json.loads(contract.get_lane(args=["ISSUER-LIVE", "DOMAIN-LIVE"]).call())
    assert lane["nonce"] == "2"


def test_gaia_live_case_resolution_gate():
    factory = get_contract_factory(contract_file_path="gaia.py")
    contract = factory.deploy()

    tx = contract.open_case(
        args=["CASE-LIVE", "settlement-mismatch", "SETTLE-LIVE", "{}"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)

    tx = contract.classify_case(
        args=["CASE-LIVE", "CLS-1", '[{"type":"reconcile"},{"type":"manual_review"}]']
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)

    case = json.loads(contract.get_case(args=["CASE-LIVE"]).call())
    assert case["status"] == "CLASSIFIED"

    tx = contract.discharge_obligation(
        args=["CLS-1-O0", "sha256:evd-1"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)

    tx = contract.waive_obligation(
        args=["CLS-1-O1", "runbook 7.2"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)

    tx = contract.resolve_case(
        args=["CASE-LIVE", "sha256:resolved"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)
    case = json.loads(contract.get_case(args=["CASE-LIVE"]).call())
    assert case["status"] == "RESOLVED"


def test_daa_live_authority_allocation():
    factory = get_contract_factory(contract_file_path="daa.py")
    contract = factory.deploy()

    tx = contract.request_allocation(
        args=["REQ-LIVE", "POOL-LIVE", "USD", "BENEFICIARY-B", "treasury-facility",
              "500", "POLICYHASH-1", "0", "9999999999"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)

    tx = contract.award(
        args=["REQ-LIVE", "AWD-LIVE", "400", "5000000000"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)

    award = json.loads(contract.get_award(args=["AWD-LIVE"]).call())
    assert award["status"] == "AWARDED"
    assert award["max_authority"] == "400"

    decision = json.loads(
        contract.verify_authority(
            args=["AWD-LIVE", "BENEFICIARY-B", "POOL-LIVE", "treasury-facility", "350", "5000000005"]
        ).call()
    )
    assert decision["decision"] == "AUTHORIZE"

    over = json.loads(
        contract.verify_authority(
            args=["AWD-LIVE", "BENEFICIARY-B", "POOL-LIVE", "treasury-facility", "401", "5000000006"]
        ).call()
    )
    assert over["decision"] == "DENY"
