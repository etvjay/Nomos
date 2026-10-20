"""Caller-identity spike: what does Core observe when an Adapter calls it?

Throwaway. No PPA edits, no capability change, no deployment.
"""
import json
from gltest import get_contract_factory, get_accounts
from gltest.assertions import tx_execution_succeeded

OWNER = get_accounts()[0].address
OTHER = get_accounts()[1].address
CORE = "/tmp/opencode/spike/core_probe.py"
ADAPTER = "/tmp/opencode/spike/adapter_probe.py"


def _hex(s):
    return s.lower().replace("0x", "")


def test_spike():
    core = get_contract_factory(contract_file_path=CORE).deploy()
    core_addr = core.address

    t = core.record_sender(args=["direct_eoa"]).transact(wait_interval=3000, wait_retries=10)
    direct = core.get_observation(args=["direct_eoa"]).call()
    print("\n================ BOUNDARY OBSERVATIONS ================")
    print(f"EOA (caller)      : {_hex(OWNER)}")
    print(f"Core address      : {_hex(core_addr)}")
    print(f"[1] DIRECT EOA -> Core")
    print(f"    core observed : {direct}")
    print(f"    == EOA?      : {_hex(direct) == _hex(OWNER)}")

    adapter = get_contract_factory(contract_file_path=ADAPTER).deploy()
    adapter.initialize(args=[core_addr]).transact(wait_interval=3000, wait_retries=10)
    print(f"\nAdapter address   : {_hex(adapter.address)}")

    print(f"\n[2] ADAPTER -> Core (gl.get_contract_at + emit on='accepted')")
    t2 = adapter.forward(args=["via_adapter", OWNER, "100"]).transact(
        wait_interval=5000, wait_retries=25)
    print(f"    forward tx ok : {tx_execution_succeeded(t2)}")
    try:
        obs = json.loads(core.get_observation(args=["via_adapter"]).call())
        print(f"    core observed : {json.dumps(obs)}")
        o = _hex(obs["observed_sender"])
        print(f"    == ADAPTER?   : {o == _hex(adapter.address)}")
        print(f"    == original EOA? {o == _hex(OWNER)}")
    except Exception as e:
        print(f"    core has NO observation -> {type(e).__name__}: {str(e)[:160]}")

    print(f"\n[3] ADAPTER forwarding with SPOOFED declared_source")
    t3 = adapter.forward(args=["spoofed", "0x" + "ab" * 20, "999"]).transact(
        wait_interval=5000, wait_retries=25)
    print(f"    forward tx ok : {tx_execution_succeeded(t3)}")
    try:
        obs = json.loads(core.get_observation(args=["spoofed"]).call())
        print(f"    core observed : {json.dumps(obs)}")
    except Exception as e:
        print(f"    core has NO observation -> {type(e).__name__}: {str(e)[:160]}")
    print("\n=====================================================")
