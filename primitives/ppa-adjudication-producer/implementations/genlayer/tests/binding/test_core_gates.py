"""Direct-mode tests for Core-side independent gating of adapter-delivered
proposals (core contract only; full chain runs on GLSim in tests/integration).

Establishes the work-order property "Core still independently gates": even a
proposal that passed the Adapter (i.e. bound to an ACCEPTED producer receipt)
is re-checked by Core at execution time — caller registration, policy drift,
amount, capital — and money moves only through Core. MOCKED judgment payload
bytes (what the adapter's async emit carries).

Run from the repository root:
    pytest primitives/ppa-adjudication-producer/implementations/genlayer/tests/binding/test_core_gates.py -v
"""
from __future__ import annotations

import hashlib
import json

import pytest

CORE = "primitives/ppa-core/implementations/genlayer/ppa_core.py"
ADAPTER_PATH = ("primitives/ppa-receipt-adapter/implementations/genlayer/"
                "ppa_receipt_adapter.py")

PV = "TECH-V1"
RECIPIENT = "0x9f6aa7364d20cf25f054ea83f3cb950317fd34b6"
ACCT = "PROD-GATE-1"
RULES = json.dumps({"daily_limit": "1000", "per_tx_limit": "500",
                    "currency": "USDC", "policy_version": PV,
                    "allowlist": [RECIPIENT]})
# direct-VM deploy address: sha256(resolved path)[:20]
ADAPTER_ADDR = "0x" + hashlib.sha256(ADAPTER_PATH.encode()).hexdigest()[:40]


def _hex(a) -> str:
    if isinstance(a, (bytes, bytearray)):
        return "0x" + bytes(a).hex()
    h = a.as_hex if hasattr(a, "as_hex") else str(a)
    h = h.lower()
    return h if h.startswith("0x") else "0x" + h


def _proposal(pid="P1", did="D1", pay="PAY1", amount="100", to=RECIPIENT,
              policy=PV):
    return json.dumps({
        "proposal_id": pid, "decision_id": did, "payment_id": pay,
        "account_id": ACCT, "to": to, "amount": amount, "policy_version": policy,
        "evidence_hash": "sha256:" + "d" * 64,
        "expires_at": "2099-01-01T00:00:00+00:00"})


def _core(direct_vm, direct_deploy, owner):
    direct_vm.sender = owner
    c = direct_deploy(CORE)
    oh = _hex(owner)
    c.initialize(oh)
    c.create_account(ACCT, RULES)
    c.deposit(ACCT, "900")
    c.register_adapter(ADAPTER_ADDR)
    return c


def test_foreign_caller_is_refused(direct_vm, direct_deploy, direct_alice, direct_bob):
    c = _core(direct_vm, direct_deploy, direct_alice)
    direct_vm.sender = direct_bob
    out = c.execute_proposal(_proposal())
    assert out["status"] == "REJECTED"
    assert out["reason_code"] == "REJECTED_CALLER_NOT_REGISTERED_ADAPTER"
    assert c.get_account(ACCT)["balance"] == "900"


def test_registered_adapter_happy_path_settles_via_core_only(
        direct_vm, direct_deploy, direct_alice):
    c = _core(direct_vm, direct_deploy, direct_alice)
    direct_vm.sender = bytes.fromhex(ADAPTER_ADDR[2:])
    out = c.execute_proposal(_proposal())
    assert out["status"] == "EXECUTED", out
    pay = c.get_payment("PAY1")
    assert pay["status"] == "SETTLED" and pay["actor"] == "adapter:" + ADAPTER_ADDR[2:]
    acct = c.get_account(ACCT)
    assert acct["balance"] == "800" and acct["daily_spent"] == "100"
    # replay: same consequence returned, balance unchanged (exactly-once)
    again = c.execute_proposal(_proposal())
    assert again["status"] == "EXECUTED" and again["reason_code"] == "EXECUTED"
    assert c.get_account(ACCT)["balance"] == "800"


def test_amount_widening_refused_despite_adapter_caller(
        direct_vm, direct_deploy, direct_alice):
    """A proposal presenting a 99999 amount (over per_tx) is refused by Core
    even when it arrives from the registered adapter caller."""
    c = _core(direct_vm, direct_deploy, direct_alice)
    direct_vm.sender = bytes.fromhex(ADAPTER_ADDR[2:])
    out = c.execute_proposal(_proposal(pid="P-BIG", pay="PAY-BIG", amount="99999"))
    assert out["status"] == "REJECTED"
    assert out["reason_code"] == "REJECTED_AMOUNT"
    assert out["detail"] == "PER_TX_LIMIT"
    assert c.get_account(ACCT)["balance"] == "900"


def test_capital_gate_refused(direct_vm, direct_deploy, direct_alice):
    c = _core(direct_vm, direct_deploy, direct_alice)
    owner_hex = _hex(direct_alice)
    direct_vm.sender = direct_alice
    c.withdraw(ACCT, "600")  # uncommitted balance now 300
    direct_vm.sender = bytes.fromhex(ADAPTER_ADDR[2:])
    out = c.execute_proposal(_proposal(pid="P-CAP", pay="PAY-CAP", amount="400"))
    assert out["status"] == "REJECTED"
    assert out["reason_code"] == "REJECTED_CAPITAL"
    assert out["detail"] == "INSUFFICIENT_UNCOMMITTED"


def test_policy_drift_and_recipient_gates(direct_vm, direct_deploy, direct_alice):
    c = _core(direct_vm, direct_deploy, direct_alice)
    ad = bytes.fromhex(ADAPTER_ADDR[2:])
    direct_vm.sender = ad
    drift = c.execute_proposal(_proposal(pid="P-POL", pay="PAY-POL", policy="V2"))
    assert drift["reason_code"] == "REJECTED_POLICY"
    assert drift["detail"] == "POLICY_VERSION_DRIFT"
    off = c.execute_proposal(_proposal(pid="P-TO", pay="PAY-TO",
                                       to="0x" + "aa" * 20))
    assert off["reason_code"] == "REJECTED_RECIPIENT"
    assert off["detail"] == "NOT_ALLOWLISTED"
    assert c.get_account(ACCT)["balance"] == "900"
