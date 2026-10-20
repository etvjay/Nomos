"""PPA GenLayer spine: receipt -> proposal -> gated send.

v0.3: the owner is no longer implicitly an adjudicator. Both tests register a
judicator and submit through it, preserving the disposition assertions. The
origin-binding rules themselves are specified in test_ppa_receipt_origin.py.
"""
import json
from gltest import get_contract_factory, get_accounts
from gltest.assertions import tx_execution_succeeded

OWNER = get_accounts()[0].address
RECIPIENT = "0x9f6aa7364d20cf25f054ea83f3cb950317fd34b6"
ISSUER = "0x1111111111111111111111111111111111111111"


ADJUDICATOR = get_accounts()[1]


def _deploy():
    c = get_contract_factory(contract_file_path="ppa.py").deploy()
    c.initialize(args=[OWNER]).transact(wait_interval=3000, wait_retries=10)
    return c


def _funded(c, rules):
    c.create_account(args=["ACC1", rules]).transact(wait_interval=3000, wait_retries=10)
    c.deposit(args=["ACC1", "1000"]).transact(wait_interval=3000, wait_retries=10)


def _register(c):
    c.register_adjudicator(args=[json.dumps({
        "source_contract": ADJUDICATOR.address,
        "authority_fingerprint": "sha256:spine-fp-001",
        "policy_version": "TECH-V1",
        "created_at": "2020-01-01T00:00:00+00:00",
        "expires_at": "2099-01-01T00:00:00+00:00",
    })]).transact(wait_interval=3000, wait_retries=10)


def _adj():
    """The contract driven by the registered adjudicator account."""
    return ADJUDICATOR


def _rules(require_att=False):
    r = {"daily_limit": "1000", "per_tx_limit": "500", "currency": "USDC"}
    if require_att:
        r.update({
            "require_attestation": True,
            "attestation_issuers": [ISSUER],
            "attestation_policy_version": "TECH-V1",
        })
    return json.dumps(r)


def _receipt(status="ACCEPTED", **kw):
    v = {
        "decision_id": "DEC-1",
        "source_contract": ADJUDICATOR.address,
        "authority_fingerprint": "sha256:spine-fp-001",
        "question_hash": "sha256:q",
        "evidence_hash": "sha256:e",
        "decision_status": status,
        "equivalence_mode": "comparative",
        "policy_version": "TECH-V1",
        "created_at": "2020-01-01T00:00:00+00:00",
        "expires_at": "2099-01-01T00:00:00+00:00",
    }
    v.update(kw)
    return json.dumps(v)


def _proposal(**kw):
    v = {
        "proposal_id": "PROP-1",
        "decision_id": "DEC-1",
        "account_id": "ACC1",
        "payment_id": "PAY-1",
        "to": RECIPIENT,
        "amount": "100",
        "policy_version": "TECH-V1",
    }
    v.update(kw)
    return json.dumps(v)


def test_spine_accepted_receipt_to_settlement():
    c = _deploy()
    _funded(c, _rules())
    _register(c)
    tx = c.connect(_adj()).submit_decision_receipt(
        args=[_receipt()]).transact(wait_interval=3000, wait_retries=10)
    assert tx_execution_succeeded(tx)
    r = c.get_receipt(args=["DEC-1"]).call()
    assert r["decision_status"] == "ACCEPTED" and r["actionability"] == "ACTIONABLE"
    tx = c.admit_proposal(args=[_proposal()]).transact(wait_interval=3000, wait_retries=10)
    assert tx_execution_succeeded(tx)
    p = c.get_proposal(args=["PROP-1"]).call()
    assert p["status"] == "ADMITTED"
    tx = c.execute_proposal(args=["PROP-1"]).transact(wait_interval=5000, wait_retries=15)
    assert tx_execution_succeeded(tx)
    pay = c.get_payment(args=["PAY-1"]).call()
    assert pay["status"] == "SETTLED" and pay["decision_id"] == "DEC-1"
    assert c.get_account(args=["ACC1"]).call()["balance"] == "900"
    assert c.get_proposal(args=["PROP-1"]).call()["status"] == "EXECUTED"


def test_spine_rejected_receipt_cannot_execute():
    c = _deploy()
    _funded(c, _rules())
    _register(c)
    c.connect(_adj()).submit_decision_receipt(
        args=[_receipt("REJECTED")]).transact(wait_interval=3000, wait_retries=10)
    r = c.get_receipt(args=["DEC-1"]).call()
    assert r["actionability"] == "NON_ACTIONABLE"
    c.admit_proposal(args=[_proposal()]).transact(wait_interval=3000, wait_retries=10)
    # admit should fail closed as REJECTED_PROPOSAL; proposal may not exist
    try:
        c.get_proposal(args=["PROP-1"]).call()
        prop_exists = True
    except Exception:
        prop_exists = False
    assert prop_exists is False
    assert c.get_account(args=["ACC1"]).call()["balance"] == "1000"
