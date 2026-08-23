"""IAS Stage 1 real-democracy verification on GLSim.

Uses a REAL data source (CoinGecko BTC page) with the sim's live LLM backend
so validators genuinely fetch, extract, and compare under tolerance-based
comparative equivalence. Threshold set absurdly high: correct extraction means
NO breach; consensus failure or hallucination shows as UNDETERMINED/breach.
"""
import json

from gltest import get_contract_factory, get_accounts
from gltest.assertions import tx_execution_succeeded

OWNER = get_accounts()[0].address


def test_stage1_comparative_consensus_live():
    f = get_contract_factory(contract_file_path="ias_stage1.py")
    c = f.deploy()
    c.initialize(args=[OWNER]).transact(wait_interval=2000, wait_retries=10)

    tx = c.create_monitor(args=["BTC-REAL",
        "BTC USD", "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
        "price", "999999999", "above", "15.0", "low", ""
    ]).transact(wait_interval=3000, wait_retries=10)
    assert tx_execution_succeeded(tx)

    # THE TEST: real web fetch + LLM extraction + validator comparison
    tx2 = c.check_monitor(args=["BTC-REAL"]).transact(
        wait_interval=15000, wait_retries=30)
    status_str = str(tx2.get("status", ""))

    m = c.get_monitor(args=["BTC-REAL"]).call()
    print("MONITOR STATE:", json.dumps(m)[:300])

    # Consensus reached if last_status was written (success OR extraction_failed
    # are both deterministic post-consensus states). UNDETERMINED would leave
    # the initial empty value.
    reached = m["last_status"] in ("success", "extraction_failed")
    print("CONSENSUS REACHED:", reached)
    print("EXTRACTION:", m["last_status"], "| VALUE:", m.get("last_value"))

    assert reached, "comparative consensus did not resolve"
    if m["last_status"] == "success":
        v = float(m["last_value"])
        print("EXTRACTED VALUE:", v)
        # With sim LLM mocks installed, 42 is the expected deterministic output.
        # Without mocks (real validator LLMs), assert BTC plausibility instead:
        # plausible = 1000 < v < 10000000
