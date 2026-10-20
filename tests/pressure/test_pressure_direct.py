"""Cross-primitive real-world pressure tests (direct mode).

Implements the adversarial questions mandated by AGENTS.md against every
executable primitive contract:

  replay / double-spend, stale evidence, identity/version confusion,
  authority revocation, competing valid requests, capacity overcommit,
  partial execution, exception-created authority, and judgment-is-not-approval.

Runs in the in-memory direct VM (fast, leader function only). The
consensus-level (GLSim) burst test lives in test_pressure_glsim.py.

Run from the repository root:
    pytest tests/pressure/ -v
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

# --- MODULARIZED_OUT_PRESSURE_SPEC -------------------------------------------
# delegate, invoice, and dispute/refund were moved out of the PPA core so the
# single-file deploy fits the Bradbury per-tx gas ceiling. They are declared
# unsupported in primitives/ppa/CAPABILITY.json and enforced absent by
# primitives/ppa/implementations/genlayer/tests/test_ppa_capability_parity.py.
#
# The adversarial properties these tests assert remain MANDATORY when the
# extensions return. The bodies below are preserved verbatim as that
# specification; only the execution marker is added.
#
# A skipped test is NOT passing behavior. See
# convergence/reports/PRESSURE-MODULARIZED-SPEC-REPORT.json.
_MODULARIZED = {
    "delegation": "delegation narrows and never widens; revocation and expiry kill authority immediately",
    "invoice-settlement": "an invoice settles exactly once and only through the send gates",
    "dispute-refund": "refund is a compensating entry; settled history is never rewritten; no double refund",
}


def modularized_out(extension):
    reason = (
        "MODULARIZED_OUT_PRESSURE_SPEC: targets the '{ext}' extension, which is not in the "
        "current PPA core deploy (gas-modularized out to fit the Bradbury per-tx ceiling). "
        "Assertion body preserved verbatim as the specification. Mandatory property when the "
        "extension returns: {prop}. This skip is not a pass."
    ).format(ext=extension, prop=_MODULARIZED[extension])
    return pytest.mark.skip(reason=reason)

PPA = "primitives/ppa/implementations/genlayer/ppa.py"
POLICY = "primitives/policy-envelope/implementations/genlayer/policy_envelope.py"
DAL = "primitives/dal/implementations/genlayer/dal.py"
CE = "primitives/claim-encumbrance/implementations/genlayer/claim_encumbrance.py"
CC = "primitives/capital-commitment/implementations/genlayer/capital_commitment.py"
DAA = "primitives/daa/implementations/genlayer/daa.py"
WA = "primitives/workflow-authorization/implementations/genlayer/workflow_authorization.py"
MA = "primitives/mandate-allocation/implementations/genlayer/mandate_allocation.py"
FC = "primitives/financial-contract/implementations/genlayer/financial_contract.py"
GAIA = "primitives/gaia/implementations/genlayer/gaia.py"
POP = "primitives/proof-of-payable/implementations/genlayer/proof_of_payable.py"
CV = "primitives/claim-verification/implementations/genlayer/claim_verification.py"

RECIPIENT = "0x9f6aa7364d20cf25f054ea83f3cb950317fd34b6"
OTHER = "0x1111111111111111111111111111111111111111"
ISSUER = "0x2222222222222222222222222222222222222222"


def _hex(a) -> str:
    """Normalize a direct-mode test address to a 0x-prefixed hex string."""
    if isinstance(a, (bytes, bytearray)):
        return "0x" + bytes(a).hex()
    h = a.as_hex if hasattr(a, "as_hex") else str(a)
    h = h.lower()
    return h if h.startswith("0x") else "0x" + h



def _rules(per_tx="500", daily="1000", **extra):
    r = {"daily_limit": daily, "per_tx_limit": per_tx, "currency": "USDC"}
    r.update(extra)
    return json.dumps(r)


def _att(subject, issuer=ISSUER, status="VALID", policy="v1"):
    """Fixed-schema PPA attestation payload (no PII, exact field set)."""
    return json.dumps({
        "subject": subject, "issuer": issuer, "status": status,
        "issued_at": "2020-01-01T00:00:00Z",
        "expires_at": "2099-12-31T00:00:00Z",
        "evidence_hash": "sha256:attestation-evidence-1",
        "policy_version": policy,
    })


def _ppa(direct_vm, direct_deploy, alice, rules=None, deposit="2000"):
    direct_vm.sender = alice
    c = direct_deploy(PPA)
    c.initialize(_hex(alice))
    c.create_account("ACC1", rules if rules is not None else _rules())
    if deposit:
        c.deposit("ACC1", deposit)
    return c


def _warp(direct_vm, iso: str) -> None:
    """Advance the contract-visible clock.

    VMContext.warp() updates the VM's cached datetime but does NOT rewrite
    gl.message_raw['datetime'], which is what contracts read via
    gl.message_raw / gl.message.datetime. Warp both.
    """
    direct_vm.warp(iso)
    import sys as _sys
    gl_mod = _sys.modules.get("genlayer.gl")
    if gl_mod is not None and isinstance(getattr(gl_mod, "message_raw", None), dict):
        gl_mod.message_raw["datetime"] = iso


# --------------------------------------------------------------------------
# Programmable Payment Account — the real-world money path
# --------------------------------------------------------------------------

def test_payment_id_replay_of_settled_payment_blocked(direct_vm, direct_deploy, direct_alice):
    """Replaying a settled payment id must fail without moving funds twice."""
    c = _ppa(direct_vm, direct_deploy, direct_alice)
    c.send("ACC1", "P1", RECIPIENT, "300")
    assert c.get_payment("P1")["status"] == "SETTLED"

    with pytest.raises(ValueError, match="PPA: payment id exists"):
        c.send("ACC1", "P1", RECIPIENT, "300")

    acc = c.get_account("ACC1")
    assert acc["balance"] == "1700"          # exactly one debit
    assert acc["daily_spent"] == "300"


def test_denied_payment_id_retryable_after_rule_change(direct_vm, direct_deploy, direct_alice):
    """A DENIED record never burns funds and does not consume the id; the same
    id may settle once the rules allow it."""
    c = _ppa(direct_vm, direct_deploy, direct_alice)
    c.send("ACC1", "P1", RECIPIENT, "600")
    assert c.get_payment("P1")["status"] == "DENIED"
    assert c.get_payment("P1")["reason"] == "POLICY_PER_TX_LIMIT"
    assert c.get_account("ACC1")["balance"] == "2000"

    c.update_rules("ACC1", _rules(per_tx="700"))
    c.send("ACC1", "P1", RECIPIENT, "600")
    assert c.get_payment("P1")["status"] == "SETTLED"
    assert c.get_account("ACC1")["balance"] == "1400"


def test_daily_limit_burst_conserves_balance(direct_vm, direct_deploy, direct_alice):
    """Burst of 11 valid requests against a 1000 daily cap: 10 settle, the
    11th is denied, and total debits equal exactly the cap."""
    c = _ppa(direct_vm, direct_deploy, direct_alice, rules=_rules(per_tx="100", daily="1000"),
             deposit="5000")
    for i in range(10):
        c.send("ACC1", f"B{i}", RECIPIENT, "100")
    c.send("ACC1", "B10", RECIPIENT, "100")

    settled = [c.get_payment(f"B{i}")["status"] for i in range(11)]
    assert settled.count("SETTLED") == 10
    assert c.get_payment("B10")["status"] == "DENIED"
    assert c.get_payment("B10")["reason"] == "POLICY_DAILY_LIMIT"
    acc = c.get_account("ACC1")
    assert acc["balance"] == "4000"           # 5000 - 10*100; denied send burned nothing
    assert acc["daily_spent"] == "1000"       # cap exactly consumed


def test_allowlist_denies_unlisted_recipient(direct_vm, direct_deploy, direct_alice):
    c = _ppa(direct_vm, direct_deploy, direct_alice,
             rules=_rules(allowlist=[RECIPIENT]))
    c.send("ACC1", "A1", OTHER, "100")
    assert c.get_payment("A1")["reason"] == "POLICY_DENYLIST"
    assert c.get_account("ACC1")["balance"] == "2000"

    c.send("ACC1", "A2", RECIPIENT, "100")
    assert c.get_payment("A2")["status"] == "SETTLED"


def test_insufficient_balance_denied_not_partial(direct_vm, direct_deploy, direct_alice):
    """No partial execution: an over-balance send moves nothing at all."""
    c = _ppa(direct_vm, direct_deploy, direct_alice, rules=_rules(per_tx="500", daily="1000"),
             deposit="100")
    c.send("ACC1", "I1", RECIPIENT, "300")
    pay = c.get_payment("I1")
    assert pay["status"] == "DENIED"
    assert pay["reason"] == "INSUFFICIENT_COMMITMENT"
    acc = c.get_account("ACC1")
    assert acc["balance"] == "100"
    assert acc["daily_spent"] == "0"


def test_non_owner_cannot_admin_or_deposit(direct_vm, direct_deploy, direct_alice, direct_bob):
    """Absence of authority must never create authority."""
    c = _ppa(direct_vm, direct_deploy, direct_alice)
    direct_vm.sender = direct_bob
    with pytest.raises(ValueError, match="PPA: caller is not the account owner"):
        c.create_account("ACC2", _rules())
    with pytest.raises(ValueError, match="PPA: caller is not the account owner"):
        c.update_rules("ACC1", _rules(per_tx="999999"))
    with pytest.raises(ValueError, match="PPA: caller is not the account owner"):
        c.withdraw("ACC1", "500")
    with pytest.raises(ValueError, match="PPA: caller has no authority on this account"):
        c.deposit("ACC1", "100")
    assert c.get_account("ACC1")["balance"] == "2000"


def test_withdraw_over_uncommitted_balance_rejected(direct_vm, direct_deploy, direct_alice):
    c = _ppa(direct_vm, direct_deploy, direct_alice)
    with pytest.raises(ValueError, match="PPA: insufficient uncommitted balance"):
        c.withdraw("ACC1", "2001")
    c.withdraw("ACC1", "2000")
    assert c.get_account("ACC1")["balance"] == "0"


@modularized_out('delegation')
def test_delegation_never_widens_and_revocation_kills_spend(
        direct_vm, direct_deploy, direct_alice, direct_bob):
    """Delegation narrows: tighter per-tx and daily limits than the account,
    and revocation cuts spend authority immediately."""
    c = _ppa(direct_vm, direct_deploy, direct_alice)
    c.delegate("DEL1", _hex(direct_bob), "100", "300", "4102444800")

    direct_vm.sender = direct_bob
    # Account per-tx is 500, delegation per-tx is 100 -> narrower wins.
    c.send("ACC1", "D1", RECIPIENT, "150")
    assert c.get_payment("D1")["reason"] == "DELEGATE_PER_TX_LIMIT"

    for pid in ("D2", "D3", "D4"):
        c.send("ACC1", pid, RECIPIENT, "100")
        assert c.get_payment(pid)["status"] == "SETTLED"
    c.send("ACC1", "D5", RECIPIENT, "100")   # 4th of day vs delegate daily 300
    assert c.get_payment("D5")["reason"] == "DELEGATE_DAILY_LIMIT"

    acc = c.get_account("ACC1")
    assert acc["balance"] == "1700"
    assert acc["daily_spent"] == "300"

    direct_vm.sender = direct_alice
    c.revoke_delegation("DEL1")
    direct_vm.sender = direct_bob
    with pytest.raises(ValueError, match="PPA: caller has no authority on this account"):
        c.send("ACC1", "D6", RECIPIENT, "50")


@modularized_out('delegation')
def test_expired_delegation_loses_authority(direct_vm, direct_deploy, direct_alice, direct_bob):
    c = _ppa(direct_vm, direct_deploy, direct_alice)
    c.delegate("DELX", _hex(direct_bob), "100", "300", "1000000000")  # epoch 2001

    direct_vm.sender = direct_bob
    with pytest.raises(ValueError, match="PPA: caller has no authority on this account"):
        c.send("ACC1", "X1", RECIPIENT, "100")
    assert c.get_delegation("DELX")["status"] == "EXPIRED"


@modularized_out('delegation')
def test_policy_allowlist_applies_to_delegate(direct_vm, direct_deploy, direct_alice, direct_bob):
    """The account allowlist cannot be bypassed by acting through a delegate."""
    c = _ppa(direct_vm, direct_deploy, direct_alice,
             rules=_rules(allowlist=[RECIPIENT]))
    c.delegate("DEL2", _hex(direct_bob), "100", "300", "4102444800")
    direct_vm.sender = direct_bob
    c.send("ACC1", "L1", OTHER, "50")
    assert c.get_payment("L1")["reason"] == "POLICY_DENYLIST"
    c.send("ACC1", "L2", RECIPIENT, "50")
    assert c.get_payment("L2")["status"] == "SETTLED"


def test_attestation_gate_fail_closed(direct_vm, direct_deploy, direct_alice):
    """An unavailable/absent attestation is a denial, never an approval."""
    rules = _rules(require_attestation=True, attestation_issuers=[ISSUER],
                   attestation_policy_version="v1")
    c = _ppa(direct_vm, direct_deploy, direct_alice, rules=rules)

    c.send("ACC1", "T1", RECIPIENT, "100")
    assert c.get_payment("T1")["reason"] == "ATTESTATION_MISSING"
    assert c.get_account("ACC1")["balance"] == "2000"

    # Attestation bound to the wrong subject does not admit this recipient.
    c.register_attestation("ATT2", _att(OTHER))
    c.send("ACC1", "T2", RECIPIENT, "100")
    assert c.get_payment("T2")["reason"] == "ATTESTATION_SUBJECT_MISMATCH"

    # Right subject but wrong policy version is still a denial.
    c.register_attestation("ATT9", _att(RECIPIENT, policy="v0"))
    c.send("ACC1", "T3", RECIPIENT, "100")
    assert c.get_payment("T3")["reason"] == "ATTESTATION_POLICY_MISMATCH"
    assert c.get_account("ACC1")["balance"] == "2000"


def test_attestation_revocation_blocks_future_sends(direct_vm, direct_deploy, direct_alice):
    rules = _rules(require_attestation=True, attestation_issuers=[ISSUER],
                   attestation_policy_version="v1")
    c = _ppa(direct_vm, direct_deploy, direct_alice, rules=rules)
    c.register_attestation("ATT1", _att(RECIPIENT))

    c.send("ACC1", "V1", RECIPIENT, "100")
    assert c.get_payment("V1")["status"] == "SETTLED"

    c.revoke_attestation("ATT1")
    c.send("ACC1", "V2", RECIPIENT, "100")
    assert c.get_payment("V2")["reason"] == "ATTESTATION_REVOKED"
    acc = c.get_account("ACC1")
    assert acc["balance"] == "1900"           # only the first send debited
    assert c.get_payment("V1")["status"] == "SETTLED"  # history untouched


@modularized_out('dispute-refund')
def test_dispute_refund_is_compensating_not_rewrite(direct_vm, direct_deploy, direct_alice):
    """Refund creates compensating state; original payment facts stay intact
    and a resolved dispute cannot be resolved twice (no double refund)."""
    c = _ppa(direct_vm, direct_deploy, direct_alice)
    c.send("ACC1", "P1", RECIPIENT, "300")
    c.dispute_payment("DSP1", "P1", "settlement-mismatch",
                      '{"expected":"300","actual":"250"}')

    c.resolve_dispute("DSP1", "refund")
    acc = c.get_account("ACC1")
    pay = c.get_payment("P1")
    assert acc["balance"] == "2000"           # funds restored
    assert pay["status"] == "REFUNDED"
    assert pay["amount"] == "300"             # original facts preserved
    assert pay["to"] == RECIPIENT

    with pytest.raises(ValueError, match="PPA: dispute not open"):
        c.resolve_dispute("DSP1", "refund")   # no double refund
    assert c.get_account("ACC1")["balance"] == "2000"


@modularized_out('dispute-refund')
def test_dispute_guards_payment_lookup_and_authority(
        direct_vm, direct_deploy, direct_alice, direct_bob):
    c = _ppa(direct_vm, direct_deploy, direct_alice)
    c.send("ACC1", "P1", RECIPIENT, "100")
    with pytest.raises(ValueError, match="PPA: payment not found"):
        c.dispute_payment("DSP1", "NO-SUCH-PAY", "duplicate", "{}")
    direct_vm.sender = direct_bob
    with pytest.raises(ValueError, match="PPA: caller has no authority on this account"):
        c.dispute_payment("DSP2", "P1", "duplicate", "{}")
    with pytest.raises(ValueError, match="PPA: caller is not the account owner"):
        c.resolve_dispute("DSP2", "reject")   # owner check fires first


# --------------------------------------------------------------------------
# Policy Envelope — hard limits under competing requests
# --------------------------------------------------------------------------

ENV = ("ENV1", "POLICYHASH-1", "1000", "USD", "1700000000", "1800000000")


def _env(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    c = direct_deploy(POLICY)
    c.create_envelope(*ENV)
    return c


def _eval(c, req_id, amount, asset="USD", ts="1750000000"):
    return json.loads(c.evaluate_request("ENV1", req_id, amount, asset, "ACTOR", "TARGET", ts))


def test_envelope_competing_requests_cannot_overcommit_capacity(
        direct_vm, direct_deploy, direct_alice):
    """Two individually-valid requests must not jointly exceed the cap."""
    c = _env(direct_vm, direct_deploy, direct_alice)
    first = _eval(c, "R1", "600")
    assert first["decision"] == "ADMIT"
    second = _eval(c, "R2", "600")            # 600+600 > 1000
    assert second["decision"] == "DENY"
    assert second["reason_code"] == "CAPACITY_EXHAUSTED"
    assert c.used_amount("ENV1") == "600"     # denied attempt consumed nothing

    third = _eval(c, "R3", "400")             # exact fill is allowed
    assert third["decision"] == "ADMIT"
    assert c.used_amount("ENV1") == "1000"
    fourth = _eval(c, "R4", "1")
    assert fourth["reason_code"] == "CAPACITY_EXHAUSTED"


def test_envelope_stale_timestamps_denied_fail_closed(
        direct_vm, direct_deploy, direct_alice):
    """Stale/future evidence cannot authorize: window is checked before amount."""
    c = _env(direct_vm, direct_deploy, direct_alice)
    stale = _eval(c, "R1", "5000", ts="1699999999")   # before valid_after, also over limit
    assert stale["decision"] == "DENY"
    assert stale["reason_code"] == "OUTSIDE_VALIDITY_WINDOW"
    future = _eval(c, "R2", "100", ts="1800000001")   # after valid_until
    assert future["reason_code"] == "OUTSIDE_VALIDITY_WINDOW"
    assert c.used_amount("ENV1") == "0"


def test_expired_envelope_denies_even_in_window(direct_vm, direct_deploy, direct_alice):
    c = _env(direct_vm, direct_deploy, direct_alice)
    c.expire_envelope("ENV1")
    r = _eval(c, "R1", "100")
    assert r["decision"] == "DENY"
    assert r["reason_code"] == "ENVELOPE_INACTIVE"
    assert c.used_amount("ENV1") == "0"


def test_envelope_asset_and_amount_gates(direct_vm, direct_deploy, direct_alice):
    c = _env(direct_vm, direct_deploy, direct_alice)
    assert _eval(c, "R1", "100", asset="EUR")["reason_code"] == "ASSET_MISMATCH"
    assert _eval(c, "R2", "1001")["reason_code"] == "AMOUNT_EXCEEDS_LIMIT"
    # Denied ids are not consumed: a valid request may reuse the id.
    assert _eval(c, "R2", "100")["decision"] == "ADMIT"


# --------------------------------------------------------------------------
# Dynamic Authorization Lanes — replay protection
# --------------------------------------------------------------------------

def _lane(direct_vm, direct_deploy, direct_alice, domain="DOM-A", expiry="2000000000"):
    direct_vm.sender = direct_alice
    c = direct_deploy(DAL)
    c.open_lane("ISSUER-1", domain, expiry)
    return c


def test_nonce_replay_denied_and_state_frozen(direct_vm, direct_deploy, direct_alice):
    c = _lane(direct_vm, direct_deploy, direct_alice)
    first = json.loads(c.exercise("ISSUER-1", "DOM-A", "1", "1500000000"))
    assert first["decision"] == "AUTHORIZE"
    replay = json.loads(c.exercise("ISSUER-1", "DOM-A", "1", "1500000000"))
    assert replay["decision"] == "DENY"
    assert replay["reason_code"] == "NONCE_REUSED"
    assert json.loads(c.get_lane("ISSUER-1", "DOM-A"))["nonce"] == "2"  # frozen


def test_nonce_gap_denied(direct_vm, direct_deploy, direct_alice):
    c = _lane(direct_vm, direct_deploy, direct_alice)
    r = json.loads(c.exercise("ISSUER-1", "DOM-A", "5", "1500000000"))
    assert r["decision"] == "DENY"
    assert r["reason_code"] == "NONCE_INVALID"
    assert json.loads(c.get_lane("ISSUER-1", "DOM-A"))["nonce"] == "1"


def test_revoked_lane_denies_future_authorization(direct_vm, direct_deploy, direct_alice):
    c = _lane(direct_vm, direct_deploy, direct_alice)
    c.revoke_lane("ISSUER-1", "DOM-A")
    r = json.loads(c.exercise("ISSUER-1", "DOM-A", "1", "1500000000"))
    assert r["decision"] == "DENY"
    assert r["reason_code"] == "LANE_REVOKED"


def test_expired_lane_denies(direct_vm, direct_deploy, direct_alice):
    c = _lane(direct_vm, direct_deploy, direct_alice, domain="DOM-E", expiry="1000")
    r = json.loads(c.exercise("ISSUER-1", "DOM-E", "1", "2000"))
    assert r["decision"] == "DENY"
    assert r["reason_code"] == "LANE_EXPIRED"


def test_lanes_are_independent_replay_domains(direct_vm, direct_deploy, direct_alice):
    """Consuming one domain must not invalidate another from the same issuer."""
    c = _lane(direct_vm, direct_deploy, direct_alice, domain="DOM-1")
    c.open_lane("ISSUER-1", "DOM-2", "2000000000")
    for n in ("1", "2", "3"):
        r = json.loads(c.exercise("ISSUER-1", "DOM-1", n, "1500000000"))
        assert r["decision"] == "AUTHORIZE"
    assert json.loads(c.get_lane("ISSUER-1", "DOM-1"))["nonce"] == "4"
    # Domain 2 unaffected: its first nonce still works.
    r = json.loads(c.exercise("ISSUER-1", "DOM-2", "1", "1500000000"))
    assert r["decision"] == "AUTHORIZE"


# --------------------------------------------------------------------------
# Claim Encumbrance — capacity accounting under contention
# --------------------------------------------------------------------------

def test_encumbrance_overcommit_rejected_capacity_stays_exact(
        direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    c = direct_deploy(CE)
    c.set_financeable_amount("C1", "1000")
    c.reserve("R1", "C1", "700")
    with pytest.raises(ValueError, match="ClaimEncumbrance: exceeds financeable capacity"):
        c.reserve("R2", "C1", "400")            # 700+400 > 1000
    assert c.active_encumbrances("C1") == "700"  # failed reserve moved nothing
    assert c.get_encumbrance("R2") == ""         # no phantom reservation
    with pytest.raises(ValueError, match="ClaimEncumbrance: financeable amount already set"):
        c.set_financeable_amount("C1", "500")    # claim amount is immutable
    with pytest.raises(ValueError, match="ClaimEncumbrance: reservation already exists"):
        c.reserve("R1", "C1", "100")             # identity confusion blocked


def test_encumbrance_terminate_paths_are_single_shot(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    c = direct_deploy(CE)
    c.set_financeable_amount("C1", "1000")

    c.reserve("R1", "C1", "700")
    c.release("R1")
    assert c.active_encumbrances("C1") == "0"    # capacity returned
    with pytest.raises(ValueError, match="ClaimEncumbrance: reservation already terminated"):
        c.release("R1")                          # double release blocked
    with pytest.raises(ValueError, match="ClaimEncumbrance: reservation already terminated"):
        c.settle("R1")                           # release->settle blocked

    c.reserve("R2", "C1", "500")
    c.commit("R2")
    c.settle("R2")
    assert c.active_encumbrances("C1") == "0"
    with pytest.raises(ValueError, match="ClaimEncumbrance: reservation already terminated"):
        c.settle("R2")                           # settle twice blocked
    # Released capacity is reusable by a new reservation.
    c.reserve("R3", "C1", "900")
    assert c.active_encumbrances("C1") == "900"


# --------------------------------------------------------------------------
# Capital Commitment — pool backing under contention
# --------------------------------------------------------------------------

def test_backing_overcommit_rejected_and_release_restores_capacity(
        direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    c = direct_deploy(CC)
    c.set_backing("POOL-1", "USD", "1000")
    c.reserve("CM1", "POOL-1", "USD", "BEN", "600", "9999999999")
    with pytest.raises(ValueError, match="CapitalCommitment: reservation exceeds available backing capacity"):
        c.reserve("CM2", "POOL-1", "USD", "BEN", "500", "9999999999")
    assert c.available_capacity("POOL-1", "USD") == "400"
    assert c.active_commitments("POOL-1", "USD") == "600"

    c.release("CM1")
    assert c.available_capacity("POOL-1", "USD") == "1000"  # capacity restored
    assert c.active_commitments("POOL-1", "USD") == "0"

    # Fully-restored capacity can be re-reserved, then committed.
    c.reserve("CM3", "POOL-1", "USD", "BEN", "1000", "9999999999")
    c.commit("CM3")
    assert c.available_capacity("POOL-1", "USD") == "0"
    with pytest.raises(ValueError, match="CapitalCommitment: commitment_id already used"):
        c.reserve("CM3", "POOL-1", "USD", "BEN", "1", "9999999999")


# --------------------------------------------------------------------------
# Dynamic Authority Allocation — bounded grants and revocation
# --------------------------------------------------------------------------

def _daa_awarded(direct_vm, direct_deploy, direct_alice, bound="5000"):
    direct_vm.sender = direct_alice
    c = direct_deploy(DAA)
    c.request_allocation("REQ1", "POOL-1", "USD", "BENEFICIARY-B",
                         "treasury-facility", bound, "POLICYHASH-1", "0", "9999999999")
    c.award("REQ1", "AL1", "4000", "2000000000")
    return c


def _verify(c, amount, actor="BENEFICIARY-B", resource="POOL-1",
            purpose="treasury-facility", ts="2000000000"):
    return json.loads(c.verify_authority("AL1", actor, resource, purpose, amount, ts))


def test_award_bounds_enforced_and_revocation_kills_authority(
        direct_vm, direct_deploy, direct_alice):
    c = _daa_awarded(direct_vm, direct_deploy, direct_alice)
    assert _verify(c, "1000")["decision"] == "AUTHORIZE"
    assert _verify(c, "5000")["reason_code"] == "EXCEEDS_AWARD_BOUND"      # > 4000
    assert _verify(c, "1000", actor="EVIL-ACTOR")["reason_code"] == "BENEFICIARY_MISMATCH"
    assert _verify(c, "1000", resource="POOL-2")["reason_code"] == "RESOURCE_MISMATCH"
    assert _verify(c, "1000", purpose="other-scope")["reason_code"] == "PURPOSE_MISMATCH"
    assert _verify(c, "1000", ts="10000000000")["reason_code"] == "AWARD_EXPIRED"

    c.revoke_award("AL1")
    assert _verify(c, "1000")["reason_code"] == "AWARD_REVOKED"
    with pytest.raises(ValueError, match="DAA: request not awardable"):
        c.award("REQ1", "AL2", "100", "2000000000")   # request already consumed
    # A fresh request still cannot reuse an existing (revoked) allocation id.
    c.request_allocation("REQ9", "POOL-1", "USD", "BENEFICIARY-B",
                         "treasury-facility", "5000", "POLICYHASH-1", "0", "9999999999")
    with pytest.raises(ValueError, match="DAA: allocation_id already exists"):
        c.award("REQ9", "AL1", "100", "2000000000")   # revoked id is retired forever


def test_only_authority_source_awards_and_bound_escalation_impossible(
        direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    c = direct_deploy(DAA)
    c.request_allocation("REQ7", "POOL-1", "USD", "BENEFICIARY-B",
                         "treasury-facility", "5000", "POLICYHASH-1", "0", "9999999999")
    direct_vm.sender = direct_bob
    with pytest.raises(ValueError, match="DAA: only the authority source may award"):
        c.award("REQ7", "AL-X", "100", "2000000000")
    # Bound escalation: award may never exceed the requested bound.
    direct_vm.sender = direct_alice
    with pytest.raises(ValueError, match="DAA: award exceeds requested bound"):
        c.award("REQ7", "AL-Y", "6000", "2000000000")


def test_award_outside_request_validity_window_rejected(
        direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    c = direct_deploy(DAA)
    c.request_allocation("REQ2", "POOL-1", "USD", "BENEFICIARY-B",
                         "treasury-facility", "5000", "POLICYHASH-1",
                         "1700000000", "1800000000")
    with pytest.raises(ValueError, match="DAA: award time outside request validity window"):
        c.award("REQ2", "AL2", "100", "1900000000")


# --------------------------------------------------------------------------
# Workflow Authorization (Path/Pact) — standing authority windows
# --------------------------------------------------------------------------

def _wa(direct_vm, direct_deploy, direct_alice, path_id="PATH1",
         valid_after="0", valid_until="9999999999", max_per="5000"):
    direct_vm.sender = direct_alice
    c = direct_deploy(WA)
    c.grant_path(path_id, _hex(direct_alice), "AGENT-B", "treasury-payments",
                 max_per, "USD", valid_after, valid_until)
    return c


def test_pact_execute_deny_then_authorize_then_terminal(
        direct_vm, direct_deploy, direct_alice):
    c = _wa(direct_vm, direct_deploy, direct_alice)
    c.propose_pact("PACT1", "PATH1", "wf-ref-1", '{"amount":"4000"}', "1500000000")
    # Before acceptance -> deny.
    r = json.loads(c.execute_pact("PACT1", "100", "1500000000"))
    assert r["decision"] == "DENY" and r["reason_code"] == "PACT_NOT_ACCEPTED"

    c.accept_pact("PACT1")                     # sender is path principal
    over = json.loads(c.execute_pact("PACT1", "6000", "1500000000"))  # > path bound
    assert over["decision"] == "DENY" and over["reason_code"] == "EXCEEDS_PATH_BOUND"
    assert json.loads(c.get_pact("PACT1"))["status"] == "ACCEPTED"     # still usable

    ok = json.loads(c.execute_pact("PACT1", "4000", "1500000000"))
    assert ok["decision"] == "AUTHORIZE"
    with pytest.raises(ValueError, match="WorkflowAuthorization: pact is terminal"):
        c.execute_pact("PACT1", "4000", "1500000000")   # replay of executed pact


def test_revoked_path_blocks_execution_and_new_pacts(
        direct_vm, direct_deploy, direct_alice, direct_bob):
    c = _wa(direct_vm, direct_deploy, direct_alice)
    c.propose_pact("PACT2", "PATH1", "wf-ref-2", "{}", "1500000000")
    direct_vm.sender = direct_bob
    with pytest.raises(ValueError, match="WorkflowAuthorization: only the path principal may accept"):
        c.accept_pact("PACT2")
    direct_vm.sender = direct_alice
    c.accept_pact("PACT2")

    c.revoke_path("PATH1")
    r = json.loads(c.execute_pact("PACT2", "100", "1500000000"))
    assert r["decision"] == "DENY" and r["reason_code"] == "PATH_NOT_ACTIVE"
    with pytest.raises(ValueError, match="WorkflowAuthorization: path is not active"):
        c.propose_pact("PACT3", "PATH1", "wf-ref-3", "{}", "1500000000")


def test_expired_path_window_denies_execution(direct_vm, direct_deploy, direct_alice):
    c = _wa(direct_vm, direct_deploy, direct_alice, path_id="PATH-E",
            valid_after="0", valid_until="1000")
    c.propose_pact("PACT-E", "PATH-E", "wf-ref-e", "{}", "500")
    c.accept_pact("PACT-E")
    r = json.loads(c.execute_pact("PACT-E", "100", "2000"))
    assert r["decision"] == "DENY" and r["reason_code"] == "PATH_EXPIRED"


# --------------------------------------------------------------------------
# Mandate Allocation — advisory exposure caps (recommendation, not authority)
# --------------------------------------------------------------------------

def test_mandate_exposure_cap_enforced_under_competition(
        direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    c = direct_deploy(MA)
    c.register_mandate("MAN1", "sha256:mandate-doc-1", "1000", "USD",
                       '["invoice","trade-receivable"]')

    e1 = json.loads(c.evaluate_opportunity("E1", "MAN1", "OPP-1", "invoice", "600", "1500000000"))
    assert e1["eligibility"] == "ELIGIBLE"
    # Competing request that would jointly exceed the cap is ineligible.
    e2 = json.loads(c.evaluate_opportunity("E2", "MAN1", "OPP-2", "invoice", "600", "1500000000"))
    assert e2["eligibility"] == "INELIGIBLE"
    assert e2["reason_code"] == "EXPOSURE_EXCEEDED"
    assert c.committed_exposure("MAN1") == "600"      # ineligible consumed nothing

    e3 = json.loads(c.evaluate_opportunity("E3", "MAN1", "OPP-3", "trade-receivable", "400", "1500000000"))
    assert e3["eligibility"] == "ELIGIBLE"            # exact fill
    assert c.committed_exposure("MAN1") == "1000"
    e4 = json.loads(c.evaluate_opportunity("E4", "MAN1", "OPP-4", "invoice", "1", "1500000000"))
    assert e4["eligibility"] == "INELIGIBLE"
    assert c.committed_exposure("MAN1") == "1000"

    # Class outside the mandate is rejected without consuming exposure.
    e5 = json.loads(c.evaluate_opportunity("E5", "MAN1", "OPP-5", "crypto-loan", "1", "1500000000"))
    assert e5["reason_code"] == "CLASS_NOT_PERMITTED"
    assert c.committed_exposure("MAN1") == "1000"

    with pytest.raises(ValueError, match="MandateAllocation: evaluation already exists"):
        c.evaluate_opportunity("E1", "MAN1", "OPP-6", "invoice", "1", "1500000000")


# --------------------------------------------------------------------------
# Financial Contract — obligation cash-flow lifecycle
# --------------------------------------------------------------------------

def test_payment_conservation_no_overpay_no_replay(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    c = direct_deploy(FC)
    c.open_contract("FC1", _hex(direct_alice), "OBLIGOR-B", "10000", "USD",
                    "1700000000", "1800000000", "PATH-REF-1")
    r = json.loads(c.apply_payment("FC1", "P1", "6000", "1750000000"))
    assert r["applied"] == "6000" and r["outstanding"] == "4000"

    with pytest.raises(ValueError, match="FinancialContract: payment already exists"):
        c.apply_payment("FC1", "P1", "6000", "1750000000")   # replay blocked

    over = json.loads(c.apply_payment("FC1", "P2", "5000", "1750000000"))
    assert over["decision"] == "DENY" and over["reason_code"] == "EXCEEDS_OUTSTANDING"
    stale = json.loads(c.apply_payment("FC1", "P3", "100", "1699999999"))
    assert stale["reason_code"] == "BEFORE_VALIDITY_WINDOW"

    # Not matured yet -> default cannot be declared.
    with pytest.raises(ValueError, match="FinancialContract: maturity has not passed"):
        c.declare_default("FC1")

    r2 = json.loads(c.apply_payment("FC1", "P4", "4000", "1750000000"))
    assert r2["contract_status"] == "CLOSED" and r2["outstanding"] == "0"
    closed = json.loads(c.apply_payment("FC1", "P5", "1", "1750000000"))
    assert closed["reason_code"] == "CONTRACT_CLOSED"

    rec = json.loads(c.get_contract("FC1"))
    assert rec["total_paid"] == "10000" and rec["outstanding"] == "0"  # conservation


def test_default_is_terminal_and_creditor_only(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    c = direct_deploy(FC)
    # Already-matured window (maturity in the past) with outstanding balance.
    c.open_contract("FC2", _hex(direct_alice), "OBLIGOR-B", "5000", "USD",
                    "1600000000", "1700000000", "PATH-REF-2")

    direct_vm.sender = direct_bob
    with pytest.raises(ValueError, match="FinancialContract: only the creditor may declare default"):
        c.declare_default("FC2")

    direct_vm.sender = direct_alice
    c.declare_default("FC2")
    assert json.loads(c.get_contract("FC2"))["status"] == "DEFAULTED"
    with pytest.raises(ValueError, match="FinancialContract: contract not active"):
        c.declare_default("FC2")                    # double default blocked

    late = json.loads(c.apply_payment("FC2", "P1", "100", "1750000000"))
    assert late["decision"] == "DENY"
    assert late["reason_code"] == "CONTRACT_DEFAULTED"
    assert json.loads(c.get_contract("FC2"))["total_paid"] == "0"  # nothing moved


# --------------------------------------------------------------------------
# Gaia — disputes/rectification without authority bypass
# --------------------------------------------------------------------------

def test_rectification_requires_complete_obligations_and_single_resolution(
        direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    c = direct_deploy(GAIA)
    c.open_case("CASE1", "settlement-mismatch", "SETTLE-77",
                '{"expected":"100","actual":"90"}')
    c.classify_case("CASE1", "CL1",
                    '[{"type":"refund","bound":{"amount":"10"}},{"type":"reconcile","bound":{}}]')
    with pytest.raises(ValueError, match="Gaia: case already classified"):
        c.classify_case("CASE1", "CL2", '[{"type":"refund","bound":{}}]')

    with pytest.raises(ValueError, match="Gaia: pending obligations remain"):
        c.resolve_case("CASE1", "sha256:res-1")           # O0 and O1 still prescribed
    c.discharge_obligation("CL1-O0", "sha256:dis-1")
    with pytest.raises(ValueError, match="Gaia: pending obligations remain"):
        c.resolve_case("CASE1", "sha256:res-1")           # O1 still pending
    c.waive_obligation("CL1-O1", "waived per treasury policy")

    c.resolve_case("CASE1", "sha256:res-1")
    assert json.loads(c.get_case("CASE1"))["status"] == "RESOLVED"
    with pytest.raises(ValueError, match="Gaia: case already resolved"):
        c.resolve_case("CASE1", "sha256:res-2")           # no double resolution

    with pytest.raises(ValueError, match="Gaia: obligation already dispositioned"):
        c.discharge_obligation("CL1-O0", "sha256:dis-2")  # evidence history frozen
    assert json.loads(c.get_obligation("CL1-O0"))["evidence_hash"] == "sha256:dis-1"


def test_gaia_rejects_unknown_category(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    c = direct_deploy(GAIA)
    with pytest.raises(ValueError, match="Gaia: unknown case category"):
        c.open_case("CASE2", "free-text-injection", "SUBJ", "{}")


# --------------------------------------------------------------------------
# Proof of Payable — evidence lifecycle guards
# --------------------------------------------------------------------------

def test_evidence_state_machine_guards(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    c = direct_deploy(POP)
    c.open_claim("C1", "1000", "INV-2026-001", "ACME-CORP")
    with pytest.raises(ValueError, match="ProofOfPayable: cannot attest without evidence"):
        c.attest_claim("C1")
    with pytest.raises(ValueError, match="ProofOfPayable: only ATTESTED claims may settle"):
        c.settle_claim("C1")

    c.attach_evidence("C1", "PRF1", "sha256:proof-1", '{"source":"erp"}')
    with pytest.raises(ValueError, match="ProofOfPayable: proof_id already exists"):
        c.attach_evidence("C1", "PRF1", "sha256:proof-other", "{}")
    # The same evidence identity cannot be re-used under another claim.
    c.open_claim("C2", "500", "INV-2026-002", "ACME-CORP")
    with pytest.raises(ValueError, match="ProofOfPayable: proof_id already exists"):
        c.attach_evidence("C2", "PRF1", "sha256:proof-1", "{}")

    c.attest_claim("C1")
    with pytest.raises(ValueError, match="ProofOfPayable: claim already attested"):
        c.attest_claim("C1")
    c.settle_claim("C1")
    claim = json.loads(c.get_claim("C1"))
    assert claim["status"] == "SETTLED"
    assert claim["latest_proof_hash"] == "sha256:proof-1"
    with pytest.raises(ValueError, match="ProofOfPayable: claim is not live"):
        c.settle_claim("C1")                       # settle twice blocked
    with pytest.raises(ValueError, match="ProofOfPayable: claim is not live"):
        c.attach_evidence("C1", "PRF9", "sha256:proof-9", "{}")  # no post-settlement evidence


def test_disputed_claim_is_not_settlement_eligible(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    c = direct_deploy(POP)
    c.open_claim("C3", "1000", "INV-2026-003", "ACME-CORP")
    c.attach_evidence("C3", "PRF3", "sha256:proof-3", "{}")
    c.attest_claim("C3")
    c.dispute_claim("C3")
    with pytest.raises(ValueError, match="ProofOfPayable: claim is not live"):
        c.settle_claim("C3")                       # disputed claims cannot settle
    c.reject_claim("C3")
    assert json.loads(c.get_claim("C3"))["status"] == "REJECTED"
    with pytest.raises(ValueError, match="ProofOfPayable: only DISPUTED claims may be rejected"):
        c.reject_claim("C3")


# --------------------------------------------------------------------------
# Claim Verification — judgment boundary (SEMANTIC convergence)
# --------------------------------------------------------------------------

_CV_CLAIM = json.dumps({"claim_id": "C123", "amount": "100000", "asset": "USD"})
_CV_EVIDENCE = json.dumps({"invoice": {"amount": "100000"}, "delivery": {"status": "accepted"}})


def test_undetermined_verdict_is_not_approval(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    direct_vm.mock_llm(r".*", json.dumps({
        "status": "UNDETERMINED", "reason_code": "EVIDENCE_AMBIGUOUS",
        "analysis": "conflicting sources"}))
    c = direct_deploy(CV)
    d = json.loads(c.verify_claim("V1", "C123", "sha256:ev-1", _CV_CLAIM, _CV_EVIDENCE))
    assert d["status"] == "UNDETERMINED"
    assert d["status"] != "VERIFIED"               # undetermined never implies approval
    assert json.loads(c.get_verification("V1"))["status"] == "UNDETERMINED"


def test_out_of_schema_model_output_rejected(direct_vm, direct_deploy, direct_alice):
    """Free-form model output must not become an on-chain decision."""
    direct_vm.sender = direct_alice
    direct_vm.mock_llm(r".*", json.dumps({"decision": "SURE_APPROVE"}))
    c = direct_deploy(CV)
    with pytest.raises(Exception):
        c.verify_claim("V2", "C123", "sha256:ev-1", _CV_CLAIM, _CV_EVIDENCE)
    assert c.has_verification("V2") is False       # failed judgment left no state










@modularized_out('invoice-settlement')
def test_invoice_settles_once_through_send_gates(direct_vm, direct_deploy, direct_alice):
    c = _ppa(direct_vm, direct_deploy, direct_alice)
    c.issue_invoice("I1", RECIPIENT, "200", '[{"sku":"SKU-1","qty":1}]', "2026-12-31")
    c.settle_invoice("I1", "ACC1")
    inv = c.get_invoice("I1")
    assert inv["status"] == "SETTLED"
    assert c.get_payment("pay-I1")["status"] == "SETTLED"
    assert c.get_account("ACC1")["balance"] == "1800"

    with pytest.raises(ValueError, match="PPA: invoice not open"):
        c.settle_invoice("I1", "ACC1")         # no double pay
    assert c.get_account("ACC1")["balance"] == "1800"


def test_daily_window_rolls_after_24h(direct_vm, direct_deploy, direct_alice):
    """A denied send stays denied within the window; after 24h the window
    resets and the same value transfers under the same payment id."""
    c = _ppa(direct_vm, direct_deploy, direct_alice, rules=_rules(per_tx="700", daily="1000"))
    c.send("ACC1", "W1", RECIPIENT, "500")
    c.send("ACC1", "W2", RECIPIENT, "600")
    assert c.get_payment("W2")["reason"] == "POLICY_DAILY_LIMIT"

    _warp(direct_vm, (datetime.now(timezone.utc) + timedelta(hours=25)).isoformat())
    c.send("ACC1", "W2", RECIPIENT, "600")    # prior record was DENIED -> id reusable
    acc = c.get_account("ACC1")
    assert acc["daily_spent"] == "600"
    assert acc["balance"] == "900"
