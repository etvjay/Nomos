"""Receipt origin binding (v0.3): a receipt must be attributable to a registered adjudicator.

Spec under test. These replace the v0.2 red tests that documented the forgery.

v0.2 accepted any syntactically valid caller-supplied receipt JSON. `source_contract`
was a self-asserted string. The live spine run on
0xa4fbEc963Bc105bc950648D092d11bAE7eF191fb settled 100 units on a receipt whose
source_contract was the placeholder 0xabc000000000000000000000000000000000001 —
registered nowhere. That deployment is historical and BOUND_TO_SUPERSEDED_AUTHORITY.

v0.3 rule: origin is bound to `gl.message.sender_address`, compared against an
owner-registered adjudicator with a pinned authority fingerprint. A JSON
`source_contract` field is a claim, never provenance.

Boundary this file deliberately does NOT claim: origin binding establishes
attribution/integrity. It is NOT adjudication correctness. A registered but
compromised adjudicator can still emit ACCEPTED for a false conclusion and PPA
will honour it. See DECISION_BOUNDARY.md.

Run:
    source ~/nomos-venv312/bin/activate
    python -m pytest primitives/ppa/implementations/genlayer/tests/test_ppa_receipt_origin.py -q
"""
import json

from gltest import get_contract_factory, get_accounts
from gltest.assertions import tx_execution_failed, tx_execution_succeeded

OWNER = get_accounts()[0].address
ADJUDICATOR = get_accounts()[1]
ADJ_ADDR = ADJUDICATOR.address
OTHER = get_accounts()[2]
OTHER_ADDR = OTHER.address

RECIPIENT = "0x9f6aa7364d20cf25f054ea83f3cb950317fd34b6"
# Never registered anywhere.
UNREGISTERED = "0xabc000000000000000000000000000000000001"

FINGERPRINT = "sha256:adjudicator-code-identity-001"
OTHER_FINGERPRINT = "sha256:different-code-identity-999"

FAR_FUTURE = "2099-01-01T00:00:00+00:00"
LONG_PAST = "2020-01-01T00:00:00+00:00"


def _deploy():
    c = get_contract_factory(contract_file_path="ppa.py").deploy()
    c.initialize(args=[OWNER]).transact(wait_interval=3000, wait_retries=10)
    return c


def _rules():
    return json.dumps({"daily_limit": "1000", "per_tx_limit": "500", "currency": "USDC"})


def _adj(source=None, fingerprint=FINGERPRINT, expires=FAR_FUTURE, policy="TECH-V1"):
    return json.dumps({
        "source_contract": source or ADJ_ADDR,
        "authority_fingerprint": fingerprint,
        "policy_version": policy,
        "created_at": LONG_PAST,
        "expires_at": expires,
    })


def _receipt(decision_id="DEC-1", status="ACCEPTED", source=None,
             fingerprint=FINGERPRINT, evidence="sha256:ev-1",
             created_at=LONG_PAST, expires=FAR_FUTURE):
    return json.dumps({
        "decision_id": decision_id,
        "source_contract": source or ADJ_ADDR,
        "authority_fingerprint": fingerprint,
        "question_hash": "sha256:q-1",
        "evidence_hash": evidence,
        "decision_status": status,
        "equivalence_mode": "comparative",
        "policy_version": "TECH-V1",
        "created_at": created_at,
        "expires_at": expires,
    })


def _funded(c, account_id="ACC1", amount="1000"):
    c.create_account(args=[account_id, _rules()]).transact(wait_interval=3000, wait_retries=10)
    c.deposit(args=[account_id, amount]).transact(wait_interval=3000, wait_retries=10)


def _proposal(decision_id="DEC-1", proposal_id="PROP-1", amount="100"):
    return json.dumps({
        "proposal_id": proposal_id, "decision_id": decision_id, "account_id": "ACC1",
        "payment_id": "PAY-1", "to": RECIPIENT, "amount": amount, "policy_version": "TECH-V1",
    })


def _adjudicator_handle(c):
    """The same contract, driven by the adjudicator account, so sender_address is ADJ_ADDR."""
    return c.connect(ADJUDICATOR)


# --- case 1: registered ACTIVE source, matching caller -> ACTIONABLE -------------

def test_registered_source_matching_caller_is_actionable():
    c = _deploy()
    _funded(c)
    c.register_adjudicator(args=[_adj()]).transact(wait_interval=3000, wait_retries=10)

    _adjudicator_handle(c).submit_decision_receipt(
        args=[_receipt()]).transact(wait_interval=3000, wait_retries=10)

    r = c.get_receipt(args=["DEC-1"]).call()
    assert r["actionability"] == "ACTIONABLE"
    assert r["decision_status"] == "ACCEPTED"
    assert r.get("origin_status") == "BOUND"


