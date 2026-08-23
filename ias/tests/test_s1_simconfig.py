"""IAS Stage 1 consensus-machinery verification via genlayer_py with per-tx
sim_config LLM mocks (the mechanism glsim actually supports).

Run: source ~/nomos-venv312/bin/activate && python -m pytest ias/tests/test_s1_simconfig.py -q
"""
import json

import pytest
from genlayer_py import create_client, create_account
from genlayer_py.types import SimConfig

SENDER_KEY = "0x" + "11" * 32
CONTRACT_ADDR = None


def _sim_config():
    return SimConfig(
        llm_mocks={"": {"value": "42", "confidence": "high", "found": True}},
        strict=False)


def _client():
    return create_client(endpoint="http://127.0.0.1:4000/api",
                         account=create_account(SENDER_KEY))


@pytest.fixture(scope="module")
def setup():
    global CONTRACT_ADDR
    client = _client()
    code = open("/home/ubuntu/nomos/contracts/ias_stage1.py").read()
    tx = client.deploy_contract(code=code)
    rcpt = client.wait_for_transaction_receipt(tx)
    addr = (rcpt.get("data") or {}).get("contract_address") or \
           (rcpt.get("txDataDecoded") or {}).get("contractAddress")
    assert addr, f"no address: {str(rcpt)[:300]}"
    CONTRACT_ADDR = addr
    return client


def _write(client, method, args):
    h = client.write_contract(address=CONTRACT_ADDR, function_name=method,
                              args=args, sim_config=_sim_config())
    return client.wait_for_transaction_receipt(h)


def _read(client, method, args):
    return client.read_contract(address=CONTRACT_ADDR, function_name=method, args=args)


def test_full_machinery(setup):
    client = setup

    r = _write(client, "initialize", ["0x" + "11" * 20])
    assert r.get("status") in (1, "0x1")

    r = _write(client, "create_monitor",
               ["M-SIM", "mocked", "https://example.com", "price",
                "1", "above", "25.0", "medium",
                json.dumps({"action": "test"})])
    assert r.get("status") in (1, "0x1")

    # THE TEST: nondet flow with deterministic mock across validators
    r = _write(client, "check_monitor", ["M-SIM"])
    assert r.get("status") in (1, "0x1"), f"reverted: {str(r)[:250]}"

    m = _read(client, "get_monitor", ["M-SIM"])
    assert m["last_status"] == "success", f"status={m.get('last_status')}"
    assert str(m.get("last_value")) == "42"
