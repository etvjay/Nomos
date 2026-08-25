"""PPA flow tests via gltest (contract runs in the GenVM on GLSim localnet).

DENY paths are recorded as auditable DENIED payment records — asserted via
get_payment reads, since write-method return values aren't surfaced in the
receipt by gltest 0.29.

Run:
    source ~/nomos-venv312/bin/activate
    gltest primitives/ppa/implementations/genlayer/tests/test_ppa_flows.py -q

Requires glsim on :4000 and the contracts/ppa.py symlink.
"""
import json

from gltest import get_contract_factory, get_accounts
from gltest.assertions import tx_execution_succeeded

OWNER = get_accounts()[0].address
RECIPIENT = "0x9f6aa7364d20cf25f054ea83f3cb950317fd34b6"
OUTSIDER = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def _rules(per_tx="500", daily="1000", allowlist=None):
    r = {"daily_limit": daily, "per_tx_limit": per_tx, "currency": "USDC"}
    if allowlist is not None:
        r["allowlist"] = allowlist
    return json.dumps(r)


def _setup(c, account_id="ACC1", deposit="2000", **kw):
    c.create_account(args=[account_id, _rules(**kw)]).transact(wait_interval=3000, wait_retries=10)
    c.deposit(args=[account_id, deposit]).transact(wait_interval=3000, wait_retries=10)
    acc = c.get_account(args=[account_id]).call()
    assert acc["balance"] == deposit


def test_happy_path_send():
    factory = get_contract_factory(contract_file_path="ppa.py")
    c = factory.deploy()
    c.initialize(args=[OWNER]).transact(wait_interval=3000, wait_retries=10)
    _setup(c)

    tx = c.send(args=["ACC1", "P1", RECIPIENT, "300"]).transact(wait_interval=5000, wait_retries=15)
    assert tx_execution_succeeded(tx)

    acc = c.get_account(args=["ACC1"]).call()
    assert acc["balance"] == "1700"
    assert acc["daily_spent"] == "300"

    pay = c.get_payment(args=["P1"]).call()
    assert pay["status"] == "SETTLED"
    assert pay["to"].lower() == RECIPIENT.lower()
    assert pay["amount"] == "300"


def test_per_tx_limit_denied_and_retryable():
    factory = get_contract_factory(contract_file_path="ppa.py")
    c = factory.deploy()
    c.initialize(args=[OWNER]).transact(wait_interval=3000, wait_retries=10)
    _setup(c, per_tx="500")

    tx = c.send(args=["ACC1", "P1", RECIPIENT, "800"]).transact(wait_interval=5000, wait_retries=15)
    assert tx_execution_succeeded(tx)  # deny is a valid outcome, not a revert

    acc = c.get_account(args=["ACC1"]).call()
    assert acc["balance"] == "2000"  # deny moved nothing

    pay = c.get_payment(args=["P1"]).call()
    assert pay["status"] == "DENIED"
    assert pay["reason"] == "POLICY_PER_TX_LIMIT"

    # same id retryable within limits (deny does not burn the id)
    tx2 = c.send(args=["ACC1", "P1", RECIPIENT, "400"]).transact(wait_interval=5000, wait_retries=15)
    assert tx_execution_succeeded(tx2)
    pay2 = c.get_payment(args=["P1"]).call()
    assert pay2["status"] == "SETTLED"
    assert c.get_account(args=["ACC1"]).call()["balance"] == "1600"


def test_allowlist_denied():
    factory = get_contract_factory(contract_file_path="ppa.py")
    c = factory.deploy()
    c.initialize(args=[OWNER]).transact(wait_interval=3000, wait_retries=10)
    _setup(c, allowlist=[RECIPIENT])

    c.send(args=["ACC1", "P1", OUTSIDER, "50"]).transact(wait_interval=5000, wait_retries=15)
    pay = c.get_payment(args=["P1"]).call()
    assert pay["status"] == "DENIED"
    assert pay["reason"] == "POLICY_DENYLIST"
    assert c.get_account(args=["ACC1"]).call()["balance"] == "2000"


def test_insufficient_commitment_denied():
    factory = get_contract_factory(contract_file_path="ppa.py")
    c = factory.deploy()
    c.initialize(args=[OWNER]).transact(wait_interval=3000, wait_retries=10)
    _setup(c, deposit="100", per_tx="9999", daily="99999")

    c.send(args=["ACC1", "P1", RECIPIENT, "500"]).transact(wait_interval=5000, wait_retries=15)
    pay = c.get_payment(args=["P1"]).call()
    assert pay["reason"] == "INSUFFICIENT_COMMITMENT"


def test_invoice_flow():
    factory = get_contract_factory(contract_file_path="ppa.py")
    c = factory.deploy()
    c.initialize(args=[OWNER]).transact(wait_interval=3000, wait_retries=10)
    _setup(c)

    c.issue_invoice(args=["INV1", RECIPIENT, "250",
                          json.dumps([{"desc": "consulting", "amount": "250"}])]).transact(wait_interval=3000, wait_retries=10)
    inv = c.get_invoice(args=["INV1"]).call()
    assert inv["status"] == "OPEN"

    tx = c.settle_invoice(args=["INV1", "ACC1"]).transact(wait_interval=5000, wait_retries=15)
    assert tx_execution_succeeded(tx)

    inv = c.get_invoice(args=["INV1"]).call()
    assert inv["status"] == "SETTLED"
    pay = c.get_payment(args=["pay-INV1"]).call()
    assert pay["amount"] == "250"
    assert c.get_account(args=["ACC1"]).call()["balance"] == "1750"


def test_dispute_refund_restores_balance():
    factory = get_contract_factory(contract_file_path="ppa.py")
    c = factory.deploy()
    c.initialize(args=[OWNER]).transact(wait_interval=3000, wait_retries=10)
    _setup(c)
    c.send(args=["ACC1", "P1", RECIPIENT, "300"]).transact(wait_interval=5000, wait_retries=15)
    assert c.get_account(args=["ACC1"]).call()["balance"] == "1700"

    c.dispute_payment(args=["D1", "P1", "delivery-mismatch",
                            json.dumps({"expected": "service delivered"})]).transact(wait_interval=3000, wait_retries=10)
    c.resolve_dispute(args=["D1", "refund"]).transact(wait_interval=3000, wait_retries=10)

    d = c.get_dispute(args=["D1"]).call()
    assert d["status"] == "RESOLVED" and d["remedy"] == "refund"

    pay = c.get_payment(args=["P1"]).call()
    assert pay["status"] == "REFUNDED"
    assert c.get_account(args=["ACC1"]).call()["balance"] == "2000"