def test_registered_source_reaches_settlement():
    """The full consequence boundary: bound receipt -> proposal -> payment -> balance moved."""
    c = _deploy()
    _funded(c)
    c.register_adjudicator(args=[_adj()]).transact(wait_interval=3000, wait_retries=10)
    _adjudicator_handle(c).submit_decision_receipt(
        args=[_receipt()]).transact(wait_interval=3000, wait_retries=10)

    c.admit_proposal(args=[_proposal()]).transact(wait_interval=3000, wait_retries=10)
    assert c.get_proposal(args=["PROP-1"]).call()["status"] == "ADMITTED"

    tx = c.execute_proposal(args=["PROP-1"]).transact(wait_interval=5000, wait_retries=15)
    assert tx_execution_succeeded(tx)

    pay = c.get_payment(args=["PAY-1"]).call()
    assert pay["status"] == "SETTLED"
    assert pay["decision_id"] == "DEC-1"
    assert c.get_account(args=["ACC1"]).call()["balance"] == "900"


# --- case 2: unregistered source -> RECEIPT_SOURCE_UNREGISTERED ----------------

def test_unregistered_source_is_not_actionable():
    c = _deploy()
    _funded(c)
    # no registration at all
    _adjudicator_handle(c).submit_decision_receipt(
        args=[_receipt()]).transact(wait_interval=3000, wait_retries=10)

    r = c.get_receipt(args=["DEC-1"]).call()
    assert r["actionability"] == "NON_ACTIONABLE"
    assert r["fail_reason"] == "RECEIPT_SOURCE_UNREGISTERED"
    assert r["origin_status"] == "UNREGISTERED"


def test_unregistered_source_cannot_reach_settlement():
    c = _deploy()
    _funded(c)
    _adjudicator_handle(c).submit_decision_receipt(
        args=[_receipt()]).transact(wait_interval=3000, wait_retries=10)
    c.admit_proposal(args=[_proposal()]).transact(wait_interval=3000, wait_retries=10)

    try:
        c.get_proposal(args=["PROP-1"]).call()
        exists = True
    except Exception:
        exists = False
    assert exists is False, "unregistered-source receipt produced an admitted proposal"
    assert c.get_account(args=["ACC1"]).call()["balance"] == "1000"


def test_owner_cannot_self_assert_a_receipt():
    """The owner is not implicitly an adjudicator. v0.2 let the owner write its own verdict."""
    c = _deploy()
    _funded(c)
    c.submit_decision_receipt(args=[_receipt()]).transact(wait_interval=3000, wait_retries=10)
    r = c.get_receipt(args=["DEC-1"]).call()
    assert r["actionability"] == "NON_ACTIONABLE"
    assert r["fail_reason"] == "RECEIPT_SOURCE_UNREGISTERED"


def test_json_source_contract_alone_is_not_provenance():
    """An unregistered caller claiming the registered address must still be refused."""
    c = _deploy()
    _funded(c)
    c.register_adjudicator(args=[_adj()]).transact(wait_interval=3000, wait_retries=10)
    # OTHER_ADDR submits JSON asserting source_contract == ADJ_ADDR
    c.connect(OTHER).submit_decision_receipt(
        args=[_receipt(source=ADJ_ADDR)]).transact(wait_interval=3000, wait_retries=10)

    r = c.get_receipt(args=["DEC-1"]).call()
    assert r["actionability"] == "NON_ACTIONABLE"
    assert r["fail_reason"] == "RECEIPT_SOURCE_UNREGISTERED"


# --- case 3: revoked source -> RECEIPT_SOURCE_REVOKED -------------------------

def test_revoked_source_is_not_actionable():
    c = _deploy()
    _funded(c)
    c.register_adjudicator(args=[_adj()]).transact(wait_interval=3000, wait_retries=10)
    c.revoke_adjudicator(args=[ADJ_ADDR]).transact(wait_interval=3000, wait_retries=10)

    _adjudicator_handle(c).submit_decision_receipt(
        args=[_receipt()]).transact(wait_interval=3000, wait_retries=10)

    r = c.get_receipt(args=["DEC-1"]).call()
    assert r["actionability"] == "NON_ACTIONABLE"
    assert r["fail_reason"] == "RECEIPT_SOURCE_REVOKED"
    assert c.get_adjudicator(args=[ADJ_ADDR]).call()["status"] == "REVOKED"


