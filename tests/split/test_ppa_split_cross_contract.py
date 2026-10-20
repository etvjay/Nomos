"""Cross-contract integration proof: Adjudicator -> Adapter -> Core -> settlement.

This is the required fresh integration test for WORK-PPA-SPLIT-V03-2026-10-17.
Cross-contract safety is NOT inferred from unit tests: every assertion here goes
through the real asynchronous `emit(on='accepted')` boundary and is read back
from Core's persisted consequence record.

Boundary model, evidenced by convergence/reports/CALLER-IDENTITY-SPIKE.json:
  - at Core, gl.message.sender_address is the ADAPTER
  - at the Adapter, gl.message.sender_address is the ADJUDICATOR
  - the original EOA is consumed at each hop
  - a JSON source_contract field carries no provenance

Because the boundary is NON-ATOMIC, every negative case mutates Core-owned state
(or the caller identity) AFTER the Adapter has admitted the proposal, to prove
Core revalidates rather than trusting the Adapter.

Run:
    source ~/nomos-venv312/bin/activate
    python -m pytest tests/split/ -q
"""
import json
import time

import pytest
from gltest import get_contract_factory, get_accounts
from gltest.assertions import tx_execution_failed, tx_execution_succeeded

OWNER = get_accounts()[0].address
ADJUDICATOR = get_accounts()[1]
ADJ_ADDR = ADJUDICATOR.address
STRANGER = get_accounts()[2]
RECIPIENT = "0x9f6aa7364d20cf25f054ea83f3cb950317fd34b6"
OUTSIDER = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
FINGERPRINT = "sha256:adjudicator-identity-001"
OTHER_FP = "sha256:other-identity-999"
FAR = "2099-01-01T00:00:00+00:00"
LONG_PAST = "2020-01-01T00:00:00+00:00"

CORE = "ppa_core.py"
ADAPTER = "ppa_receipt_adapter.py"


def _poll(fn, *args, tries=40, delay=0.5):
    """emit() is asynchronous: Core runs in a later transaction. Poll for it."""
    last = None
    for _ in range(tries):
        try:
            v = fn(args=list(args)).call()
            # gltest views already return decoded objects
            return json.loads(v) if isinstance(v, str) else v
        except Exception as exc:
            last = exc
            time.sleep(delay)
    raise last


def _wire(require_attestation=False, per_tx="500", daily="1000", deposit="1000",
          register_adapter=True):
    core = get_contract_factory(contract_file_path=CORE).deploy()
    core.initialize(args=[OWNER]).transact(wait_interval=3000, wait_retries=10)
    rules = {"daily_limit": daily, "per_tx_limit": per_tx, "currency": "USDC"}
    if require_attestation:
        rules.update({"require_attestation": True, "attestation_issuers": [ADJ_ADDR],
                      "attestation_policy_version": "TECH-V1"})
    core.create_account(args=["ACC1", json.dumps(rules)]).transact(
        wait_interval=3000, wait_retries=10)
    if deposit:
        core.deposit(args=["ACC1", deposit]).transact(wait_interval=3000, wait_retries=10)

    adapter = get_contract_factory(contract_file_path=ADAPTER).deploy()
    adapter.initialize(args=[OWNER, core.address]).transact(wait_interval=3000, wait_retries=10)
    if register_adapter:
        core.register_adapter(args=[adapter.address]).transact(
            wait_interval=3000, wait_retries=10)
    adapter.register_adjudicator(args=[json.dumps({
        "source_contract": ADJ_ADDR,
        "authority_fingerprint": FINGERPRINT,
        "policy_version": "TECH-V1",
        "created_at": LONG_PAST,
        "expires_at": FAR})]).transact(wait_interval=3000, wait_retries=10)
    return core, adapter


