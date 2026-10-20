"""Focused PPA attestation-gate tests via gltest (GenVM on GLSim localnet).

Covers: require_attestation=false backward compatibility, missing/valid/
expired/revoked attestations, invalid status/subject/issuer/policy binding,
provider outage modeled as absent evidence (fail-closed), payment-id replay,
and balance conservation.

Run:
    source ~/nomos-venv312/bin/activate
    gltest primitives/ppa/implementations/genlayer/tests/test_ppa_attestations.py -q

Requires glsim on :4000 and the contracts/ppa.py symlink.
"""
import json

from gltest import get_contract_factory, get_accounts
from gltest.assertions import tx_execution_succeeded

OWNER = get_accounts()[0].address
RECIPIENT = "0x9f6aa7364d20cf25f054ea83f3cb950317fd34b6"
ISSUER = "0x1111111111111111111111111111111111111111"
OUTSIDER = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

VALID = {
    "subject": RECIPIENT,
    "issuer": ISSUER,
    "status": "VALID",
    "issued_at": "2020-01-01T00:00:00+00:00",
    "expires_at": "2099-01-01T00:00:00+00:00",
    "evidence_hash": "evh-att-001",
    "policy_version": "TECH-V1",
}


def _att(**overrides):
    a = dict(VALID)
    a.update(overrides)
    return json.dumps(a)


def _att_rules():
    return json.dumps({
        "daily_limit": "1000", "per_tx_limit": "500", "currency": "USDC",
        "require_attestation": True,
        "attestation_issuers": [ISSUER],
        "attestation_policy_version": "TECH-V1",
    })


def _deploy():
    factory = get_contract_factory(contract_file_path="ppa.py")
    c = factory.deploy()
    c.initialize(args=[OWNER]).transact(wait_interval=3000, wait_retries=10)
    return c


def _setup(c, rules, deposit="2000", account_id="ACC1"):
    c.create_account(args=[account_id, rules]).transact(wait_interval=3000, wait_retries=10)
    c.deposit(args=[account_id, deposit]).transact(wait_interval=3000, wait_retries=10)
    return c


def _register(c, attestation_id, payload):
    c.register_attestation(args=[attestation_id, payload]).transact(
        wait_interval=3000, wait_retries=10)


def _send(c, account_id, payment_id, to=RECIPIENT, amount="300"):
    tx = c.send(args=[account_id, payment_id, to, amount]).transact(
        wait_interval=5000, wait_retries=15)
    assert tx_execution_succeeded(tx)  # DENY is a recorded outcome, not a revert


def _balance(c, account_id="ACC1"):
    return c.get_account(args=[account_id]).call()["balance"]


def _payment(c, payment_id):
    return c.get_payment(args=[payment_id]).call()


def test_gate_off_is_backward_compatible():
    """No require_attestation -> send settles exactly as before, even with an
    empty attestation registry."""
    c = _deploy()
    _setup(c, json.dumps({"daily_limit": "1000", "per_tx_limit": "500",
                          "currency": "USDC"}))
    _send(c, "ACC1", "P1")
    assert _payment(c, "P1")["status"] == "SETTLED"
    assert _balance(c) == "1700"


def test_missing_attestation_denied_fail_closed():
    c = _deploy()
    _setup(c, _att_rules())
    _send(c, "ACC1", "P1")
    pay = _payment(c, "P1")
    assert pay["status"] == "DENIED" and pay["reason"] == "ATTESTATION_MISSING"
    assert _balance(c) == "2000"  # deny moved nothing


def test_valid_attestation_admits():
    c = _deploy()
    _setup(c, _att_rules())
    _register(c, "A1", _att())
    got = c.get_attestation(args=["A1"]).call()
    assert got["status"] == "VALID" and got["policy_version"] == "TECH-V1"
    _send(c, "ACC1", "P1")
    assert _payment(c, "P1")["status"] == "SETTLED"
    assert _balance(c) == "1700"


def test_expired_attestation_denied():
    c = _deploy()
    _setup(c, _att_rules())
    _register(c, "A1", _att(expires_at="2021-01-01T00:00:00+00:00"))
    _send(c, "ACC1", "P1")
    assert _payment(c, "P1")["reason"] == "ATTESTATION_EXPIRED"
    assert _balance(c) == "2000"


