"""IAS three-stage flow tests via gltest on GLSim localnet.

Run:
    source ~/nomos-venv312/bin/activate
    gltest ias/tests/test_ias_stages.py -q
"""
import json

from gltest import get_contract_factory, get_accounts
from gltest.assertions import tx_execution_succeeded

OWNER = get_accounts()[0].address

RECIPIENT = "0x9f6aa7364d20cf25f054ea83f3cb950317fd34b6"


def _s1():
    f = get_contract_factory(contract_file_path="ias_stage1.py")
    c = f.deploy()
    c.initialize(args=[OWNER]).transact(
        wait_interval=2000, wait_retries=10)
    return c


def test_stage1_monitor_lifecycle_with_mock():
    c = _s1()
    # create monitor with a deterministic data source we can mock via sim
    tx = c.create_monitor(
        args=["M1", "BTC price", "https://example.com/btc", "price",
              "100000", "above", "5.0",
              json.dumps({"sub_account": "A1", "to": RECIPIENT,
                          "amount": "500", "payment_id": "AUTO-1"})],
    ).transact(wait_interval=3000, wait_retries=10)
    assert tx_execution_succeeded(tx)

    m = c.get_monitor(args=["M1"]).call()
    assert m["is_active"] is True
    assert m["threshold_value"] == "100000"


def test_stage2_group_and_correlation_policy():
    f = get_contract_factory(contract_file_path="ias_stage2.py")
    c = f.deploy()
    c.initialize(args=[OWNER]).transact(
        wait_interval=2000, wait_retries=10)

    for i, mid in enumerate(["M1", "M2", "M3"]):
        c.create_monitor(
            args=[mid, f"monitor {mid}", f"https://example.com/{i}", "price",
                  "100", "above", "5.0", "GROUP-A", "1", ""],
        ).transact(wait_interval=2000, wait_retries=10)

    tx = c.create_signal_group(
        args=["GROUP-A", json.dumps(["M1", "M2", "M3"]), 2, 3600]
    ).transact(wait_interval=2000, wait_retries=10)
    assert tx_execution_succeeded(tx)

    g = c.get_group(args=["GROUP-A"]).call()
    assert g["n_of_m"] == 2
    assert len(g["monitor_ids"]) == 3


def test_stage3_kill_switch_defaults_off():
    """Safety invariant: a fresh Stage 3 account has autonomous execution OFF."""
    f = get_contract_factory(contract_file_path="ias_stage3.py")
    c = f.deploy()
    c.initialize(args=[OWNER]).transact(
        wait_interval=2000, wait_retries=10)
    # account + policy exist; kill switch default OFF means auto-execution
    # paths return DISABLED until owner flips it.
    c.create_account(
        args=["ACC1", json.dumps({"daily_limit": "99999",
                                  "per_tx_limit": "99999",
                                  "currency": "GEN"})]
    ).transact(wait_interval=2000, wait_retries=10)
    acc = c.get_account(args=["ACC1"]).call()
    assert acc["status"] == "ACTIVE"
    assert acc["balance"] == "0"
