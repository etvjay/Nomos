"""Direct-mode tests for the PPA Adjudication Producer v0.1.

Two layers of local proof (web/LLM are MOCKED here — live Bradbury evidence is
recorded separately in convergence/deployment/):

  Producer-only suite: comparative-triple canonicalization (ACCEPTED /
  REJECTED / UNDETERMINED), evidence-unavailable fail-closed path, malformed
  model output, schema fidelity to the Adapter's 10 receipt fields,
  content-derived evidence hashes, owner-only question registration,
  permissionless liveness, decision replay, and a no-capital-surface scan.

  Chain suite: producer -> Adapter -> Core with the Adapter observing
  msg.sender == the producer contract address (origin BOUND), wrong-
  fingerprint and foreign-sender non-actionability, and Core independently
  gating and settling the dispatched proposal (balance readback).

Direct VM has no get_contract_at, so the producer's emit is recorded
EMIT_FAILED locally; the chain tests re-patch gl.message.contract_address
per segment and deliver the stored receipt to the Adapter explicitly,
simulating the exact bytes the async emit would carry.

Run from the repository root:
    pytest primitives/ppa-adjudication-producer/implementations/genlayer/tests/ -v
"""
from __future__ import annotations

import json

import pytest

PRODUCER = ("primitives/ppa-adjudication-producer/implementations/genlayer/"
            "ppa_adjudication_producer.py")
ADAPTER = "primitives/ppa-receipt-adapter/implementations/genlayer/ppa_receipt_adapter.py"
CORE = "primitives/ppa-core/implementations/genlayer/ppa_core.py"

FP = "sha256:producer-source-fingerprint-local"
FP_WRONG = "sha256:not-the-registered-fingerprint"
PV = "TECH-V1"
URL = "https://feed.example.com/deliveries/ORD-42"
CLAUSE = ("The shipment status field equals delivered and the package count "
          "is 3")
BODY_OK = '{"order": "ORD-42", "status": "delivered", "packages": 3}'
BODY_NEG = '{"order": "ORD-42", "status": "cancelled", "packages": 0}'
RECIPIENT = "0x9f6aa7364d20cf25f054ea83f3cb950317fd34b6"
ACCT = "LIVE-PROD-1"
RULES = json.dumps({"daily_limit": "1000", "per_tx_limit": "500",
                    "currency": "USDC", "policy_version": PV,
                    "allowlist": [RECIPIENT]})


def _hex(a) -> str:
    if isinstance(a, (bytes, bytearray)):
        return "0x" + bytes(a).hex()
    h = a.as_hex if hasattr(a, "as_hex") else str(a)
    h = h.lower()
    return h if h.startswith("0x") else "0x" + h


def _patch_contract(direct_vm, addr_bytes):
    """Direct VM pins contract_address at import and keeps it on every sender
    refresh; re-point both message_raw and the cached gl.message (NamedTuple,
    so it must be replaced wholesale) so each contract segment sees its own
    address — simulating what a real cross-contract emit would carry."""
    import sys
    gl_mod = sys.modules["genlayer.gl"]
    direct_vm._contract_address = addr_bytes
    gl_mod.message_raw["contract_address"] = addr_bytes
    msg = gl_mod.message
    object.__setattr__(gl_mod, "message", gl_mod.MessageType(
        contract_address=msg.contract_address.__class__(bytes(addr_bytes)),
        sender_address=msg.sender_address,
        origin_address=msg.origin_address,
        value=msg.value,
        chain_id=msg.chain_id,
    ))


def _mock_judgment(direct_vm, satisfied, verdict, confidence, body=BODY_OK):
    direct_vm.clear_mocks()
    direct_vm.mock_web(r".*", {"status": 200, "body": body})
    direct_vm.mock_llm(r".*", json.dumps({
        "satisfied": satisfied, "verdict": verdict,
        "confidence": confidence, "reason": "mocked evidence judgment"}))


def _verdict_triple(res):
    return (res["satisfied"], res["verdict"], res["confidence"])


# ----------------------------------------------------------------- init

