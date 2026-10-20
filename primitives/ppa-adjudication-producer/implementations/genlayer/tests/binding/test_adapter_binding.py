"""Direct-mode tests for the Adapter-side authority binding as consumed by
the PPA Adjudication Producer (adapter contract only — the direct VM loads a
single contract class per session; the full chain runs on GLSim in
tests/integration/).

Simulates what the Adapter must observe when the producer contract emits:
msg.sender == a registered adjudicator source address. MOCKED judgment data.

Run from the repository root:
    pytest primitives/ppa-adjudication-producer/implementations/genlayer/tests/binding/ -v
"""
from __future__ import annotations

import json

import pytest

ADAPTER = "primitives/ppa-receipt-adapter/implementations/genlayer/ppa_receipt_adapter.py"

FP = "sha256:producer-source-fingerprint-local"
PV = "TECH-V1"
PRODUCER_SRC = "0x" + "ab" * 20  # stand-in for the producer contract address


def _hex(a) -> str:
    if isinstance(a, (bytes, bytearray)):
        return "0x" + bytes(a).hex()
    h = a.as_hex if hasattr(a, "as_hex") else str(a)
    h = h.lower()
    return h if h.startswith("0x") else "0x" + h


def _receipt(did, status="ACCEPTED", fingerprint=FP, source=PRODUCER_SRC):
    return json.dumps({
        "decision_id": did, "source_contract": source,
        "authority_fingerprint": fingerprint, "question_hash": "sha256:q",
        "evidence_hash": "sha256:" + "e" * 64, "decision_status": status,
        "equivalence_mode": "comparative", "policy_version": PV,
        "created_at": "2020-01-01T00:00:00+00:00",
        "expires_at": "2099-01-01T00:00:00+00:00"})


def _adapter(direct_vm, direct_deploy, owner):
    direct_vm.sender = owner
    a = direct_deploy(ADAPTER)
    a.initialize(_hex(owner), "0x" + "cc" * 20)
    a.register_adjudicator(json.dumps({
        "source_contract": PRODUCER_SRC, "authority_fingerprint": FP,
        "policy_version": PV, "created_at": "2020-01-01T00:00:00+00:00",
        "expires_at": "2099-01-01T00:00:00+00:00"}))
    return a


def _as_producer(direct_vm, owner):
    """Point msg.sender at the registered producer source address: this is
    the condition the real emit sets on Bradbury."""
    direct_vm.sender = bytes.fromhex(PRODUCER_SRC[2:])


def test_producer_contract_sender_is_bound_and_actionable(direct_vm, direct_deploy, direct_alice):
    a = _adapter(direct_vm, direct_deploy, direct_alice)
    _as_producer(direct_vm, direct_alice)
    out = a.submit_decision_receipt(_receipt("D-OK"))
    assert out["origin_status"] == "BOUND"
    assert out["actionability"] == "ACTIONABLE"
    rec = a.get_receipt("D-OK")
    assert rec["source_contract"] == PRODUCER_SRC
    # the owner EOA submitting the same bytes is NOT the producer: origin fails
    direct_vm.sender = direct_alice
    out2 = a.submit_decision_receipt(_receipt("D-EOA"))
    assert out2["origin_status"] == "UNREGISTERED"
    assert out2["actionability"] == "NON_ACTIONABLE"


def test_wrong_fingerprint_from_bound_source_is_mismatch(direct_vm, direct_deploy, direct_alice):
    a = _adapter(direct_vm, direct_deploy, direct_alice)
    _as_producer(direct_vm, direct_alice)
    out = a.submit_decision_receipt(_receipt("D-FP", fingerprint="sha256:wrong"))
    assert out["origin_status"] == "AUTHORITY_MISMATCH"
    assert out["actionability"] == "NON_ACTIONABLE"


# REJECTED receipts carry the Adapter's generic non-actionable stamp
# (REJECTED_PROPOSAL_REPLAY); UNDETERMINED gets its own reason code.
@pytest.mark.parametrize("status,reason", [
    ("REJECTED", "REJECTED_PROPOSAL_REPLAY"),
    ("UNDETERMINED", "REJECTED_UNDETERMINED"),
])
def test_non_accepted_judgments_never_admit(direct_vm, direct_deploy, direct_alice,
                                            status, reason):
    a = _adapter(direct_vm, direct_deploy, direct_alice)
    _as_producer(direct_vm, direct_alice)
    did = "D-" + status
    out = a.submit_decision_receipt(_receipt(did, status=status))
    assert out["actionability"] == "NON_ACTIONABLE", out
    direct_vm.sender = direct_alice
    adm = a.admit_proposal(json.dumps({
        "proposal_id": "P-" + status, "decision_id": did, "account_id": "A1",
        "payment_id": "PAY1", "to": "0x" + "11" * 20, "amount": "100",
        "policy_version": PV}))
    assert adm["status"] == "REJECTED"
    assert adm["reason_code"] == reason


def test_accepted_admits_and_binds_evidence(direct_vm, direct_deploy, direct_alice):
    a = _adapter(direct_vm, direct_deploy, direct_alice)
    _as_producer(direct_vm, direct_alice)
    a.submit_decision_receipt(_receipt("D-AD"))
    direct_vm.sender = direct_alice
    adm = a.admit_proposal(json.dumps({
        "proposal_id": "P-AD", "decision_id": "D-AD", "account_id": "A1",
        "payment_id": "PAY-AD", "to": "0x" + "11" * 20, "amount": "100",
        "policy_version": PV}))
    assert adm["status"] == "ADMITTED", adm
    prop = a.get_proposal("P-AD")
    assert prop["evidence_hash"] == "sha256:" + "e" * 64
    assert prop["expires_at"] == "2099-01-01T00:00:00+00:00"
    # policy drift on admit is rejected even from an actionable receipt
    drift = a.admit_proposal(json.dumps({
        "proposal_id": "P-DRIFT", "decision_id": "D-AD", "account_id": "A1",
        "payment_id": "PAY2", "to": "0x" + "11" * 20, "amount": "100",
        "policy_version": "V2"}))
    assert drift["status"] == "REJECTED"
    assert drift["reason_code"] == "REJECTED_POLICY"


def test_receipt_replay_rejected(direct_vm, direct_deploy, direct_alice):
    a = _adapter(direct_vm, direct_deploy, direct_alice)
    _as_producer(direct_vm, direct_alice)
    a.submit_decision_receipt(_receipt("D-RP"))
    out = a.submit_decision_receipt(_receipt("D-RP"))
    assert out["reason_code"] == "REJECTED_PROPOSAL_REPLAY"
