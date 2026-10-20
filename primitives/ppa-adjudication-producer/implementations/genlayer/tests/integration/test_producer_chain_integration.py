"""GLSim chain proof for the PPA Adjudication Producer v0.1.

Runs producer, Adapter, and Core as three real deployed contracts on the
consensus execution path (gltest against local GLSim). The producer's delivery
is its OWN cross-contract emit (gl.get_contract_at(...).emit(on="accepted")):
the Adapter observes msg.sender == the producer CONTRACT address, not the
owner EOA. Web/LLM are deterministic sim mocks so the judgment is reproducible.

Environment findings (2026-10-18):
- This glsim build's sim_installMocks APPENDS mock patterns without clearing
  (first-match wins), so mocks cannot be switched mid-session. All phase mocks
  are installed up front and disambiguated by distinct evidence URLs and
  distinct clause markers embedded in the prompt.
- GLSim here runs leader_only: the validator_fn path is NOT exercised locally.
  Real validator quorum + equivalence votes are proven on Bradbury.
- Clock is frozen at sim start; TTLs are long, so expiry never triggers.

Run (GLSim on :4000, from the repository root):
    gltest primitives/ppa-adjudication-producer/implementations/genlayer/tests/integration/ -v -s
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from gltest import get_contract_factory, get_accounts
from gltest.assertions import tx_execution_succeeded
from gltest_cli.config.general import get_general_config

ROOT = Path(__file__).resolve().parents[6]
PRODUCER_PATH = str(ROOT / "primitives/ppa-adjudication-producer/implementations/genlayer/ppa_adjudication_producer.py")
ADAPTER_PATH = str(ROOT / "primitives/ppa-receipt-adapter/implementations/genlayer/ppa_receipt_adapter.py")
CORE_PATH = str(ROOT / "primitives/ppa-core/implementations/genlayer/ppa_core.py")

FP = "sha256:producer-source-fingerprint-local"
PV = "TECH-V1"
URL_A = "https://feed.example.com/alpha/ORD-42"
URL_B = "https://feed.example.com/bravo/ORD-42"
URL_C = "https://feed.example.com/charlie/ORD-42"
CLAUSE_A = ("MARKER-ALPHA: the shipment status field equals delivered and the "
            "package count is 3")
CLAUSE_B = ("MARKER-BRAVO: the shipment status field equals delivered and the "
            "package count is 3")
CLAUSE_C = ("MARKER-CHARLIE: the shipment status field equals delivered and "
            "the package count is 3")
BODY_OK = '{"order": "ORD-42", "status": "delivered", "packages": 3}'
BODY_NEG = '{"order": "ORD-42", "status": "cancelled", "packages": 0}'
ACCT = "PROD-CHAIN-1"
RECIPIENT = "0x9f6aa7364d20cf25f054ea83f3cb950317fd34b6"
RULES = json.dumps({"daily_limit": "1000", "per_tx_limit": "500",
                    "currency": "USDC", "policy_version": PV,
                    "allowlist": [RECIPIENT]})

W, R = 10000, 50


def _install_all_mocks():
    """One up-front install: glsim cannot switch mocks mid-session."""
    endpoint = get_general_config().get_rpc_url()
    body = json.dumps({
        "jsonrpc": "2.0", "method": "sim_installMocks", "id": 1,
        "params": {
            "llm_mocks": {
                "MARKER-ALPHA": {"satisfied": True, "verdict": "delivered",
                                 "confidence": "high", "reason": "sim: delivered"},
                "MARKER-BRAVO": {"satisfied": False, "verdict": "not_delivered",
                                 "confidence": "high", "reason": "sim: cancelled"},
                "MARKER-CHARLIE": {"satisfied": False, "verdict": "ambiguous",
                                   "confidence": "low", "reason": "sim: unclear"},
            },
            "web_mocks": {
                "feed\\.example\\.com/alpha": {"status": 200, "body": BODY_OK},
                "feed\\.example\\.com/bravo": {"status": 200, "body": BODY_NEG},
                "feed\\.example\\.com/charlie": {"status": 500, "body": ""},
            },
            "strict": False,
        }}).encode()
    req = urllib.request.Request(endpoint, data=body,
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


def _tx(method):
    receipt = method.transact(wait_interval=W, wait_retries=R)
    return receipt, tx_execution_succeeded(receipt)


def _poll_view(method, tries=20):
    """Read a view until it returns (covers async emit landing)."""
    last = None
    for _ in range(tries):
        try:
            return method.call()
        except Exception as e:
            last = str(e)[:120]
            time.sleep(0.5)
    raise AssertionError(f"view never resolved: {last}")


def _assert_no_proposal(adapter, pid):
    import pytest as _pt
    with _pt.raises(AssertionError):
        _poll_view(adapter.get_proposal(args=[pid]), tries=2)


def _title(n, text):
    print("\n" + "=" * 72 + f"\nSTEP {n}  {text}\n" + "=" * 72)


def _proposal(pid, did, pay):
    return json.dumps({
        "proposal_id": pid, "decision_id": did, "account_id": ACCT,
        "payment_id": pay, "to": RECIPIENT, "amount": "100",
        "policy_version": PV})


def test_producer_chain_binding_and_settlement():
    accounts = get_accounts()
    OWNER, KEEPER = accounts[0], accounts[1]

    _title(0, "Mocks installed up front (per-phase URL + clause markers)")
    print("  ", _install_all_mocks())

    _title(1, "Deploy Core, Adapter, Producer (three contracts, real addresses)")
    core = get_contract_factory(contract_file_path=CORE_PATH).deploy(account=OWNER)
    adapter = get_contract_factory(contract_file_path=ADAPTER_PATH).deploy(account=OWNER)
    producer = get_contract_factory(contract_file_path=PRODUCER_PATH).deploy(account=OWNER)
    print(f"  core     {core.address}\n  adapter  {adapter.address}\n  producer {producer.address}")

    _title(2, "Bootstrap: account + adapter registration; adjudicator bound to PRODUCER CONTRACT")
    pf = get_contract_factory(contract_file_path=PRODUCER_PATH)
    producer_k = pf.build_contract(contract_address=producer.address, account=KEEPER)
    for m in [
        core.initialize(args=[OWNER.address]),
        core.create_account(args=[ACCT, RULES]),
        core.deposit(args=[ACCT, "900"]),
        core.register_adapter(args=[adapter.address]),
        adapter.initialize(args=[OWNER.address, core.address]),
        adapter.register_adjudicator(args=[json.dumps({
            "source_contract": producer.address, "authority_fingerprint": FP,
            "policy_version": PV, "created_at": "2020-01-01T00:00:00+00:00",
            "expires_at": "2099-01-01T00:00:00+00:00"})]),
        producer.initialize(args=[OWNER.address, adapter.address, FP, PV]),
        producer.register_question(args=["Q-A", URL_A, CLAUSE_A, "86400"]),
        producer.register_question(args=["Q-B", URL_B, CLAUSE_B, "86400"]),
        producer.register_question(args=["Q-C", URL_C, CLAUSE_C, "86400"]),
    ]:
        r, ok = _tx(m)
        assert ok, (m, r)

    _title(3, "Keeper triggers producer adjudication on positive evidence (permissionless)")
    r, ok = _tx(producer_k.adjudicate(args=["D-CHAIN", "Q-A"]))
    assert ok, r
    rec = _poll_view(producer.get_receipt(args=["D-CHAIN"]))
    print(f"  producer receipt: status={rec['status']} submit={rec['adapter_submit']} "
          f"bytes={rec['observation']['bytes']}")
    assert rec["status"] == "ACCEPTED"
    assert rec["adapter_submit"] == "QUEUED"
    eh = rec["receipt"]["evidence_hash"]
    assert eh.startswith("sha256:") and len(eh) == 71 and eh != "sha256:placeholder"
    assert rec["observation"]["bytes"] > 0, "evidence observation must be real content"

    _title(4, "Adapter readback: sender observed == producer CONTRACT, origin BOUND")
    ar = _poll_view(adapter.get_receipt(args=["D-CHAIN"]))
    print(f"  adapter receipt: origin={ar['origin_status']} action={ar['actionability']} "
          f"source={ar['source_contract'][:14]}...")
    assert ar["origin_status"] == "BOUND"
    assert ar["actionability"] == "ACTIONABLE"
    assert ar["source_contract"].lower().removeprefix("0x") == \
        producer.address.lower().removeprefix("0x")
    assert ar["authority_fingerprint"] == FP
    assert ar["evidence_hash"] == eh, "adapter binds the producer's content hash"

    _title(5, "Admit + dispatch; Core re-gates and settles (async emit)")
    r, ok = _tx(adapter.admit_proposal(args=[_proposal("P-CHAIN", "D-CHAIN", "PAY-CHAIN")]))
    assert ok, r
    assert adapter.get_proposal(args=["P-CHAIN"]).call()["status"] == "ADMITTED"
    r, ok = _tx(adapter.dispatch_proposal(args=["P-CHAIN"]))
    assert ok, r
    cons = _poll_view(core.get_consequence(args=["P-CHAIN"]))
    print(f"  core consequence: status={cons['status']} reason={cons['reason_code']} "
          f"adapter_caller={cons['adapter_caller'][:14]}...")
    assert cons["status"] == "EXECUTED"
    pay = core.get_payment(args=["PAY-CHAIN"]).call()
    assert pay["status"] == "SETTLED" and pay["actor"] == \
        "adapter:" + adapter.address.lower().removeprefix("0x")
    acct = core.get_account(args=[ACCT]).call()
    print(f"  account: balance={acct['balance']} daily_spent={acct['daily_spent']}")
    assert acct["balance"] == "800" and acct["daily_spent"] == "100"

    _title(6, "Owner EOA CANNOT forge producer delivery: direct submit is UNREGISTERED")
    crafted = dict(rec["receipt"])
    crafted["decision_id"] = "D-SPOOF"
    r, ok = _tx(adapter.submit_decision_receipt(args=[json.dumps(crafted)]))
    assert ok, r
    spoof = adapter.get_receipt(args=["D-SPOOF"]).call()
    print(f"  spoof receipt: origin={spoof['origin_status']} action={spoof['actionability']}")
    assert spoof["origin_status"] == "UNREGISTERED"
    assert spoof["actionability"] == "NON_ACTIONABLE"
    r, ok = _tx(adapter.admit_proposal(args=[_proposal("P-SPOOF", "D-SPOOF", "PAY-SPOOF")]))
    assert ok
    _assert_no_proposal(adapter, "P-SPOOF")
    print("  spoof admit: no proposal created")

    _title(7, "Negative evidence -> producer REJECTED -> non-actionable, never admits")
    r, ok = _tx(producer_k.adjudicate(args=["D-NEG", "Q-B"]))
    assert ok, r
    neg = _poll_view(producer.get_receipt(args=["D-NEG"]))
    assert neg["status"] == "REJECTED"
    assert neg["receipt"]["evidence_hash"] != eh, "different evidence => different hash"
    aneg = _poll_view(adapter.get_receipt(args=["D-NEG"]))
    assert aneg["origin_status"] == "BOUND"
    assert aneg["actionability"] == "NON_ACTIONABLE"
    r, ok = _tx(adapter.admit_proposal(args=[_proposal("P-NEG", "D-NEG", "PAY-NEG")]))
    assert ok
    _assert_no_proposal(adapter, "P-NEG")
    print("  REJECTED judgment: BOUND origin, refused at admit")

    _title(8, "Evidence unavailable/ambiguous -> UNDETERMINED, fail-closed end to end")
    r, ok = _tx(producer_k.adjudicate(args=["D-UND", "Q-C"]))
    assert ok, r
    und = _poll_view(producer.get_receipt(args=["D-UND"]))
    print(f"  undetermined: status={und['status']} reason={und['observation']['reason']}")
    assert und["status"] == "UNDETERMINED"
    aund = _poll_view(adapter.get_receipt(args=["D-UND"]))
    assert aund["actionability"] == "NON_ACTIONABLE"
    assert aund["fail_reason"] == "REJECTED_UNDETERMINED"
    r, ok = _tx(adapter.admit_proposal(args=[_proposal("P-UND", "D-UND", "PAY-UND")]))
    assert ok
    _assert_no_proposal(adapter, "P-UND")

    _title(9, "Final state: exactly one settlement, from the producer-bound ACCEPTED path")
    acct = core.get_account(args=[ACCT]).call()
    assert acct["balance"] == "800", acct
    print(f"  final balance={acct['balance']} daily_spent={acct['daily_spent']} "
          f"(only D-CHAIN ever moved value)")