def test_revoked_source_cannot_reach_settlement():
    c = _deploy()
    _funded(c)
    c.register_adjudicator(args=[_adj()]).transact(wait_interval=3000, wait_retries=10)
    c.revoke_adjudicator(args=[ADJ_ADDR]).transact(wait_interval=3000, wait_retries=10)
    _adjudicator_handle(c).submit_decision_receipt(
        args=[_receipt()]).transact(wait_interval=3000, wait_retries=10)
    c.admit_proposal(args=[_proposal()]).transact(wait_interval=3000, wait_retries=10)
    try:
        c.get_proposal(args=["PROP-1"]).call()
        exists = True
    except Exception:
        exists = False
    assert exists is False
    assert c.get_account(args=["ACC1"]).call()["balance"] == "1000"


# --- case 3b: registered but expired registry entry ---------------------------

def test_expired_registration_is_not_actionable():
    c = _deploy()
    _funded(c)
    c.register_adjudicator(args=[_adj(expires="2021-01-01T00:00:00+00:00")]).transact(
        wait_interval=3000, wait_retries=10)
    _adjudicator_handle(c).submit_decision_receipt(
        args=[_receipt()]).transact(wait_interval=3000, wait_retries=10)
    r = c.get_receipt(args=["DEC-1"]).call()
    assert r["actionability"] == "NON_ACTIONABLE"
    assert r["fail_reason"] == "RECEIPT_SOURCE_EXPIRED"


# --- case 4: registered source, wrong caller -> RECEIPT_SOURCE_MISMATCH -------

def test_wrong_caller_claiming_registered_source_is_mismatch():
    """An address with no registry entry that names itself as the registered source."""
    c = _deploy()
    _funded(c)
    c.register_adjudicator(args=[_adj()]).transact(wait_interval=3000, wait_retries=10)
    # OTHER_ADDR is not registered -> unregistered, which is checked first.
    c.connect(OTHER).submit_decision_receipt(
        args=[_receipt(source=OTHER_ADDR)]).transact(wait_interval=3000, wait_retries=10)
    r = c.get_receipt(args=["DEC-1"]).call()
    assert r["actionability"] == "NON_ACTIONABLE"
    assert r["fail_reason"] == "RECEIPT_SOURCE_UNREGISTERED"


def test_registered_caller_with_foreign_source_field_is_mismatch():
    """Adjudicator calls, but the receipt names a different source than its own address."""
    c = _deploy()
    _funded(c)
    c.register_adjudicator(args=[_adj()]).transact(wait_interval=3000, wait_retries=10)
    _adjudicator_handle(c).submit_decision_receipt(
        args=[_receipt(source=UNREGISTERED)]).transact(wait_interval=3000, wait_retries=10)
    r = c.get_receipt(args=["DEC-1"]).call()
    assert r["actionability"] == "NON_ACTIONABLE"
    assert r["fail_reason"] == "RECEIPT_SOURCE_MISMATCH"


# --- case 5: fingerprint mismatch -> RECEIPT_AUTHORITY_MISMATCH ----------------

def test_authority_fingerprint_mismatch_is_refused():
    c = _deploy()
    _funded(c)
    c.register_adjudicator(args=[_adj()]).transact(wait_interval=3000, wait_retries=10)
    _adjudicator_handle(c).submit_decision_receipt(
        args=[_receipt(fingerprint=OTHER_FINGERPRINT)]).transact(
        wait_interval=3000, wait_retries=10)
    r = c.get_receipt(args=["DEC-1"]).call()
    assert r["actionability"] == "NON_ACTIONABLE"
    assert r["fail_reason"] == "RECEIPT_AUTHORITY_MISMATCH"
    assert c.get_account(args=["ACC1"]).call()["balance"] == "1000"


# --- case 6/7: REJECTED and UNDETERMINED stay non-actionable ------------------

def test_rejected_status_stays_non_actionable():
    c = _deploy()
    _funded(c)
    c.register_adjudicator(args=[_adj()]).transact(wait_interval=3000, wait_retries=10)
    _adjudicator_handle(c).submit_decision_receipt(
        args=[_receipt(status="REJECTED")]).transact(wait_interval=3000, wait_retries=10)
    r = c.get_receipt(args=["DEC-1"]).call()
    assert r["actionability"] == "NON_ACTIONABLE"
    assert r["fail_reason"] == "NOT_ACCEPTED"
    assert c.get_account(args=["ACC1"]).call()["balance"] == "1000"