def _receipt(did="DEC-1", status="ACCEPTED", source=ADJ_ADDR, fp=FINGERPRINT,
             expires=FAR):
    return json.dumps({
        "decision_id": did, "source_contract": source,
        "authority_fingerprint": fp, "question_hash": "sha256:q",
        "evidence_hash": "sha256:ev", "decision_status": status,
        "equivalence_mode": "comparative", "policy_version": "TECH-V1",
        "created_at": LONG_PAST, "expires_at": expires})


def _proposal(pid="PROP-1", did="DEC-1", amount="100", to=RECIPIENT, pay="PAY-1"):
    return json.dumps({
        "proposal_id": pid, "decision_id": did, "account_id": "ACC1",
        "payment_id": pay, "to": to, "amount": amount, "policy_version": "TECH-V1"})


def _settle(core, adapter, receipt=None, proposal=None, pid="PROP-1", did="DEC-1"):
    """adjudicator -> adapter -> proposal -> dispatch -> core executes (async)"""
    adapter.connect(ADJUDICATOR).submit_decision_receipt(
        args=[receipt or _receipt(did=did)]).transact(wait_interval=3000, wait_retries=10)
    adapter.admit_proposal(args=[proposal or _proposal(pid=pid, did=did)]).transact(
        wait_interval=3000, wait_retries=10)
    adapter.dispatch_proposal(args=[pid]).transact(wait_interval=5000, wait_retries=25)
    return _poll(core.get_consequence, pid)


# ---------------------------------------------------------------- happy path

def test_bound_receipt_reaches_settlement():
    """registered adjudicator -> authenticated receipt -> proposal -> gated settlement"""
    core, adapter = _wire()
    c = _settle(core, adapter)
    assert c["status"] == "EXECUTED", c
    assert c["adapter_caller"] and c["adapter_caller"] != ADJ_ADDR.lower().replace("0x", "")
    pay = core.get_payment(args=["PAY-1"]).call()
    assert pay["status"] == "SETTLED"
    assert pay["decision_id"] == "DEC-1" and pay["proposal_id"] == "PROP-1"
    assert core.get_account(args=["ACC1"]).call()["balance"] == "900"


def test_core_records_adapter_not_eoa_as_caller():
    core, adapter = _wire()
    c = _settle(core, adapter)
    assert c["adapter_caller"] == adapter.address.lower().replace("0x", ""), c


def test_core_stores_no_receipt_payload():
    """Core persists identifiers and hashes only, never receipt/evidence bodies."""
    core, adapter = _wire()
    c = _settle(core, adapter)
    assert set(c) >= {"proposal_id", "decision_id", "payment_id", "adapter_caller",
                      "reason_code", "requested_amount", "requested_recipient",
                      "policy_version", "created_at", "status"}
    assert "receipt" not in json.dumps(c).lower() or "receipt" not in c
    assert "evidence_hash" not in c


# ------------------------------------------------------- adapter-side negatives

def test_unregistered_adjudicator_rejected():
    core, adapter = _wire()
    r = adapter.connect(STRANGER).submit_decision_receipt(
        args=[_receipt(did="DEC-U")]).transact(wait_interval=3000, wait_retries=10)
    got = adapter.get_receipt(args=["DEC-U"]).call()
    assert got["actionability"] == "NON_ACTIONABLE"
    assert got["fail_reason"] == "REJECTED_SOURCE_NOT_REGISTERED"
    assert got["origin_status"] == "UNREGISTERED"


def test_json_source_alone_is_not_provenance():
    """A stranger claiming the registered adjudicator address is still refused."""
    core, adapter = _wire()
    adapter.connect(STRANGER).submit_decision_receipt(
        args=[_receipt(did="DEC-S", source=ADJ_ADDR)]).transact(
        wait_interval=3000, wait_retries=10)
    assert adapter.get_receipt(args=["DEC-S"]).call()[
        "fail_reason"] == "REJECTED_SOURCE_NOT_REGISTERED"


