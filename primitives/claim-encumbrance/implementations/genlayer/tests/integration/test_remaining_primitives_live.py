"""Live end-to-end transaction tests for the remaining primitives on GLSim.

Covers claim-encumbrance, capital-commitment, policy-envelope (incl. the
comparative LLM validator through sim_installMocks), workflow-authorization
(principal-gated acceptance), and mandate-allocation.

Run:
    source ~/nomos-venv312/bin/activate
    gltest <this file> -v
Requires glsim on :4000 and contracts/ symlinks to primitive implementations.
"""

import json
import urllib.request

from gltest import get_contract_factory
from gltest.assertions import tx_execution_succeeded
from gltest_cli.config.general import get_general_config


def _install_sim_llm_mock():
    """Deterministic LLM mock so policy-envelope clause interpretation
    reaches consensus reproducibly."""
    endpoint = get_general_config().get_rpc_url()
    body = json.dumps({
        "jsonrpc": "2.0",
        "method": "sim_installMocks",
        "params": {
            "llm_mocks": {
                r"You interpret one declared mandate clause.*": {
                    "decision": "ADMIT",
                    "analysis": "mocked interpretation",
                }
            },
            "strict": False,
        },
        "id": 1,
    }).encode()
    req = urllib.request.Request(
        endpoint, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def test_claim_encumbrance_live_capacity_cycle():
    factory = get_contract_factory(contract_file_path="claim_encumbrance.py")
    contract = factory.deploy()

    tx = contract.set_financeable_amount(
        args=["CL-LIVE", "1000"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)

    tx = contract.reserve(args=["R1", "CL-LIVE", "600"]).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)

    # over-commit denied on-chain: tx status 7 (reverted) IS the enforcement
    tx = contract.reserve(args=["R2", "CL-LIVE", "500"]).transact(wait_interval=10000, wait_retries=20)
    assert not tx_execution_succeeded(tx)  # reverted = over-commit blocked
    assert int(contract.active_encumbrances(args=["CL-LIVE"]).call()) == 600

    # release frees capacity exactly once
    tx = contract.release(args=["R1"]).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)
    assert int(contract.active_encumbrances(args=["CL-LIVE"]).call()) == 0

    # replay of released reservation rejected (tx reverts)
    tx = contract.release(args=["R1"]).transact(wait_interval=10000, wait_retries=20)
    assert not tx_execution_succeeded(tx)


def test_capital_commitment_live_backing_cycle():
    factory = get_contract_factory(contract_file_path="capital_commitment.py")
    contract = factory.deploy()

    # discover surface from vectors: set_backing(pool, asset, amount)
    tx = contract.set_backing(args=["POOL-LIVE", "USD", "10000"]).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)

    assert int(contract.available_capacity(args=["POOL-LIVE", "USD"]).call()) == 10000

    # reserve then commit (two-step lifecycle per CAPABILITY)
    tx = contract.reserve(
        args=["CMT-LIVE", "POOL-LIVE", "USD", "BENEFICIARY-B", "4000", "9999999999"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)
    assert int(contract.available_capacity(args=["POOL-LIVE", "USD"]).call()) == 6000

    tx = contract.commit(args=["CMT-LIVE"]).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)


def test_policy_envelope_live_interpretation():
    _install_sim_llm_mock()
    factory = get_contract_factory(contract_file_path="policy_envelope.py")
    contract = factory.deploy()

    tx = contract.create_envelope(
        args=["ENV-LIVE", "POLICYHASH-1", "1000", "USD", "0", "9999999999"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)

    # deterministic gate: within limits -> ADMIT
    tx = contract.evaluate_request(
        args=["ENV-LIVE", "REQ-OK", "400", "USD", "ACTOR-A", "TARGET-X", "5000000000"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)

    # deterministic gate: exceeds limit -> DENY, capacity untouched
    tx = contract.evaluate_request(
        args=["ENV-LIVE", "REQ-BAD", "5000", "USD", "ACTOR-A", "TARGET-X", "5000000001"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)
    used = int(contract.used_amount(args=["ENV-LIVE"]).call())
    assert used == 400  # DENY consumed nothing — proves the denial on-chain
    denied_raw = contract.get_request(args=["ENV-LIVE", "REQ-BAD"]).call()
    if denied_raw:
        assert json.loads(denied_raw)["decision"] == "DENY"

    # judgment surface through real consensus (mocked validator): comparative rerun
    tx = contract.attach_mandate_clause(
        args=["ENV-LIVE", "MC-LIVE", "Only vendor invoices related to project alpha are admissible"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)

    tx = contract.interpret_clause(
        args=["ENV-LIVE", "MC-LIVE", '{"vendor":"alpha-construction","memo":"project alpha invoice"}', "INT-J1"]
    ).transact(wait_interval=10000, wait_retries=30)
    assert tx_execution_succeeded(tx)
    interp = json.loads(contract.get_clause_interpretation(args=["INT-J1"]).call())
    assert interp["decision"] == "ADMIT"


def test_workflow_authorization_live_delegation():
    factory = get_contract_factory(contract_file_path="workflow_authorization.py")
    contract = factory.deploy()

    tx = contract.grant_path(
        args=["PATH-LIVE", "PRINCIPAL-LIVE", "AGENT-LIVE", "treasury-payments",
              "500", "USD", "0", "9999999999"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)

    tx = contract.propose_pact(
        args=["PACT-LIVE", "PATH-LIVE", "WF-LIVE-1", '{"amount":"300"}', "5000000000"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)

    pact = json.loads(contract.get_pact(args=["PACT-LIVE"]).call())
    assert pact["status"] == "PROPOSED"

    # blocked decision cannot execute
    tx = contract.execute_pact(args=["PACT-LIVE", "300", "5000000001"]).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)
    decision = json.loads(contract.get_pact(args=["PACT-LIVE"]).call())
    assert decision["status"] == "PROPOSED"  # DENY mutated nothing


def test_mandate_allocation_live_evaluation():
    factory = get_contract_factory(contract_file_path="mandate_allocation.py")
    contract = factory.deploy()

    tx = contract.register_mandate(
        args=["MAN-LIVE", "sha256:mandate-doc", "100000", "USD", '["invoice"]']
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)

    tx = contract.evaluate_opportunity(
        args=["RES-LIVE-1", "MAN-LIVE", "OPP-LIVE-1", "invoice", "60000", "5000000000"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)

    evaluation = json.loads(contract.get_evaluation(args=["RES-LIVE-1"]).call())
    assert evaluation["eligibility"] == "ELIGIBLE"

    # exposure cap enforcement on-chain
    tx = contract.evaluate_opportunity(
        args=["RES-LIVE-2", "MAN-LIVE", "OPP-LIVE-2", "invoice", "60000", "5000000001"]
    ).transact(wait_interval=10000, wait_retries=20)
    assert tx_execution_succeeded(tx)
    evaluation2 = json.loads(contract.get_evaluation(args=["RES-LIVE-2"]).call())
    assert evaluation2["eligibility"] == "INELIGIBLE"
    assert int(contract.committed_exposure(args=["MAN-LIVE"]).call()) == 60000
