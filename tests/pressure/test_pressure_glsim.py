"""GLSim consensus-level pressure test (integration mode).

Fires a rapid burst of payment writes at the PPA through the real GenLayer
execution path (leader + consensus validation on GLSim localnet) and asserts
economic conservation under load: exactly the daily cap settles, overflow is
denied, and no funds appear or vanish.

Run (GLSim must be listening on the address in gltest.config.yaml):
    gltest tests/pressure/test_pressure_glsim.py -v -s
"""
import json

from gltest import get_contract_factory, get_accounts
from gltest.assertions import tx_execution_succeeded

OWNER = get_accounts()[0].address
RECIPIENT = "0x9f6aa7364d20cf25f054ea83f3cb950317fd34b6"


def _tx(method, wait_interval=3000, wait_retries=10):
    receipt = method.transact(wait_interval=wait_interval, wait_retries=wait_retries)
    assert tx_execution_succeeded(receipt)
    return receipt


def test_payment_burst_conserves_funds_under_consensus():
    """12 writes back-to-back: 10 settle up to the daily cap, 2 denied,
    balance conservation exact to the unit."""
    factory = get_contract_factory(contract_file_path="ppa.py")
    c = factory.deploy()

    _tx(c.initialize(args=[OWNER]))
    rules = json.dumps({"daily_limit": "1000", "per_tx_limit": "100", "currency": "USDC"})
    _tx(c.create_account(args=["ACC1", rules]))
    _tx(c.deposit(args=["ACC1", "5000"]))

    statuses = []
    for i in range(12):
        _tx(c.send(args=["ACC1", f"BURST-{i}", RECIPIENT, "100"]))
        pay = c.get_payment(args=[f"BURST-{i}"]).call()
        statuses.append(pay["status"])

    assert statuses.count("SETTLED") == 10
    assert statuses.count("DENIED") == 2
    denied = c.get_payment(args=["BURST-11"]).call()
    assert denied["reason"] == "POLICY_DAILY_LIMIT"

    acc = c.get_account(args=["ACC1"]).call()
    assert acc["balance"] == "4000"       # 5000 - 10*100 exactly; denials burned nothing
    assert acc["daily_spent"] == "1000"   # cap exactly consumed, never exceeded

    # Replay of a settled id through the consensus path must fail execution.
    receipt = c.send(args=["ACC1", "BURST-0", RECIPIENT, "100"]).transact(
        wait_interval=3000, wait_retries=10)
    assert not tx_execution_succeeded(receipt)
    acc = c.get_account(args=["ACC1"]).call()
    assert acc["balance"] == "4000"       # replay moved nothing

    # Remaining uncommitted funds are withdrawable by the owner only.
    _tx(c.withdraw(args=["ACC1", "4000"]))
    assert c.get_account(args=["ACC1"]).call()["balance"] == "0"
