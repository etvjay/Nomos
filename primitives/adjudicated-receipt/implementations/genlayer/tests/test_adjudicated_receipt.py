"""Direct-mode tests for the Adjudicated Receipt primitive v0.2.

Covers the deterministic envelope and the judgment surface with mocked
web/LLM: provisional acceptance, challenge window, finalization, exactly-once
settlement, defined expiry/cancellation rules, non-acceptance fail-closed
paths, and owner-only vs permissionless authority.

Run from the repository root:
    pytest primitives/adjudicated-receipt/implementations/genlayer/tests/ -v
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

CONTRACT = "primitives/adjudicated-receipt/implementations/genlayer/adjudicated_receipt.py"

OBJECT_REF = "0x9f6aa7364d20cf25f054ea83f3cb950317fd34b6"
EVIDENCE_URL = "https://vendor.example.com/api/deliveries/OBJ-77"
CLAUSE = "All 5 servers delivered, installed, and passing acceptance tests"
TTL = "86400"          # evidence TTL
WINDOW = "3600"        # challenge window


def _hex(a) -> str:
    if isinstance(a, (bytes, bytearray)):
        return "0x" + bytes(a).hex()
    h = a.as_hex if hasattr(a, "as_hex") else str(a)
    h = h.lower()
    return h if h.startswith("0x") else "0x" + h


def _setup(direct_vm, direct_deploy, alice, invoice_id="OBJ-77",
           ttl=TTL, window=WINDOW):
    direct_vm.sender = alice
    c = direct_deploy(CONTRACT)
    c.initialize(_hex(alice))
    c.register_release(
        invoice_id, OBJECT_REF, "2500", "USDC",
        EVIDENCE_URL,
        CLAUSE,
        ttl,
        window,
        "policy-v1",
        "vendor.example.com",
    )
    return c


def _mock_verdict(direct_vm, satisfied, verdict="delivered", confidence="high",
                  web_body="delivery manifest: 5 servers installed, acceptance passed"):
    direct_vm.clear_mocks()
    direct_vm.mock_web(r".*", {"status": 200, "body": web_body})
    direct_vm.mock_llm(r".*", json.dumps({
        "satisfied": satisfied, "verdict": verdict,
        "confidence": confidence, "reason": "mocked validator verdict",
    }))


def _warp(direct_vm, seconds):
    """Warp the contract-visible clock forward by `seconds`."""
    future = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    iso = future.isoformat()
    direct_vm.warp(iso)
    import sys as _sys
    gl_mod = _sys.modules.get("genlayer.gl")
    if gl_mod is not None and isinstance(getattr(gl_mod, "message_raw", None), dict):
        gl_mod.message_raw["datetime"] = iso


def _provisional(direct_vm, direct_deploy, alice, receipt_id="RC-1", invoice_id="OBJ-77"):
    c = _setup(direct_vm, direct_deploy, alice, invoice_id=invoice_id)
    _mock_verdict(direct_vm, True, "delivered", "high")
    r = c.adjudicate_object(invoice_id, receipt_id)
    assert r["status"] == "PROVISIONAL_ACCEPTED", r
    return c


# ------------------------------------------------ P0-1: provisional lifecycle

def test_provisional_acceptance_cannot_settle_until_finalized(
        direct_vm, direct_deploy, direct_alice):
    """An accepted quorum verdict is provisional: no release authority exists
    until the challenge window passes and finalize_release succeeds."""
    c = _provisional(direct_vm, direct_deploy, direct_alice)
    rec = c.get_receipt("RC-1")
    assert rec["status"] == "PROVISIONAL_ACCEPTED"
    assert rec["reason_code"] == "QUORUM_DELIVERED_HIGH_CONFIDENCE"
    assert rec["obligation_hash"] == c.get_object("OBJ-77")["obligation_hash"]

    with pytest.raises(ValueError, match="AdjudicatedReceipt: receipt is not FINAL_ACCEPTED"):
        c.settle_release("RC-1")

    with pytest.raises(ValueError, match="AdjudicatedReceipt: challenge window still open"):
        c.finalize_release("RC-1")


def test_full_lifecycle_provisional_final_settle_once(
        direct_vm, direct_deploy, direct_alice):
    c = _provisional(direct_vm, direct_deploy, direct_alice)

    _warp(direct_vm, 3601)   # past the 3600s challenge window
    fin = c.finalize_release("RC-1")
    assert fin["status"] == "FINAL_ACCEPTED"
    assert c.get_receipt("RC-1")["finalized_at"] != ""

    s = c.settle_release("RC-1")
    assert s["status"] == "SETTLED" and s["amount"] == "2500" and s["to"] == OBJECT_REF
    assert c.get_object("OBJ-77")["status"] == "SETTLED"
    assert c.get_release("pay-RC-1")["status"] == "SETTLED"
    assert c.get_release("pay-RC-1")["receipt_id"] == "RC-1"

    with pytest.raises(ValueError, match="AdjudicatedReceipt: receipt already consumed"):
        c.settle_release("RC-1")
    with pytest.raises(ValueError, match="AdjudicatedReceipt: release object not open"):
        c.adjudicate_object("OBJ-77", "RC-2")


def test_challenge_freezes_and_upheld_resolution_is_terminal(
        direct_vm, direct_deploy, direct_alice):
    """A challenge inside the window freezes the receipt; an upheld
    resolution is terminal non-acceptance with recorded bond forfeiture."""
    c = _provisional(direct_vm, direct_deploy, direct_alice)

    chal = c.challenge_release("RC-1", "500", "sha256:counter-evidence-1",
                               "vendor page shows 0 delivered")
    assert chal == "challenged"
    assert c.get_receipt("RC-1")["status"] == "CHALLENGED"
    ch = c.get_challenge("RC-1")
    assert ch["status"] == "OPEN" and ch["bond"] == "500"

    with pytest.raises(ValueError, match="AdjudicatedReceipt: receipt is not FINAL_ACCEPTED"):
        c.settle_release("RC-1")
    with pytest.raises(ValueError, match="AdjudicatedReceipt: receipt is not provisionally accepted"):
        c.finalize_release("RC-1")

    res = c.resolve_challenge("RC-1", "upheld")
    assert res["status"] == "CHALLENGED" and res["bond_disposition"] == "FORFEITED"
    assert c.get_challenge("RC-1")["resolution"] == "upheld"

    _warp(direct_vm, 3601)
    with pytest.raises(ValueError, match="AdjudicatedReceipt: receipt is not provisionally accepted"):
        c.finalize_release("RC-1")   # upheld challenge is terminal
    with pytest.raises(ValueError, match="AdjudicatedReceipt: receipt is not FINAL_ACCEPTED"):
        c.settle_release("RC-1")
    with pytest.raises(ValueError, match="AdjudicatedReceipt: challenge already resolved"):
        c.resolve_challenge("RC-1", "dismissed")


def test_dismissed_challenge_restores_provisional_then_finalizes(
        direct_vm, direct_deploy, direct_alice):
    c = _provisional(direct_vm, direct_deploy, direct_alice)
    c.challenge_release("RC-1", "100", "sha256:frivolous", "no merit")

    res = c.resolve_challenge("RC-1", "dismissed")
    assert res["status"] == "PROVISIONAL_ACCEPTED" and res["bond_disposition"] == "RETURNED"

    _warp(direct_vm, 3601)
    assert c.finalize_release("RC-1")["status"] == "FINAL_ACCEPTED"
    assert c.settle_release("RC-1")["status"] == "SETTLED"


def test_expired_evidence_finalizes_as_expired_never_settles(
        direct_vm, direct_deploy, direct_alice):
    """Defined expiry rule: past the evidence TTL, finalize records EXPIRED
    (a defined non-payment outcome, not an implicit refund), and no settle
    path exists afterwards."""
    c = _setup(direct_vm, direct_deploy, direct_alice, ttl="3600", window="60")
    _mock_verdict(direct_vm, True, "delivered", "high")
    c.adjudicate_object("OBJ-77", "RC-1")

    _warp(direct_vm, 3700)   # past evidence TTL (3600) AND challenge window (60)
    fin = c.finalize_release("RC-1")
    assert fin["success"] is False and fin["status"] == "EXPIRED"
    assert c.get_receipt("RC-1")["reason_code"] == "EVIDENCE_TTL_EXPIRED"

    with pytest.raises(ValueError, match="AdjudicatedReceipt: receipt is not FINAL_ACCEPTED"):
        c.settle_release("RC-1")
    # The object stays OPEN: the owner may re-register or cancel, but cannot
    # settle a stale receipt.
    assert c.get_object("OBJ-77")["status"] == "OPEN"


def test_cancel_release_is_owner_only_and_terminal(
        direct_vm, direct_deploy, direct_alice, direct_bob):
    c = _provisional(direct_vm, direct_deploy, direct_alice)

    direct_vm.sender = direct_bob
    with pytest.raises(ValueError, match="AdjudicatedReceipt: caller is not the account owner"):
        c.cancel_release("OBJ-77")

    direct_vm.sender = direct_alice
    res = c.cancel_release("OBJ-77")
    assert res["status"] == "CANCELLED"
    assert c.get_object("OBJ-77")["status"] == "CANCELLED"
    with pytest.raises(ValueError, match="AdjudicatedReceipt: release object not open"):
        c.adjudicate_object("OBJ-77", "RC-2")
    with pytest.raises(ValueError, match="AdjudicatedReceipt: receipt is not FINAL_ACCEPTED"):
        c.settle_release("RC-1")   # provisional receipt never settles

    # A FINAL receipt also cannot settle a cancelled object.
    c.register_release("OBJ-9", OBJECT_REF, "100", "USDC", EVIDENCE_URL, CLAUSE,
                       TTL, WINDOW, "policy-v1", "vendor.example.com")
    _mock_verdict(direct_vm, True, "delivered", "high")
    assert c.adjudicate_object("OBJ-9", "RC-9")["status"] == "PROVISIONAL_ACCEPTED"
    _warp(direct_vm, 3601)
    assert c.finalize_release("RC-9")["status"] == "FINAL_ACCEPTED"
    c.cancel_release("OBJ-9")
    with pytest.raises(ValueError, match="AdjudicatedReceipt: release object not open"):
        c.settle_release("RC-9")


def test_challenge_validation_and_window_closure(
        direct_vm, direct_deploy, direct_alice):
    c = _provisional(direct_vm, direct_deploy, direct_alice)
    with pytest.raises(ValueError, match="AdjudicatedReceipt: challenge reason required"):
        c.challenge_release("RC-1", "100", "sha256:x", "")
    with pytest.raises(ValueError, match="AdjudicatedReceipt: bond must be a positive uint-string"):
        c.challenge_release("RC-1", "0", "sha256:x", "r")
    with pytest.raises(ValueError, match="AdjudicatedReceipt: receipt not found"):
        c.challenge_release("NOPE", "100", "sha256:x", "r")

    _warp(direct_vm, 3601)   # window closed
    with pytest.raises(ValueError, match="AdjudicatedReceipt: challenge window closed"):
        c.challenge_release("RC-1", "100", "sha256:x", "late")


def test_resolve_challenge_is_owner_only(
        direct_vm, direct_deploy, direct_alice, direct_bob):
    c = _provisional(direct_vm, direct_deploy, direct_alice)
    c.challenge_release("RC-1", "100", "sha256:x", "r")
    direct_vm.sender = direct_bob
    with pytest.raises(ValueError, match="AdjudicatedReceipt: caller is not the account owner"):
        c.resolve_challenge("RC-1", "upheld")
    direct_vm.sender = direct_alice
    with pytest.raises(ValueError, match="AdjudicatedReceipt: unknown resolution"):
        c.resolve_challenge("RC-1", "coin_flip")


# ------------------------------------------------ judgment-surface non-approval

def test_rejected_receipt_can_never_settle(direct_vm, direct_deploy, direct_alice):
    c = _setup(direct_vm, direct_deploy, direct_alice)
    _mock_verdict(direct_vm, False, "not_delivered", "high",
                  web_body="delivery manifest: 0 of 5 servers received")

    r = c.adjudicate_object("OBJ-77", "RC-BAD")
    assert r["status"] == "REJECTED", r
    assert r["success"] is False
    assert c.get_receipt("RC-BAD")["reason_code"] == "EVIDENCE_NOT_SATISFYING"

    with pytest.raises(ValueError, match="AdjudicatedReceipt: receipt is not provisionally accepted"):
        c.finalize_release("RC-BAD")
    with pytest.raises(ValueError, match="AdjudicatedReceipt: receipt is not provisionally accepted"):
        c.challenge_release("RC-BAD", "100", "sha256:x", "r")
    assert c.get_object("OBJ-77")["status"] == "OPEN"

    _mock_verdict(direct_vm, True, "delivered", "high")
    assert c.adjudicate_object("OBJ-77", "RC-GOOD")["status"] == "PROVISIONAL_ACCEPTED"
    _warp(direct_vm, 3601)
    assert c.finalize_release("RC-GOOD")["status"] == "FINAL_ACCEPTED"
    assert c.settle_release("RC-GOOD")["status"] == "SETTLED"


def test_out_of_schema_model_output_is_undetermined(direct_vm, direct_deploy, direct_alice):
    c = _setup(direct_vm, direct_deploy, direct_alice)
    direct_vm.clear_mocks()
    direct_vm.mock_web(r".*", {"status": 200, "body": "some page"})
    direct_vm.mock_llm(r".*", json.dumps({"decision": "SURE_APPROVE"}))

    r = c.adjudicate_object("OBJ-77", "RC-WEIRD")
    assert r["status"] == "UNDETERMINED"
    assert r["reason"] == "consensus_unreachable"
    assert c.get_receipt("RC-WEIRD")["reason_code"] == "CONSENSUS_UNREACHABLE"
    with pytest.raises(ValueError, match="AdjudicatedReceipt: receipt is not provisionally accepted"):
        c.finalize_release("RC-WEIRD")
    with pytest.raises(ValueError, match="AdjudicatedReceipt: receipt is not FINAL_ACCEPTED"):
        c.settle_release("RC-WEIRD")


def test_partial_or_low_confidence_cannot_advance(direct_vm, direct_deploy, direct_alice):
    c = _setup(direct_vm, direct_deploy, direct_alice)

    _mock_verdict(direct_vm, True, "partial", "high",
                  web_body="3 of 5 servers installed, 2 pending")
    r = c.adjudicate_object("OBJ-77", "RC-PART")
    assert r["status"] == "UNDETERMINED_DELIVERY_UNCERTAIN"
    assert r["reason"] == "delivery_uncertain"
    assert c.get_receipt("RC-PART")["reason_code"] == "DELIVERY_UNCERTAIN"

    _mock_verdict(direct_vm, True, "delivered", "low", web_body="unclear manifest page")
    assert c.adjudicate_object("OBJ-77", "RC-LOW")["status"] == "UNDETERMINED_DELIVERY_UNCERTAIN"

    for rid in ("RC-PART", "RC-LOW"):
        with pytest.raises(ValueError, match="AdjudicatedReceipt: receipt is not provisionally accepted"):
            c.finalize_release(rid)
        with pytest.raises(ValueError, match="AdjudicatedReceipt: receipt is not FINAL_ACCEPTED"):
            c.settle_release(rid)
    assert c.get_object("OBJ-77")["status"] == "OPEN"

    _mock_verdict(direct_vm, True, "delivered", "high")
    assert c.adjudicate_object("OBJ-77", "RC-OK")["status"] == "PROVISIONAL_ACCEPTED"
    _warp(direct_vm, 3601)
    assert c.finalize_release("RC-OK")["status"] == "FINAL_ACCEPTED"
    assert c.settle_release("RC-OK")["status"] == "SETTLED"


def test_keeper_adjudicates_and_challenges_but_only_owner_finalizes_actions(
        direct_vm, direct_deploy, direct_alice, direct_bob):
    """Adjudication, challenge, and finalize are permissionless (liveness);
    registration, challenge resolution, settlement, and cancellation are
    owner-held."""
    direct_vm.sender = direct_alice
    c = direct_deploy(CONTRACT)
    c.initialize(_hex(direct_alice))
    c.register_release("OBJ-77", OBJECT_REF, "2500", "USDC", EVIDENCE_URL, CLAUSE,
                       TTL, WINDOW, "policy-v1", "vendor.example.com")

    direct_vm.sender = direct_bob
    _mock_verdict(direct_vm, True, "delivered", "high")
    assert c.adjudicate_object("OBJ-77", "RC-KEEPER")["status"] == "PROVISIONAL_ACCEPTED"
    # keeper may also challenge anyone's provisional receipt
    c.challenge_release("RC-KEEPER", "100", "sha256:x", "keeper challenge")
    # ...but cannot resolve, settle, register, or cancel.
    with pytest.raises(ValueError, match="AdjudicatedReceipt: caller is not the account owner"):
        c.resolve_challenge("RC-KEEPER", "upheld")
    with pytest.raises(ValueError, match="AdjudicatedReceipt: caller is not the account owner"):
        c.settle_release("RC-KEEPER")
    with pytest.raises(ValueError, match="AdjudicatedReceipt: caller is not the account owner"):
        c.register_release("OBJ-X", OBJECT_REF, "1", "USDC", EVIDENCE_URL, CLAUSE,
                           TTL, WINDOW, "policy-v1", "vendor.example.com")
    with pytest.raises(ValueError, match="AdjudicatedReceipt: caller is not the account owner"):
        c.cancel_release("OBJ-77")

    # Permissionless finalize after a dismissed challenge and passed window.
    direct_vm.sender = direct_alice
    c.resolve_challenge("RC-KEEPER", "dismissed")
    _warp(direct_vm, 3601)
    assert c.finalize_release("RC-KEEPER")["status"] == "FINAL_ACCEPTED"
    assert c.settle_release("RC-KEEPER")["status"] == "SETTLED"
    assert c.get_release("pay-RC-KEEPER")["invoice_id"] == "OBJ-77"


def test_registration_validation(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    c = direct_deploy(CONTRACT)
    c.initialize(_hex(direct_alice))
    base = ("OBJ-X", OBJECT_REF, "100", "USDC", EVIDENCE_URL, CLAUSE,
            TTL, WINDOW, "policy-v1", "vendor.example.com")
    c.register_release(*base)
    with pytest.raises(ValueError, match="AdjudicatedReceipt: invalid or duplicate object id"):
        c.register_release(*base)
    with pytest.raises(ValueError, match="AdjudicatedReceipt: policy version required"):
        c.register_release(*("OBJ-Y",) + base[1:8] + ("", "vendor.example.com"))
    with pytest.raises(ValueError, match="AdjudicatedReceipt: invalid challenge window"):
        c.register_release("OBJ-Z", OBJECT_REF, "100", "USDC", EVIDENCE_URL, CLAUSE,
                           TTL, "0", "policy-v1", "vendor.example.com")
    with pytest.raises(ValueError, match="AdjudicatedReceipt: invalid evidence TTL"):
        c.register_release("OBJ-W", OBJECT_REF, "100", "USDC", EVIDENCE_URL, CLAUSE,
                           "abc", WINDOW, "policy-v1", "vendor.example.com")