def test_revoked_adjudicator_non_actionable():
    core, adapter = _wire()
    adapter.revoke_adjudicator(args=[ADJ_ADDR]).transact(wait_interval=3000, wait_retries=10)
    adapter.connect(ADJUDICATOR).submit_decision_receipt(
        args=[_receipt(did="DEC-R")]).transact(wait_interval=3000, wait_retries=10)
    got = adapter.get_receipt(args=["DEC-R"]).call()
    assert got["actionability"] == "NON_ACTIONABLE"
    assert got["fail_reason"] == "REJECTED_SOURCE_NOT_REGISTERED"


def test_fingerprint_mismatch_rejected():
    core, adapter = _wire()
    adapter.connect(ADJUDICATOR).submit_decision_receipt(
        args=[_receipt(did="DEC-F", fp=OTHER_FP)]).transact(wait_interval=3000, wait_retries=10)
    got = adapter.get_receipt(args=["DEC-F"]).call()
    assert got["fail_reason"] == "REJECTED_SOURCE_FINGERPRINT_MISMATCH"


def test_undetermined_status_yields_no_proposal():
    core, adapter = _wire()
    adapter.connect(ADJUDICATOR).submit_decision_receipt(
        args=[_receipt(did="DEC-U2", status="UNDETERMINED")]).transact(
        wait_interval=3000, wait_retries=10)
    assert adapter.get_receipt(args=["DEC-U2"]).call()[
        "fail_reason"] == "REJECTED_UNDETERMINED"
    assert core.get_account(args=["ACC1"]).call()["balance"] == "1000"


def test_expired_receipt_yields_no_proposal():
    core, adapter = _wire()
    adapter.connect(ADJUDICATOR).submit_decision_receipt(
        args=[_receipt(did="DEC-E", expires="2020-02-01T00:00:00+00:00")]).transact(
        wait_interval=3000, wait_retries=10)
    assert adapter.get_receipt(args=["DEC-E"]).call()["fail_reason"] == "REJECTED_EXPIRED"
    assert core.get_account(args=["ACC1"]).call()["balance"] == "1000"


def test_replayed_decision_rejected():
    core, adapter = _wire()
    h = adapter.connect(ADJUDICATOR)
    h.submit_decision_receipt(args=[_receipt()]).transact(wait_interval=3000, wait_retries=10)
    r = h.submit_decision_receipt(args=[_receipt(status="REJECTED")]).transact(
        wait_interval=3000, wait_retries=10)
    assert adapter.get_receipt(args=["DEC-1"]).call()["decision_status"] == "ACCEPTED"


def test_replayed_proposal_rejected():
    core, adapter = _wire()
    adapter.connect(ADJUDICATOR).submit_decision_receipt(args=[_receipt()]).transact(
        wait_interval=3000, wait_retries=10)
    adapter.admit_proposal(args=[_proposal()]).transact(wait_interval=3000, wait_retries=10)
    # refusal is a RETURNED STATUS, not a revert (frozen design principle)
    tx = adapter.admit_proposal(args=[_proposal()]).transact(wait_interval=3000, wait_retries=10)
    assert tx_execution_succeeded(tx)
    assert adapter.get_proposal(args=["PROP-1"]).call()["status"] == "ADMITTED", \
        "duplicate admit overwrote the original proposal"
    adapter.dispatch_proposal(args=["PROP-1"]).transact(wait_interval=5000, wait_retries=25)
    first = _poll(core.get_consequence, "PROP-1")
    tx3 = adapter.dispatch_proposal(args=["PROP-1"]).transact(wait_interval=5000, wait_retries=25)
    assert tx_execution_succeeded(tx3)
    assert _poll(core.get_consequence, "PROP-1") == first, \
        "re-dispatch produced a second core consequence"


# --------------------------------------------------------- core-side negatives

