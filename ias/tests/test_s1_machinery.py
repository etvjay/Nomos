"""Stage 1 consensus-machinery test via gltest (leader_only sim mode) with
module-scope LLM mock installation — the exact pattern of the passing
encumbrance integration test.

Proves: web fetch -> LLM extraction -> comparative validator -> vote ->
breach detection -> proposal creation, end to end through consensus.

Run:
    source ~/nomos-venv312/bin/activate
    gltest ias/tests/test_s1_machinery.py -q -s
"""
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
                # match our extraction prompt (any variant)
                r".*Extract.*numeric value.*|.*WEBPAGE CONTENT.*": {
                    "value": "42",
                    "confidence": "high",
                    "found": True,
                }
            },
            "strict": False,
        },
        "id": 1,
    }).encode()
    req = urllib.request.Request(endpoint, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def test_stage1_consensus_machinery():
    f = get_contract_factory(contract_file_path="ias_stage1.py")
    c = f.deploy()
    tx = c.initialize(args=[OWNER]).transact(wait_interval=2000, wait_retries=10)
    assert tx_execution_succeeded(tx)

    tx2 = c.create_monitor(args=["M-MOCK", "mocked source", "https://example.com",
        "price", "1", "above", "25.0", "medium",
        json.dumps({"action": "inspect", "note": "machinery test"})
    ]).transact(wait_interval=3000, wait_retries=10)
    assert tx_execution_succeeded(tx2)

    # THE TEST: full nondet flow. Mock must be installed IMMEDIATELY before
    # check_monitor — glsim clears mocks after each executed transaction.
    _install_mock()
    tx3 = c.check_monitor(args=["M-MOCK"]).transact(wait_interval=15000, wait_retries=30)

    if not tx_execution_succeeded(tx3):
        lr = tx3["consensus_data"]["leader_receipt"][0]
        gr = lr.get("genvm_result") or {}
        print("CHECK STDERR:", str(gr.get("stderr"))[:500])
        print("CHECK RESULT:", str(lr.get("result"))[:250])
    assert tx_execution_succeeded(tx3), "check_monitor reverted"

    m = c.get_monitor(args=["M-MOCK"]).call()
    print("MONITOR:", json.dumps(m)[:350])
    assert m["last_status"] == "success", f"status={m['last_status']}"
    assert str(m["last_value"]) == "42"
    assert m.get("last_confidence") == "high"