def test_undetermined_status_stays_non_actionable():
    """Fail-closed on UNDETERMINED must not relax because the caller is trusted."""
    c = _deploy()
    _funded(c)
    c.register_adjudicator(args=[_adj()]).transact(wait_interval=3000, wait_retries=10)
    _adjudicator_handle(c).submit_decision_receipt(
        args=[_receipt(status="UNDETERMINED")]).transact(wait_interval=3000, wait_retries=10)
    r = c.get_receipt(args=["DEC-1"]).call()
    assert r["actionability"] == "NON_ACTIONABLE"
    assert r["fail_reason"] == "NOT_ACCEPTED"
    c.admit_proposal(args=[_proposal()]).transact(wait_interval=3000, wait_retries=10)
    try:
        c.get_proposal(args=["PROP-1"]).call()
        exists = True
    except Exception:
        exists = False
    assert exists is False
    assert c.get_account(args=["ACC1"]).call()["balance"] == "1000"


# --- case 8: expired ACCEPTED receipt -> NON_ACTIONABLE -----------------------

def test_expired_accepted_receipt_is_not_actionable():
    c = _deploy()
    _funded(c)
    c.register_adjudicator(args=[_adj()]).transact(wait_interval=3000, wait_retries=10)
    _adjudicator_handle(c).submit_decision_receipt(
        args=[_receipt(created_at="2020-01-01T00:00:00+00:00",
                       expires="2020-02-01T00:00:00+00:00")]).transact(
        wait_interval=3000, wait_retries=10)
    r = c.get_receipt(args=["DEC-1"]).call()
    assert r["actionability"] == "NON_ACTIONABLE"
    assert r["fail_reason"] == "RECEIPT_EXPIRED"
    assert c.get_account(args=["ACC1"]).call()["balance"] == "1000"


# --- case 9: decision replay -> refused ---------------------------------------

def test_replayed_decision_id_is_refused():
    c = _deploy()
    _funded(c)
    c.register_adjudicator(args=[_adj()]).transact(wait_interval=3000, wait_retries=10)
    h = _adjudicator_handle(c)
    h.submit_decision_receipt(args=[_receipt()]).transact(wait_interval=3000, wait_retries=10)

    # same decision_id, different content, must not overwrite or re-become actionable
    tx = h.submit_decision_receipt(
        args=[_receipt(status="REJECTED")]).transact(wait_interval=3000, wait_retries=10)
    assert tx_execution_failed(tx), "replayed decision_id was accepted"

    r = c.get_receipt(args=["DEC-1"]).call()
    assert r["decision_status"] == "ACCEPTED"
    assert r["actionability"] == "ACTIONABLE"


def test_refused_decision_id_is_still_consumed():
    """A refused receipt must not be re-presented under the same id to get a second evaluation."""
    c = _deploy()
    _funded(c)
    c.register_adjudicator(args=[_adj()]).transact(wait_interval=3000, wait_retries=10)
    h = _adjudicator_handle(c)
    # REJECTED consumes DEC-1
    h.submit_decision_receipt(args=[_receipt(status="REJECTED")]).transact(
        wait_interval=3000, wait_retries=10)
    # a later ACCEPTED under the same id must be refused
    tx = h.submit_decision_receipt(args=[_receipt(status="ACCEPTED")]).transact(
        wait_interval=3000, wait_retries=10)
    assert tx_execution_failed(tx), "a consumed decision_id was re-evaluated"
    assert c.get_receipt(args=["DEC-1"]).call()["actionability"] == "NON_ACTIONABLE"


# --- registry surface --------------------------------------------------------

def test_registry_rejects_duplicate_registration():
    c = _deploy()
    c.register_adjudicator(args=[_adj()]).transact(wait_interval=3000, wait_retries=10)
    tx = c.register_adjudicator(args=[_adj()]).transact(wait_interval=3000, wait_retries=10)
    assert tx_execution_failed(tx), "duplicate adjudicator registration was accepted"


def test_non_owner_cannot_register_adjudicator():
    c = _deploy()
    c.register_adjudicator(args=[_adj()]).transact(wait_interval=3000, wait_retries=10)
    tx = c.connect(OTHER).register_adjudicator(args=[_adj(source=OTHER_ADDR)]).transact(
        wait_interval=3000, wait_retries=10)
    assert tx_execution_failed(tx), "non-owner registered an adjudicator"


def test_revocation_does_not_rewrite_prior_receipts():
    """Revocation affects future receipts only; admitted history keeps its provenance."""
    c = _deploy()
    _funded(c)
    c.register_adjudicator(args=[_adj()]).transact(wait_interval=3000, wait_retries=10)
    _adjudicator_handle(c).submit_decision_receipt(
        args=[_receipt()]).transact(wait_interval=3000, wait_retries=10)
    c.revoke_adjudicator(args=[ADJ_ADDR]).transact(wait_interval=3000, wait_retries=10)

    r = c.get_receipt(args=["DEC-1"]).call()
    assert r["origin_status"] == "BOUND", "prior receipt provenance was rewritten"
    assert r["actionability"] == "ACTIONABLE"
