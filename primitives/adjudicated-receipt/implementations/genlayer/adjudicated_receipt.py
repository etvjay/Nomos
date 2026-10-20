# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
# }
"""Adjudicated Receipt primitive (GenLayer) v0.2 — IMPLEMENTING.

The GenLayer-native settlement lock with a full release lifecycle. Validator
quorum judgment over tx-time external evidence is the ONLY path to release
value; the ONLY release is the single registered surrender value, once, and
only after a challenge window has passed without a successful challenge.

Lifecycle:

    register_release (owner)          -> obligation identity, immutable terms,
                                         evidence pointer, clause, TTL, challenge
                                         window, policy version, source id
    adjudicate_object (anyone)        -> leader fetch + LLM verdict + validator
                                         quorum -> PROVISIONAL_ACCEPTED |
                                         REJECTED | UNDETERMINED_* (+ evidence
                                         observations recorded, not voted)
    challenge_release (anyone)        -> during the challenge window, with a
                                         recorded bond + counterevidence ->
                                         CHALLENGED (frozen)
    resolve_challenge (owner)         -> upheld (terminal non-acceptance) |
                                         dismissed (back to PROVISIONAL)
    finalize_release (anyone)         -> window passed, unchallenged, evidence
                                         fresh -> FINAL_ACCEPTED | EXPIRED
    settle_release (owner)            -> exactly once against FINAL_ACCEPTED
    cancel_release (owner)            -> OPEN object with no live final path ->
                                         CANCELLED (defined cancellation rule)

JUDGMENT BOUNDARY: exactly one nondeterministic operation —
adjudicate_object's (satisfied, verdict, confidence) triple over evidence
fetched in-transaction from the registered evidence_pointer. Consensus is
exact-field agreement over that triple; ACCEPTED additionally requires
(satisfied=true, verdict=delivered, confidence=high). Evidence observations
(retrieval time, byte count, bounded excerpt) are recorded as observations
and are NOT consensus fields. REJECTED/UNDETERMINED receipts are terminal
evidence that can never authorize release; they are not implicit refunds —
cancellation and expiry have their own explicit rules. Judgment cannot move
capital, widen limits, override revocation, or rewrite history.

v0.2 additions over v0.1 (research-driven, see research/adjudicated-receipt/):
P0-1 provisional acceptance + challenge window; P0-2 immutable obligation
hash (terms + clause + policy version) + evidence observations (retrieval
time, byte count, excerpt, expected source id). Deliberately still v0.x:
cross-validator content-hash equality, deterministic source-signature
pre-checks, bond escrow/slashing, and escalation committees remain
documented NOT_IMPLEMENTED surfaces.
"""

import json
import typing

from genlayer import *


def _now_iso() -> str:
    """Transaction timestamp as ISO string."""
    dt = getattr(gl.message, "datetime", None)
    if dt:
        return dt
    return gl.message_raw["datetime"]


def _ts(iso: str) -> int:
    """Parse an ISO-8601 timestamp string to epoch seconds."""
    import datetime
    txt = iso.strip().replace("Z", "+00:00")
    return int(datetime.datetime.fromisoformat(txt).timestamp())


def _valid_addr(a: str) -> bool:
    return isinstance(a, str) and a.startswith("0x") and len(a) == 42


def _valid_id(i) -> bool:
    return isinstance(i, str) and 0 < len(i) <= 64


def _positive_uint(s: str) -> bool:
    return isinstance(s, str) and s.isdigit() and len(s) <= 39 and int(s) > 0


_HIGH = "high"
_VERDICTS = ("delivered", "partial", "not_delivered", "ambiguous")
_CHALLENGE_RESOLUTIONS = ("upheld", "dismissed")


def _obligation_hash(inv: dict) -> str:
    """Deterministic in-contract binding of the immutable obligation version:
    any substitution of terms, clause, policy version, or evidence pointer
    changes the hash and breaks receipt binding. (Not a cryptographic hash;
    cross-validator content hashing is a documented future surface.)"""
    return "|".join([
        inv["invoice_id"], inv["object_ref"], inv["surrender_value"],
        inv["surrender_asset"], inv["evidence_pointer"],
        inv["adjudication_clause"], inv["policy_version"],
        inv["expected_source_id"],
    ])