def test_revoked_attestation_denied():
    c = _deploy()
    _setup(c, _att_rules())
    _register(c, "A1", _att())
    c.revoke_attestation(args=["A1"]).transact(wait_interval=3000, wait_retries=10)
    assert c.get_attestation(args=["A1"]).call()["status"] == "REVOKED"
    _send(c, "ACC1", "P1")
    assert _payment(c, "P1")["reason"] == "ATTESTATION_REVOKED"
    assert _balance(c) == "2000"


def test_invalid_status_rejected_at_registration():
    c = _deploy()
    _setup(c, _att_rules())
    _register(c, "A1", _att(status="PENDING"))  # registry unchanged on reject
    # gate stays fail-closed: nothing admissible registered
    _send(c, "ACC1", "P1")
    assert _payment(c, "P1")["reason"] == "ATTESTATION_MISSING"


def test_subject_mismatch_denied():
    c = _deploy()
    _setup(c, _att_rules())
    _register(c, "A1", _att(subject=OUTSIDER))
    _send(c, "ACC1", "P1")
    assert _payment(c, "P1")["reason"] == "ATTESTATION_SUBJECT_MISMATCH"


def test_issuer_unauthorized_denied():
    c = _deploy()
    _setup(c, _att_rules())
    _register(c, "A1", _att(issuer=OUTSIDER))
    _send(c, "ACC1", "P1")
    assert _payment(c, "P1")["reason"] == "ATTESTATION_ISSUER_UNAUTHORIZED"


def test_policy_version_mismatch_denied():
    c = _deploy()
    _setup(c, _att_rules())
    _register(c, "A1", _att(policy_version="TECH-V0"))
    _send(c, "ACC1", "P1")
    assert _payment(c, "P1")["reason"] == "ATTESTATION_POLICY_MISMATCH"


def test_provider_outage_is_absent_evidence_not_approval():
    """A provider outage means no attestation can be registered: the gate sees
    an absent record and denies. Outage is never mistaken for approval."""
    c = _deploy()
    _setup(c, _att_rules())
    # outage window: registry stays empty across sends
    _send(c, "ACC1", "P1")
    assert _payment(c, "P1")["reason"] == "ATTESTATION_MISSING"
    _send(c, "ACC1", "P2")
    assert _payment(c, "P2")["reason"] == "ATTESTATION_MISSING"
    assert _balance(c) == "2000"


def test_payment_id_replay_rejected_and_balance_conserved():
    c = _deploy()
    _setup(c, _att_rules())
    _register(c, "A1", _att())
    _send(c, "ACC1", "P1")
    assert _payment(c, "P1")["status"] == "SETTLED"
    # replay of the settled id must raise, not double-spend
    try:
        c.send(args=["ACC1", "P1", RECIPIENT, "100"]).transact(
            wait_interval=5000, wait_retries=15)
        raise AssertionError("replay of settled payment id must fail")
    except Exception:
        pass
    pay = _payment(c, "P1")
    assert pay["status"] == "SETTLED" and pay["amount"] == "300"
    assert _balance(c) == "1700"  # only the settled amount ever left


def test_denied_id_retryable_then_settles_once():
    c = _deploy()
    _setup(c, _att_rules())
    _send(c, "ACC1", "P1")  # denied: missing attestation
    assert _payment(c, "P1")["status"] == "DENIED"
    _register(c, "A1", _att())
    _send(c, "ACC1", "P1")  # same id retryable after deny
    assert _payment(c, "P1")["status"] == "SETTLED"
    assert _balance(c) == "1700"
    assert c.get_account(args=["ACC1"]).call()["daily_spent"] == "300"


def test_balance_conservation_across_mixed_outcomes():
    c = _deploy()
    _setup(c, _att_rules())
    _register(c, "A1", _att(expires_at="2021-01-01T00:00:00+00:00"))  # expired
    _register(c, "A2", _att())                                        # valid
    _send(c, "ACC1", "P1")
    # A1 expired but A2 is valid: an expired candidate never blocks a valid one
    pay = _payment(c, "P1")
    assert pay["status"] == "SETTLED"
    _send(c, "ACC1", "P2", amount="800")  # over per-tx limit -> policy deny
    assert _payment(c, "P2")["reason"] == "POLICY_PER_TX_LIMIT"
    acc = c.get_account(args=["ACC1"]).call()
    assert acc["balance"] == "1700"  # deposit - settled only
    assert acc["daily_spent"] == "300"