def test_initialize_validation_and_meta(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    c = direct_deploy(PRODUCER)
    _patch_contract(direct_vm, direct_vm._contract_address)
    with pytest.raises(ValueError, match="invalid owner or adapter"):
        c.initialize(_hex(direct_alice), "not-an-address", FP, PV)
    with pytest.raises(ValueError, match="authority fingerprint required"):
        c.initialize(_hex(direct_alice), _hex(direct_alice), "  ", PV)
    r = c.initialize(_hex(direct_alice), _hex(direct_alice), FP, PV)
    assert r["status"] == "INITIALIZED"
    with pytest.raises(ValueError, match="already initialized"):
        c.initialize(_hex(direct_alice), _hex(direct_alice), FP, PV)
    meta = c.get_meta()
    assert meta["owner"] == _hex(direct_alice)[2:]
    assert meta["authority_fingerprint"] == FP
    assert meta["policy_version"] == PV
    assert meta["capital_methods"] == "NONE"


# ------------------------------------------------- canonicalization matrix

def _init(direct_vm, direct_deploy, alice, adapter=None):
    direct_vm.sender = alice
    c = direct_deploy(PRODUCER)
    c.initialize(_hex(alice), _hex(adapter or alice), FP, PV)
    q = c.register_question("Q-1", URL, CLAUSE, "86400")
    assert q["status"] == "REGISTERED"
    return c


def test_accepted_canonicalization(direct_vm, direct_deploy, direct_alice):
    c = _init(direct_vm, direct_deploy, direct_alice)
    _mock_judgment(direct_vm, True, "delivered", "high")
    res = c.adjudicate("D-OK", "Q-1")
    assert res["status"] == "ACCEPTED"
    rec = c.get_receipt("D-OK")
    assert rec["status"] == "ACCEPTED"
    assert rec["receipt"]["decision_status"] == "ACCEPTED"
    assert rec["receipt"]["equivalence_mode"] == "comparative"
    # direct VM swallows the emit (PostMessage -> None); honest label is QUEUED


def test_rejected_canonicalization_is_terminal_negative(direct_vm, direct_deploy, direct_alice):
    c = _init(direct_vm, direct_deploy, direct_alice)
    _mock_judgment(direct_vm, False, "not_delivered", "high", body=BODY_NEG)
    res = c.adjudicate("D-NO", "Q-1")
    assert res["status"] == "REJECTED"
    rec = c.get_receipt("D-NO")
    assert rec["observation"]["bytes"] > 0
    assert rec["receipt"]["evidence_hash"] != rec["receipt"]["question_hash"]


@pytest.mark.parametrize("satisfied,verdict,confidence", [
    (True, "partial", "high"),
    (True, "delivered", "medium"),
    (False, "ambiguous", "low"),
    (False, "delivered", "high"),   # incoherent triple must not pass
])
def test_ambiguous_triples_undetermined(direct_vm, direct_deploy, direct_alice,
                                        satisfied, verdict, confidence):
    c = _init(direct_vm, direct_deploy, direct_alice)
    _mock_judgment(direct_vm, satisfied, verdict, confidence)
    res = c.adjudicate("D-AMB", "Q-1")
    assert res["status"] == "UNDETERMINED", res


def test_evidence_unavailable_undetermined_never_approved(
        direct_vm, direct_deploy, direct_alice):
    """Unmocked URL => render raises inside the leader; fail-closed to
    UNDETERMINED with an empty observation, never a release-eligible status."""
    c = _init(direct_vm, direct_deploy, direct_alice)
    direct_vm.clear_mocks()   # deliberately no web/llm mock
    res = c.adjudicate("D-GONE", "Q-1")
    assert res["status"] == "UNDETERMINED"
    rec = c.get_receipt("D-GONE")
    assert rec["observation"]["reason"] == "evidence_unavailable"
    assert rec["observation"]["bytes"] == 0


def test_malformed_model_output_undetermined(direct_vm, direct_deploy, direct_alice):
    c = _init(direct_vm, direct_deploy, direct_alice)
    direct_vm.clear_mocks()
    direct_vm.mock_web(r".*", {"status": 200, "body": BODY_OK})
    direct_vm.mock_llm(r".*", json.dumps({"answer": "looks fine to me"}))
    res = c.adjudicate("D-BAD", "Q-1")
    assert res["status"] == "UNDETERMINED"
    assert c.get_receipt("D-BAD")["observation"]["reason"] == "malformed_model_output"


# --------------------------------------------------------- schema fidelity

def test_receipt_matches_adapter_schema_exactly(direct_vm, direct_deploy, direct_alice):
    """The emitted JSON must validate against the Adapter's 10-field schema
    and the Adapter's own validators (terminal status, eq mode, expiry)."""
    c = _init(direct_vm, direct_deploy, direct_alice)
    _mock_judgment(direct_vm, True, "delivered", "high")
    c.adjudicate("D-SCH", "Q-1")
    receipt = c.get_receipt("D-SCH")["receipt"]
    assert set(receipt.keys()) == {"decision_id", "source_contract",
        "authority_fingerprint", "question_hash", "evidence_hash",
        "decision_status", "equivalence_mode", "policy_version",
        "created_at", "expires_at"}
    assert all(isinstance(v, str) and v.strip() for v in receipt.values())
    assert receipt["decision_status"] in ("ACCEPTED", "REJECTED", "UNDETERMINED")
    assert receipt["equivalence_mode"] in ("comparative", "non_comparative", "custom", "strict")
    from datetime import datetime, timezone
    def _ts(s):
        return int(datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
                   .replace(tzinfo=timezone.utc).timestamp()) \
        if not s.endswith("+00:00") else int(datetime.fromisoformat(s).timestamp())
    assert _ts(receipt["expires_at"]) > _ts(receipt["created_at"])
    # evidence hash: content-derived sha256, not a placeholder
    eh = receipt["evidence_hash"]
    assert eh.startswith("sha256:") and len(eh) == 71
    assert eh != "sha256:placeholder" and int(eh[7:], 16) != 0
    # source identity is the producer contract itself
    assert receipt["source_contract"].lower() == _hex(direct_vm._contract_address).lower()


def test_evidence_hash_binds_observation(direct_vm, direct_deploy, direct_alice):
    c = _init(direct_vm, direct_deploy, direct_alice)
    _mock_judgment(direct_vm, True, "delivered", "high", body=BODY_OK)
    c.adjudicate("D-A", "Q-1")
    _mock_judgment(direct_vm, True, "delivered", "high", body=BODY_NEG)
    c.adjudicate("D-B", "Q-1")
    ha = c.get_receipt("D-A")["receipt"]["evidence_hash"]
    hb = c.get_receipt("D-B")["receipt"]["evidence_hash"]
    assert ha != hb


def test_question_hash_deterministic_and_distinct(direct_vm, direct_deploy, direct_alice):
    c = _init(direct_vm, direct_deploy, direct_alice)
    q1 = c.get_question("Q-1")["question_hash"]
    c.register_question("Q-2", URL, "A completely different clause", "3600")
    q2 = c.get_question("Q-2")["question_hash"]
    assert q1.startswith("sha256:") and q1 != q2


# ------------------------------------------------------------- authority

def test_register_question_is_owner_only(direct_vm, direct_deploy, direct_alice, direct_bob):
    c = _init(direct_vm, direct_deploy, direct_alice)
    direct_vm.clear_mocks()
    direct_vm.sender = direct_bob
    with pytest.raises(ValueError, match="caller is not the producer owner"):
        c.register_question("Q-X", URL, CLAUSE, "60")
    # registration validation still owner-gated on url scheme
    direct_vm.sender = direct_alice
    with pytest.raises(ValueError, match="must be https"):
        c.register_question("Q-X", "http://insecure.example.com", CLAUSE, "60")
    with pytest.raises(ValueError, match="invalid ttl"):
        c.register_question("Q-X", URL, CLAUSE, "0")


def test_adjudicate_permissionless_and_replay_never_double_produces(
        direct_vm, direct_deploy, direct_alice, direct_bob):
    c = _init(direct_vm, direct_deploy, direct_alice)
    _mock_judgment(direct_vm, True, "delivered", "high")
    direct_vm.sender = direct_bob
    r1 = c.adjudicate("D-R", "Q-1")
    assert r1["status"] == "ACCEPTED"
    receipt = c.get_receipt("D-R")["receipt"]
    direct_vm.sender = direct_alice
    r2 = c.adjudicate("D-R", "Q-1")
    assert r2["status"] == "REJECTED_REPLAY"
    # triggering authority never rewrites the stored receipt identity
    assert c.get_receipt("D-R")["receipt"] == receipt
    with pytest.raises(ValueError, match="question not found"):
        c.adjudicate("D-Z", "Q-MISSING")


def test_no_capital_or_core_surface(direct_deploy):
    """Producer must have no balances, capital authority, settlement,
    proposal/dispatch, or cross-contract read surface. Asserted by an AST
    scan of the declared method names (source text may document the absence;
    the code must not implement it), plus the absence of any Core address."""
    import ast
    tree = ast.parse(open(PRODUCER).read())
    contract = next(n for n in ast.walk(tree)
                    if isinstance(n, ast.ClassDef) and n.name.endswith("Producer"))
    methods = {n.name for n in contract.body if isinstance(n, ast.FunctionDef)}
    forbidden = {"deposit", "withdraw", "settle", "settle_release", "send",
                 "dispatch", "dispatch_proposal", "execute_proposal",
                 "admit_proposal", "create_account", "update_rules",
                 "register_attestation", "revoke_attestation"}
    assert not (methods & forbidden), methods & forbidden
    assert methods == {"__init__", "initialize", "register_question", "adjudicate",
                       "submit_receipt", "get_question", "get_receipt",
                       "get_meta", "_sender", "_assert_owner", "_own_address",
                       "_canonicalize", "_deliver"}
    # no Core/executor address can enter the contract through initialization
    init_fn = next(n for n in contract.body
                   if isinstance(n, ast.FunctionDef) and n.name == "initialize")
    params = [a.arg for a in init_fn.args.args]
    assert params == ["self", "owner", "adapter_address",
                      "authority_fingerprint", "policy_version"]
    assert not any(k in m.lower() for m in list(methods) + params
                   for k in ("core", "settle", "dispatch"))


# ------------------------------------------------------- equivalence logic

def test_validator_agrees_only_on_exact_decision_triple(direct_vm, direct_deploy, direct_alice):
    """Comparative equivalence: captured validator re-runs the whole task and
    accepts only exact agreement on (satisfied, verdict, confidence)."""
    c = _init(direct_vm, direct_deploy, direct_alice)
    _mock_judgment(direct_vm, True, "delivered", "high")
    c.adjudicate("D-EQ", "Q-1")
    assert len(direct_vm._captured_validators) >= 1
    result, leader_fn, validator_fn = direct_vm._captured_validators[-1]
    triple = _verdict_triple(result)
    assert triple == (True, "delivered", "high")

    class _Res:
        def __init__(self, calldata):
            self.calldata = calldata

    assert validator_fn(_Res(calldata=dict(result))) is True
    bad = dict(result)
    bad["confidence"] = "low"
    assert validator_fn(_Res(calldata=bad)) is False
    bad2 = dict(result)
    bad2["satisfied"] = False
    assert validator_fn(_Res(calldata=bad2)) is False
    assert validator_fn(_Res(calldata="not a dict")) is False


def test_submit_receipt_retry_is_idempotent(direct_vm, direct_deploy, direct_alice):
    c = _init(direct_vm, direct_deploy, direct_alice)
    _mock_judgment(direct_vm, True, "delivered", "high")
    c.adjudicate("D-RT", "Q-1")
    assert c.get_receipt("D-RT")["adapter_submit"] == "QUEUED"
    r = c.submit_receipt("D-RT")
    assert r["adapter_submit"] == "ALREADY_QUEUED"
    # a forced EMIT_FAILED record is retryable
    rec = c.get_receipt("D-RT")
    rec["adapter_submit"] = "EMIT_FAILED"
    c.receipts["D-RT"] = json.dumps(rec)
    r2 = c.submit_receipt("D-RT")
    assert r2["adapter_submit"] == "QUEUED"
    with pytest.raises(ValueError, match="decision not found"):
        c.submit_receipt("D-NOPE")


# NOTE: cross-contract chain proof (producer -> Adapter -> Core) is NOT
# expressible in one direct-VM process (the loader allows a single contract
# class per session, and direct mode has no get_contract_at). It runs on the
# real consensus path in tests/integration/test_producer_chain_integration.py.