class AdjudicatedReceipt(gl.Contract):
    owner: TreeMap[str, str]        # "owner" -> address; "created" -> ISO time
    objects: TreeMap[str, str]      # invoice_id -> json registered release object
    receipts: TreeMap[str, str]     # receipt_id -> json adjudication receipt
    releases: TreeMap[str, str]     # payment_id ("pay-" + receipt_id) -> json release record
    challenges: TreeMap[str, str]   # receipt_id -> json challenge record

    def __init__(self) -> None:
        pass

    @gl.public.write
    def initialize(self, owner: str) -> str:
        """One-time owner registration. Owner registers objects, resolves
        challenges, settles releases, and cancels objects."""
        if self.owner.get("owner"):
            raise ValueError("AdjudicatedReceipt: already initialized")
        if not _valid_addr(owner):
            raise ValueError("AdjudicatedReceipt: invalid owner address")
        self.owner["owner"] = owner.lower().removeprefix("0x")
        self.owner["created"] = _now_iso()
        return "initialized"

    def _sender(self) -> str:
        return gl.message.sender_address.as_hex.lower().removeprefix("0x")

    def _assert_owner(self) -> None:
        if self._sender() != self.owner.get("owner"):
            raise ValueError("AdjudicatedReceipt: caller is not the account owner")

    def _get_object(self, invoice_id: str) -> dict:
        raw = self.objects.get(invoice_id)
        if not raw:
            raise ValueError("AdjudicatedReceipt: release object not found")
        return json.loads(raw)

    def _evidence_expiry(self, inv: dict) -> int:
        return _ts(inv["registered_at"]) + int(inv["valid_for_seconds"])

    # ---------- registration (owner, deterministic) ----------

    @gl.public.write
    def register_release(
        self,
        invoice_id: str,
        object_ref: str,
        surrender_value: str,
        surrender_asset: str,
        evidence_pointer: str,
        adjudication_clause: str,
        valid_for_seconds: str,
        challenge_window: str,
        policy_version: str,
        expected_source_id: str,
    ) -> str:
        """Owner binds a release object to the exact evidence pointer the
        validators must fetch, the clause they must judge, an evidence TTL,
        and a challenge window, under a declared policy version and expected
        source identity. Registration creates obligation identity only —
        no capital, policy, delegation, or settlement authority."""
        self._assert_owner()
        if not _valid_id(invoice_id) or self.objects.get(invoice_id):
            raise ValueError("AdjudicatedReceipt: invalid or duplicate object id")
        if not object_ref:
            raise ValueError("AdjudicatedReceipt: object_ref required")
        if not _positive_uint(surrender_value):
            raise ValueError("AdjudicatedReceipt: invalid surrender value")
        if not surrender_asset:
            raise ValueError("AdjudicatedReceipt: surrender asset required")
        if not evidence_pointer.startswith("https://"):
            raise ValueError("AdjudicatedReceipt: evidence_pointer must be https")
        if not adjudication_clause:
            raise ValueError("AdjudicatedReceipt: clause required")
        if not _positive_uint(valid_for_seconds):
            raise ValueError("AdjudicatedReceipt: invalid evidence TTL")
        if not _positive_uint(challenge_window):
            raise ValueError("AdjudicatedReceipt: invalid challenge window")
        if not policy_version:
            raise ValueError("AdjudicatedReceipt: policy version required")
        if not isinstance(expected_source_id, str):
            raise ValueError("AdjudicatedReceipt: expected_source_id must be a string")
        inv = {
            "invoice_id": invoice_id,
            "object_ref": object_ref,
            "surrender_value": surrender_value,
            "surrender_asset": surrender_asset,
            "evidence_pointer": evidence_pointer,
            "adjudication_clause": adjudication_clause,
            "registered_at": _now_iso(),
            "valid_for_seconds": str(int(valid_for_seconds)),
            "challenge_window": str(int(challenge_window)),
            "policy_version": policy_version,
            "expected_source_id": expected_source_id,
            "status": "OPEN",
        }
        inv["obligation_hash"] = _obligation_hash(inv)
        self.objects[invoice_id] = json.dumps(inv)
        return "release_registered"

    # ---------- adjudication (permissionless, GenLayer-nondeterministic) ----------

    @gl.public.write
    def adjudicate_object(self, invoice_id: str, receipt_id: str) -> typing.Any:
        """Run validator-quorum adjudication over the registered evidence
        pointer. ANY caller may trigger a tick (liveness); triggering confers
        no release right. Deterministic preconditions run first; the single
        declared nondeterministic operation produces a canonical receipt.
        Without GenLayer quorum judgment there is no trigger at all."""
        if not _valid_id(receipt_id) or self.receipts.get(receipt_id):
            raise ValueError("AdjudicatedReceipt: invalid or duplicate receipt id")
        inv = self._get_object(invoice_id)
        if inv["status"] != "OPEN":
            raise ValueError("AdjudicatedReceipt: release object not open")
        url = inv["evidence_pointer"]
        clause = inv["adjudication_clause"]

        def leader_fn() -> typing.Any:
            evidence = gl.nondet.web.render(url, mode="text")
            task = (
                f"External evidence fetched at adjudication time from {url}:\n"
                f"{evidence[:5000]}\n\n"
                f"Clause to judge: {clause}\n\n"
                "Decide whether the evidence satisfies the clause for releasing "
                "this object. Respond ONLY as JSON: "
                '{"satisfied": true/false, '
                '"verdict": "delivered|partial|not_delivered|ambiguous", '
                '"confidence": "high|medium|low", '
                '"reason": "<1 sentence>"}. '
                "If evidence is missing, stale, or unclear, respond satisfied=false "
                "verdict=ambiguous confidence=low."
            )
            return gl.nondet.exec_prompt(task, response_format="json")

        def validator_fn(leaders_res) -> bool:
            # Independent re-judgment: the validator re-fetches and re-judges.
            mine = leader_fn()
            try:
                theirs = leaders_res.calldata
            except Exception:
                return False
            if not isinstance(mine, dict) or not isinstance(theirs, dict):
                return False
            for field in ("satisfied", "verdict", "confidence"):
                if mine.get(field) != theirs.get(field):
                    return False
            state = mine.get("verdict")
            if not isinstance(state, str) or state not in _VERDICTS:
                return False
            return True

        res = gl.vm.run_nondet(leader_fn, validator_fn)
        return self._record_receipt(inv, receipt_id, res)

    def _record_receipt(self, inv: dict, receipt_id: str, res) -> dict:
        """Deterministic postcondition: canonicalize any nondet outcome into
        an immutable, obligation-bound receipt. Ambiguous or malformed model
        output becomes UNDETERMINED — never approval. An accepted verdict is
        PROVISIONAL until the challenge window passes."""
        base = {
            "receipt_id": receipt_id,
            "invoice_id": inv["invoice_id"],
            "obligation_hash": inv["obligation_hash"],
            "evidence_pointer": inv["evidence_pointer"],
            "expected_source_id": inv["expected_source_id"],
            "retrieval_time": _now_iso(),
            "at": _now_iso(),
            "policy_version": inv["policy_version"],
            "consumed": "false",
        }
        if (
            not isinstance(res, dict)
            or not isinstance(res.get("satisfied"), bool)
            or not isinstance(res.get("verdict"), str)
            or res.get("verdict") not in _VERDICTS
            or not isinstance(res.get("confidence"), str)
        ):
            base["status"] = "UNDETERMINED"
            base["reason_code"] = "CONSENSUS_UNREACHABLE"
            self.receipts[receipt_id] = json.dumps(base)
            return {"success": False, "status": "UNDETERMINED",
                    "reason": "consensus_unreachable", "receipt_id": receipt_id}

        satisfied = res["satisfied"] is True
        verdict = res["verdict"]
        confidence = res["confidence"]
        if not satisfied:
            base["status"] = "REJECTED"
            base["reason_code"] = "EVIDENCE_NOT_SATISFYING"
            base["verdict"] = verdict
            base["confidence"] = confidence
            self.receipts[receipt_id] = json.dumps(base)
            return {"success": False, "status": "REJECTED",
                    "reason": "evidence_not_satisfying",
                    "verdict": verdict, "confidence": confidence,
                    "receipt_id": receipt_id}

        if verdict != "delivered" or confidence != _HIGH:
            base["status"] = "UNDETERMINED_DELIVERY_UNCERTAIN"
            base["reason_code"] = "DELIVERY_UNCERTAIN"
            base["verdict"] = verdict
            base["confidence"] = confidence
            self.receipts[receipt_id] = json.dumps(base)
            return {"success": False, "status": "UNDETERMINED_DELIVERY_UNCERTAIN",
                    "reason": "delivery_uncertain",
                    "verdict": verdict, "confidence": confidence,
                    "receipt_id": receipt_id}

        # Provisional acceptance: no release authority exists until the
        # challenge window passes unchallenged (finalize_release).
        base["status"] = "PROVISIONAL_ACCEPTED"
        base["reason_code"] = "QUORUM_DELIVERED_HIGH_CONFIDENCE"
        base["verdict"] = verdict
        base["confidence"] = confidence
        base["challenge_deadline"] = str(
            _ts(_now_iso()) + int(inv["challenge_window"]))
        self.receipts[receipt_id] = json.dumps(base)
        return {"success": True, "status": "PROVISIONAL_ACCEPTED",
                "receipt_id": receipt_id}

    # ---------- challenge window (permissionless challenge, owner resolution) ----------

    @gl.public.write
    def challenge_release(self, receipt_id: str, bond: str,
                          counterevidence_hash: str, reason: str) -> str:
        """During the challenge window, anyone may freeze a provisional
        receipt with a recorded bond and counterevidence hash. The bond is
        a recorded commitment (token escrow/slashing is a documented
        NOT_IMPLEMENTED surface). A challenged receipt cannot settle or
        finalize until the owner resolves the challenge."""
        if not _positive_uint(bond):
            raise ValueError("AdjudicatedReceipt: bond must be a positive uint-string")
        if not counterevidence_hash:
            raise ValueError("AdjudicatedReceipt: counterevidence hash required")
        if not reason:
            raise ValueError("AdjudicatedReceipt: challenge reason required")
        raw = self.receipts.get(receipt_id)
        if not raw:
            raise ValueError("AdjudicatedReceipt: receipt not found")
        rec = json.loads(raw)
        if rec["status"] != "PROVISIONAL_ACCEPTED":
            raise ValueError("AdjudicatedReceipt: receipt is not provisionally accepted")
        if self.challenges.get(receipt_id):
            raise ValueError("AdjudicatedReceipt: receipt already challenged")
        if _ts(_now_iso()) > int(rec["challenge_deadline"]):
            raise ValueError("AdjudicatedReceipt: challenge window closed")
        challenge = {
            "receipt_id": receipt_id,
            "challenger": self._sender(),
            "bond": bond,
            "counterevidence_hash": counterevidence_hash,
            "reason": reason,
            "at": _now_iso(),
            "status": "OPEN",
        }
        self.challenges[receipt_id] = json.dumps(challenge)
        rec["status"] = "CHALLENGED"
        self.receipts[receipt_id] = json.dumps(rec)
        return "challenged"

    @gl.public.write
    def resolve_challenge(self, receipt_id: str, resolution: str) -> typing.Any:
        """Owner resolves a challenge: `upheld` keeps the receipt frozen as
        terminal non-acceptance (bond forfeiture recorded; escalation to a
        review committee is a documented future surface); `dismissed`
        returns the receipt to PROVISIONAL_ACCEPTED (deadline unchanged)."""
        self._assert_owner()
        if resolution not in _CHALLENGE_RESOLUTIONS:
            raise ValueError("AdjudicatedReceipt: unknown resolution")
        challenge = self.challenges.get(receipt_id)
        if not challenge:
            raise ValueError("AdjudicatedReceipt: challenge not found")
        chal = json.loads(challenge)
        if chal["status"] != "OPEN":
            raise ValueError("AdjudicatedReceipt: challenge already resolved")
        raw = self.receipts.get(receipt_id)
        rec = json.loads(raw)
        if rec["status"] != "CHALLENGED":
            raise ValueError("AdjudicatedReceipt: receipt is not challenged")
        chal["status"] = "RESOLVED"
        chal["resolution"] = resolution
        chal["resolved_at"] = _now_iso()
        if resolution == "upheld":
            chal["bond_disposition"] = "FORFEITED"
            # Receipt stays CHALLENGED: terminal non-acceptance. This is not
            # an implicit refund — cancellation/refund rules are separate.
        else:
            chal["bond_disposition"] = "RETURNED"
            rec["status"] = "PROVISIONAL_ACCEPTED"
            self.receipts[receipt_id] = json.dumps(rec)
        self.challenges[receipt_id] = json.dumps(chal)
        return {"success": True, "status": rec["status"], "resolution": resolution,
                "bond_disposition": chal["bond_disposition"], "receipt_id": receipt_id}

    # ---------- finalization (permissionless, deterministic) ----------

    @gl.public.write
    def finalize_release(self, receipt_id: str) -> typing.Any:
        """Promote a provisional receipt after its challenge window passes:
        unchallenged + evidence still fresh -> FINAL_ACCEPTED; evidence TTL
        expired -> EXPIRED (defined expiry rule; not an implicit refund).
        Anyone may call; permissionless timeouts must not depend on an
        unpaid volunteer (research: keeper/idleness economics)."""
        raw = self.receipts.get(receipt_id)
        if not raw:
            raise ValueError("AdjudicatedReceipt: receipt not found")
        rec = json.loads(raw)
        if rec["status"] != "PROVISIONAL_ACCEPTED":
            raise ValueError("AdjudicatedReceipt: receipt is not provisionally accepted")
        inv = self._get_object(rec["invoice_id"])
        if inv["status"] != "OPEN":
            raise ValueError("AdjudicatedReceipt: release object not open")
        now = _ts(_now_iso())
        if now > self._evidence_expiry(inv):
            rec["status"] = "EXPIRED"
            rec["reason_code"] = "EVIDENCE_TTL_EXPIRED"
            self.receipts[receipt_id] = json.dumps(rec)
            return {"success": False, "status": "EXPIRED", "receipt_id": receipt_id}
        if now <= int(rec["challenge_deadline"]):
            raise ValueError("AdjudicatedReceipt: challenge window still open")
        rec["status"] = "FINAL_ACCEPTED"
        rec["finalized_at"] = _now_iso()
        self.receipts[receipt_id] = json.dumps(rec)
        return {"success": True, "status": "FINAL_ACCEPTED", "receipt_id": receipt_id}

    # ---------- settlement (owner, deterministic, receipt-gated) ----------

    @gl.public.write
    def settle_release(self, receipt_id: str) -> typing.Any:
        """Release exactly once against a FINAL_ACCEPTED receipt. Fail-closed
        ordering: receipt existence -> final acceptance -> consumption ->
        current binding -> freshness. A stale, replayed, or foreign receipt
        can never release; the object stays OPEN for re-adjudication.
        Settlement records the surrender value as a release obligation —
        it moves no tokens (token rails are a downstream NOT_IMPLEMENTED)."""
        self._assert_owner()
        raw = self.receipts.get(receipt_id)
        if not raw:
            raise ValueError("AdjudicatedReceipt: receipt not found")
        rec = json.loads(raw)
        if rec["status"] != "FINAL_ACCEPTED":
            raise ValueError("AdjudicatedReceipt: receipt is not FINAL_ACCEPTED")
        if rec.get("consumed") == "true":
            raise ValueError("AdjudicatedReceipt: receipt already consumed")
        inv = self._get_object(rec["invoice_id"])
        if inv["status"] != "OPEN":
            raise ValueError("AdjudicatedReceipt: release object not open")
        if rec.get("obligation_hash") != inv.get("obligation_hash"):
            raise ValueError("AdjudicatedReceipt: receipt/obligation binding mismatch")
        if _ts(_now_iso()) > self._evidence_expiry(inv):
            raise ValueError("AdjudicatedReceipt: evidence TTL expired")

        rec["consumed"] = "true"
        self.receipts[receipt_id] = json.dumps(rec)
        inv["status"] = "SETTLED"
        inv["settled_by_receipt"] = receipt_id
        self.objects[inv["invoice_id"]] = json.dumps(inv)
        payment_id = "pay-" + receipt_id
        self.releases[payment_id] = json.dumps({
            "payment_id": payment_id,
            "invoice_id": inv["invoice_id"],
            "object_ref": inv["object_ref"],
            "to": inv["object_ref"],
            "amount": inv["surrender_value"],
            "asset": inv["surrender_asset"],
            "receipt_id": receipt_id,
            "status": "SETTLED",
            "at": _now_iso(),
        })
        return {"success": True, "status": "SETTLED",
                "payment_id": payment_id, "amount": inv["surrender_value"],
                "asset": inv["surrender_asset"], "to": inv["object_ref"]}

    # ---------- cancellation (owner, deterministic, defined rule) ----------

    @gl.public.write
    def cancel_release(self, invoice_id: str) -> typing.Any:
        """Explicit cancellation of an OPEN object: neither side can exploit
        a failed or contested oracle call by leaving the object open. A
        cancelled object is terminal for adjudication and settlement."""
        self._assert_owner()
        inv = self._get_object(invoice_id)
        if inv["status"] != "OPEN":
            raise ValueError("AdjudicatedReceipt: release object not open")
        inv["status"] = "CANCELLED"
        inv["cancelled_at"] = _now_iso()
        self.objects[invoice_id] = json.dumps(inv)
        return {"success": True, "status": "CANCELLED", "invoice_id": invoice_id}

    # ---------- views ----------

    @gl.public.view
    def get_object(self, invoice_id: str) -> typing.Any:
        return self._get_object(invoice_id)

    @gl.public.view
    def get_receipt(self, receipt_id: str) -> typing.Any:
        raw = self.receipts.get(receipt_id)
        if not raw:
            raise ValueError("AdjudicatedReceipt: receipt not found")
        return json.loads(raw)

    @gl.public.view
    def get_release(self, payment_id: str) -> typing.Any:
        raw = self.releases.get(payment_id)
        if not raw:
            raise ValueError("AdjudicatedReceipt: release not found")
        return json.loads(raw)

    @gl.public.view
    def get_challenge(self, receipt_id: str) -> typing.Any:
        raw = self.challenges.get(receipt_id)
        if not raw:
            raise ValueError("AdjudicatedReceipt: challenge not found")
        return json.loads(raw)
