"""Enforcement at the adapter->core boundary. One emit per test, fresh deploys.

Throwaway spike. No PPA edits, no capability change, no deployment.
"""
import json
import time

from gltest import get_contract_factory
from gltest.assertions import tx_execution_succeeded

CORE = "/tmp/opencode/spike/core_enforce.py"
ADAPTER = "/tmp/opencode/spike/adapter_enforce.py"
def _h(s): return s.lower().replace("0x", "")

def poll(fn, *a, tries=60, delay=1.0):
    last = None
    for _ in range(tries):
        try:
            return fn(args=list(a)).call()
        except Exception as e:
            last = e; time.sleep(delay)
    raise last

def _wire(direct_vm=None):
    core = get_contract_factory(contract_file_path=CORE).deploy()
    core.set_cap(args=["ACC1", "500"]).transact(wait_interval=3000, wait_retries=10)
    ad = get_contract_factory(contract_file_path=ADAPTER).deploy()
    ad.initialize(args=[core.address]).transact(wait_interval=3000, wait_retries=10)
    return core, ad

def test_A_unregistered_adapter_rejected():
    core, ad = _wire()
    tx = ad.submit_and_forward(args=["A", "ACC1", "100"]).transact(wait_interval=5000, wait_retries=25)
    print("   adapter tx succeeded:", tx_execution_succeeded(tx))
    v = json.loads(poll(core.get_log, "A"))
    print("\nA unregistered adapter ->", v)
    assert v["verdict"] == "REJECTED_CALLER_NOT_REGISTERED_ADAPTER"
    assert _h(v["caller"]) == _h(ad.address), "core must attribute the call to the adapter"

def test_B_registered_adapter_executes_within_cap():
    core, ad = _wire()
    core.register_adapter(args=[ad.address]).transact(wait_interval=3000, wait_retries=10)
    tx = ad.submit_and_forward(args=["B", "ACC1", "100"]).transact(wait_interval=5000, wait_retries=25)
    print("   adapter tx succeeded:", tx_execution_succeeded(tx))
    v = json.loads(poll(core.get_log, "B"))
    print("B registered adapter, 100<=500 ->", v)
    assert v["verdict"] == "EXECUTED"
    assert _h(v["caller"]) == _h(ad.address)

def test_C_adapter_cannot_widen_amount():
    core, ad = _wire()
    core.register_adapter(args=[ad.address]).transact(wait_interval=3000, wait_retries=10)
    tx = ad.submit_and_forward(args=["C", "ACC1", "99999"]).transact(wait_interval=5000, wait_retries=25)
    print("   adapter tx succeeded:", tx_execution_succeeded(tx))
    v = json.loads(poll(core.get_log, "C"))
    print("C adapter widens to 99999 ->", v)
    assert v["verdict"] == "REJECTED_WIDENS_BEYOND_CAP"
    assert v["amount"] == "99999", "core saw the widened value and rejected it independently"

def test_D_core_attributes_to_adapter_not_original_eoa():
    core, ad = _wire()
    core.register_adapter(args=[ad.address]).transact(wait_interval=3000, wait_retries=10)
    ad.submit_and_forward(args=["D", "ACC1", "10"]).transact(wait_interval=5000, wait_retries=25)
    v = json.loads(poll(core.get_log, "D"))
    seen_by_adapter = ad.seen(args=["D"]).call()
    print("D adapter saw caller:", seen_by_adapter)
    print("  core saw caller  :", v["caller"])
    print("  adapter address  :", _h(ad.address))
    assert _h(v["caller"]) == _h(ad.address), "core must see the ADAPTER"
    assert _h(v["caller"]) != _h(seen_by_adapter), "core must NOT see the original EOA"
