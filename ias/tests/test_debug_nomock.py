"""Debug check_monitor on GLSim - sim exposes GenVM stderr in receipts."""
import json

from gltest import get_contract_factory
from gltest.assertions import tx_execution_succeeded

from gltest import get_accounts
OWNER = get_accounts()[0].address


def test_debug_no_mock():
    f = get_contract_factory(contract_file_path="ias_stage1.py")
    c = f.deploy()
    tx = c.initialize(args=[OWNER]).transact(wait_interval=2000, wait_retries=10)
    print("init:", tx_execution_succeeded(tx))

    tx2 = c.create_monitor(args=["M-DBG",
        "example numeric", "https://example.com", "price",
        "1", "above", "25.0", "low", ""]).transact(wait_interval=3000, wait_retries=10)
    ok = tx_execution_succeeded(tx2)
    print("create:", ok)
    if not ok:
        lr = tx2["consensus_data"]["leader_receipt"][0]
        print("CREATE STDERR:", str(lr.get("genvm_result", {}).get("stderr"))[:400])
        return

    tx3 = c.check_monitor(args=["M-DBG"]).transact(wait_interval=15000, wait_retries=30)
    ok3 = tx_execution_succeeded(tx3)
    print("check:", ok3)
    if not ok3:
        lr = tx3["consensus_data"]["leader_receipt"][0]
        gr = lr.get("genvm_result", {})
        print("CHECK STDERR:", str(gr.get("stderr"))[:600])
        print("CHECK STDOUT:", str(gr.get("stdout"))[:300])
    else:
        m = c.get_monitor(args=["M-DBG"]).call()
        print("MONITOR AFTER:", json.dumps(m)[:300])
