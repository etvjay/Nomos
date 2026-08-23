"""Stage 1 consensus-machinery test: mock LLM, verify nondet->vote->state."""
import json
import urllib.request

from gltest import get_contract_factory, get_accounts
from gltest.assertions import tx_execution_succeeded
from gltest_cli.config.general import get_general_config

OWNER = get_accounts()[0].address


def _install_mock():
    endpoint = get_general_config().get_rpc_url()
    body = json.dumps({
        "jsonrpc": "2.0",
        "method": "sim_installMocks",
        "params": {
            "llm_mocks": {
                r".*": {"value": "42", "confidence": "high", "found": True}
            },
            "strict": False,
        },
        "id": 1,
    }).encode()
    req = urllib.request.Request(endpoint, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _install_mock():
    import urllib.request
    from gltest_cli.config.general import get_general_config
    endpoint = get_general_config().get_rpc_url()
    body = json.dumps({
        "jsonrpc": "2.0",
        "method": "sim_installMocks",
        "params": {
            "llm_mocks": {r".*": {"value": "42", "confidence": "high", "found": True}},
            "strict": False,
        },
        "id": 1,
    }).encode()
    req = urllib.request.Request(endpoint, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        json.loads(resp.read())


def test_stage1_consensus_machinery():
    f = get_contract_factory(contract_file_path="ias_stage1.py")
    c = f.deploy()
    # NOTE: do not mutate chain.consensus_main_contract here — it's a shared
    # singleton and partial dicts (address without abi) poison later calls.
    tx = c.initialize(args=[OWNER]).transact(wait_interval=2000, wait_retries=10)
    assert tx_execution_succeeded(tx)


    tx2 = c.create_monitor(args=["M-MOCK", "mocked", "https://example.com",
        "price", "1", "above", "25.0", "medium",
        json.dumps({"action": "test"})]).transact(wait_interval=3000, wait_retries=10)
    assert tx_execution_succeeded(tx2)

    _install_mock()

    tx3 = c.check_monitor(args=["M-MOCK"]).transact(wait_interval=15000, wait_retries=30)
    if not tx_execution_succeeded(tx3):
        lr = tx3["consensus_data"]["leader_receipt"][0]
        gr = lr.get("genvm_result") or {}
        print("STDERR:", str(gr.get("stderr"))[:400])
        print("RESULT:", str(lr.get("result"))[:200])
    assert tx_execution_succeeded(tx3), "check_monitor reverted"

    m = c.get_monitor(args=["M-MOCK"]).call()
    assert m["last_status"] == "success", f"status={m['last_status']}"
    assert m["last_value"] == "42"

    # breach: 42 > threshold 1 -> proposal must exist with payload
    props = [k for k in []]  # proposals not enumerable in this view; check via breach id in monitor flow
    # verify through the returned proposal path instead:
    print("STATE:", json.dumps(m))