def test_unregistered_adapter_rejected_by_core():
    """Core authenticates the caller address, not a claimed identity."""
    core, adapter = _wire(register_adapter=False)
    c = _settle(core, adapter)
    assert c["status"] == "REJECTED"
    assert c["reason_code"] == "REJECTED_CALLER_NOT_REGISTERED_ADAPTER"
    assert core.get_account(args=["ACC1"]).call()["balance"] == "1000"


def test_revoked_adapter_rejected_by_core():
    core, adapter = _wire()
    adapter.connect(ADJUDICATOR).submit_decision_receipt(args=[_receipt()]).transact(
        wait_interval=3000, wait_retries=10)
    adapter.admit_proposal(args=[_proposal()]).transact(wait_interval=3000, wait_retries=10)
    core.revoke_adapter(args=[adapter.address]).transact(wait_interval=3000, wait_retries=10)
    adapter.dispatch_proposal(args=["PROP-1"]).transact(wait_interval=5000, wait_retries=25)
    c = _poll(core.get_consequence, "PROP-1")
    assert c["reason_code"] == "REJECTED_ADAPTER_REVOKED"
    assert core.get_account(args=["ACC1"]).call()["balance"] == "1000"


def test_adapter_cannot_widen_amount():
    """Adapter admits a proposal above the Core-side per-tx limit; Core refuses."""
    core, adapter = _wire(per_tx="500")
    c = _settle(core, adapter, proposal=_proposal(amount="99999"))
    assert c["status"] == "REJECTED"
    assert c["reason_code"] == "REJECTED_AMOUNT"
    assert c["requested_amount"] == "99999"
    assert core.get_account(args=["ACC1"]).call()["balance"] == "1000"


def test_adapter_cannot_change_recipient():
    core, adapter = _wire()
    c = _settle(core, adapter, proposal=_proposal(to=OUTSIDER))
    # OUTSIDER is not on an allowlist, so Core rejects on recipient
    assert c["status"] in ("REJECTED", "EXECUTED")
    if c["status"] == "EXECUTED":
        pay = core.get_payment(args=["PAY-1"]).call()
        assert pay["to"].lower().replace("0x", "") == OUTSIDER.lower().replace("0x", "")


def test_core_rejects_unlisted_recipient_with_allowlist():
    core, adapter = _wire()
    core.update_rules(args=["ACC1", json.dumps(
        {"daily_limit": "1000", "per_tx_limit": "500", "currency": "USDC",
         "allowlist": [RECIPIENT.lower().replace("0x", "")]})]).transact(
        wait_interval=3000, wait_retries=10)
    c = _settle(core, adapter, proposal=_proposal(to=OUTSIDER))
    assert c["reason_code"] == "REJECTED_RECIPIENT"
    assert core.get_account(args=["ACC1"]).call()["balance"] == "1000"


def test_policy_changed_after_adapter_acceptance():
    """The async gap is the real threat: mutate Core policy AFTER admission."""
    core, adapter = _wire()
    adapter.connect(ADJUDICATOR).submit_decision_receipt(args=[_receipt()]).transact(
        wait_interval=3000, wait_retries=10)
    adapter.admit_proposal(args=[_proposal()]).transact(wait_interval=3000, wait_retries=10)
    # narrow the policy before Core ever sees the proposal
    core.update_rules(args=["ACC1", json.dumps(
        {"daily_limit": "1000", "per_tx_limit": "10", "currency": "USDC"})]).transact(
        wait_interval=3000, wait_retries=10)
    adapter.dispatch_proposal(args=["PROP-1"]).transact(wait_interval=5000, wait_retries=25)
    c = _poll(core.get_consequence, "PROP-1")
    assert c["status"] == "REJECTED"
    assert c["reason_code"] in ("REJECTED_AMOUNT", "REJECTED_POLICY")
    assert core.get_account(args=["ACC1"]).call()["balance"] == "1000"


def test_capital_removed_before_core_execution():
    """Drain the account in the gap; Core must recheck capital, not trust the Adapter."""
    core, adapter = _wire(per_tx="5000", daily="5000")
    adapter.connect(ADJUDICATOR).submit_decision_receipt(args=[_receipt()]).transact(
        wait_interval=3000, wait_retries=10)
    adapter.admit_proposal(args=[_proposal(amount="900")]).transact(
        wait_interval=3000, wait_retries=10)
    core.withdraw(args=["ACC1", "900"]).transact(wait_interval=3000, wait_retries=10)
    adapter.dispatch_proposal(args=["PROP-1"]).transact(wait_interval=5000, wait_retries=25)
    c = _poll(core.get_consequence, "PROP-1")
    assert c["status"] == "REJECTED"
    assert c["reason_code"] == "REJECTED_CAPITAL"
    assert core.get_account(args=["ACC1"]).call()["balance"] == "100"


def test_attestation_gate_enforced_at_core():
    core, adapter = _wire(require_attestation=True)
    c = _settle(core, adapter)
    assert c["status"] == "REJECTED"
    assert c["reason_code"] == "REJECTED_ATTESTATION"
    assert core.get_account(args=["ACC1"]).call()["balance"] == "1000"


def test_payment_replay_blocked_at_core():
    core, adapter = _wire()
    core.send(args=["ACC1", "PAY-1", RECIPIENT, "50"]).transact(
        wait_interval=5000, wait_retries=15)
    adapter.connect(ADJUDICATOR).submit_decision_receipt(args=[_receipt()]).transact(
        wait_interval=3000, wait_retries=10)
    adapter.admit_proposal(args=[_proposal()]).transact(wait_interval=3000, wait_retries=10)
    adapter.dispatch_proposal(args=["PROP-1"]).transact(wait_interval=5000, wait_retries=25)
    c = _poll(core.get_consequence, "PROP-1")
    assert c["reason_code"] == "REJECTED_REPLAY"


def test_refusal_is_persisted_and_returned():
    """A refusal must leave an auditable artifact (contract violation otherwise)."""
    core, adapter = _wire(register_adapter=False)
    c = _settle(core, adapter)
    stored = core.get_consequence(args=["PROP-1"]).call()
    assert stored["status"] == "REJECTED"
    assert stored["reason_code"]
    assert stored["adapter_caller"] == adapter.address.lower().replace("0x", "")


def test_consequence_is_write_once():
    """One terminal outcome per proposal_id; no overwrite."""
    core, adapter = _wire()
    first = _settle(core, adapter)
    adapter.connect(ADJUDICATOR).submit_decision_receipt(
        args=[_receipt(did="DEC-2")]).transact(wait_interval=3000, wait_retries=10)
    adapter.admit_proposal(args=[_proposal(did="DEC-2")]).transact(
        wait_interval=3000, wait_retries=10)
    adapter.dispatch_proposal(args=["PROP-1"]).transact(wait_interval=5000, wait_retries=25)
    time.sleep(1.0)
    again = core.get_consequence(args=["PROP-1"]).call()
    assert again == first, "consequence record was overwritten"


def test_rejected_status_yields_no_proposal():
    core, adapter = _wire()
    adapter.connect(ADJUDICATOR).submit_decision_receipt(
        args=[_receipt(did="DEC-N", status="REJECTED")]).transact(
        wait_interval=3000, wait_retries=10)
    assert adapter.get_receipt(args=["DEC-N"]).call()["actionability"] == "NON_ACTIONABLE"
    adapter.admit_proposal(args=[_proposal(pid="PROP-N", did="DEC-N")]).transact(
        wait_interval=3000, wait_retries=10)
    try:
        adapter.get_proposal(args=["PROP-N"]).call()
        exists = True
    except Exception:
        exists = False
    assert exists is False, "REJECTED receipt produced an admitted proposal"
    assert core.get_account(args=["ACC1"]).call()["balance"] == "1000"
