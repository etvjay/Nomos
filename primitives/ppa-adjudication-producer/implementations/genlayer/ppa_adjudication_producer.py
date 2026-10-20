# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
"""PPA Adjudication Producer (GenLayer) v0.1 — IMPLEMENTING.

A separately-authorized adjudication producer for the PPA Core/Adapter split.
It is the first Nomos component that supplies real GenLayer nondeterministic
judgment behind an Adapter receipt: the owner EOA that opens accounts is no
longer the source of adjudicated truth.

Pipeline (exactly one nondeterministic operation per decision):

    register_question (owner)         -> immutable question identity:
                                         https evidence url + clause + TTL,
                                         deterministic question_hash
    adjudicate (anyone, liveness)     -> leader fetches evidence in-transaction
                                         (gl.nondet.web.render) and runs an LLM
                                         judgment (gl.nondet.exec_prompt);
                                         validators INDEPENDENTLY re-fetch and
                                         re-judge; consensus is exact agreement
                                         on the decision triple
                                         (satisfied, verdict, confidence)
                                         [comparative equivalence]
    canonicalization (deterministic)  -> ACCEPTED only on
                                         (satisfied=true, verdict=delivered,
                                          confidence=high); confident negative
                                         -> REJECTED; anything ambiguous,
                                         low-confidence, malformed, or
                                         evidence-unavailable -> UNDETERMINED.
                                         Judgment can never be silent: every
                                         decision id resolves to one terminal
                                         status before submission.
    evidence binding (deterministic)  -> evidence_hash = sha256 over the
                                         normalized observation envelope
                                         (url, byte count, bounded excerpt,
                                         decision triple, retrieval time).
                                         Content-derived, not a placeholder.
    submission (deterministic emit)   -> the exact 10-field Adapter receipt is
                                         emitted to the registered Adapter's
                                         submit_decision_receipt; the Adapter
                                         observes msg.sender == this contract,
                                         binds origin by source fingerprint,
                                         and decides actionability itself.

BOUNDARY (enforced by absence, verified by interface scan in tests):
    no balances, no deposit/withdraw, no capital or commitment, no Core
    address or call path, no proposal/dispatch/settlement surface. The
    producer only produces receipts. Core independently re-gates every
    bound proposal at dispatch time; a producer ACCEPTED is not money.

Failure/retry rule: a successful emit is recorded as QUEUED (the Adapter's
acceptance is proven by off-chain readback, never claimed from inside); if the
emit call itself raises, the receipt is stored with adapter_submit=EMIT_FAILED
(recorded, not swallowed) and any caller may re-deliver it via
submit_receipt. Re-delivery is idempotent at the Adapter
(replay is rejected there by decision_id).
"""

import hashlib
import json
import typing

from genlayer import *


def _now_iso() -> str:
    dt = getattr(gl.message, "datetime", None)
    if dt:
        return dt
    return gl.message_raw["datetime"]


def _ts(iso: str) -> int:
    import datetime
    txt = iso.strip().replace("Z", "+00:00")
    return int(datetime.datetime.fromisoformat(txt).timestamp())


def _iso(epoch: int) -> str:
    import datetime
    return datetime.datetime.fromtimestamp(
        epoch, tz=datetime.timezone.utc
    ).isoformat().replace("+00:00", "Z")


def _valid_addr(a) -> bool:
    return isinstance(a, str) and a.startswith("0x") and len(a) == 42


def _valid_id(i) -> bool:
    return isinstance(i, str) and 0 < len(i) <= 64


def _positive_uint(s) -> bool:
    return isinstance(s, str) and s.isdigit() and len(s) <= 12 and int(s) > 0


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


_VERDICTS = ("delivered", "partial", "not_delivered", "ambiguous")
_CONFIDENCES = ("high", "medium", "low")
_HIGH = "high"


class PPAAdjudicationProducer(gl.Contract):
    meta: TreeMap[str, str]          # owner, adapter, authority_fingerprint,
                                     # policy_version, created
    questions: TreeMap[str, str]     # question_id -> json question record
    receipts: TreeMap[str, str]      # decision_id -> json receipt record

    # Mirrors PPAReceiptAdapter.RECEIPT_FIELDS exactly (schema fidelity is
    # asserted by the test suite; the Adapter re-validates on receipt).
    RECEIPT_FIELDS = (
        "decision_id", "source_contract", "authority_fingerprint",
        "question_hash", "evidence_hash", "decision_status",
        "equivalence_mode", "policy_version", "created_at", "expires_at",
    )

    def __init__(self) -> None:
        pass

    @gl.public.write
    def initialize(self, owner: str, adapter_address: str,
                   authority_fingerprint: str, policy_version: str) -> typing.Any:
        if self.meta.get("owner"):
            raise ValueError("PPA Producer: already initialized")
        if not _valid_addr(owner) or not _valid_addr(adapter_address):
            raise ValueError("PPA Producer: invalid owner or adapter address")
        if not isinstance(authority_fingerprint, str) or not authority_fingerprint.strip():
            raise ValueError("PPA Producer: authority fingerprint required")
        if not isinstance(policy_version, str) or not policy_version.strip():
            raise ValueError("PPA Producer: policy version required")
        self.meta["owner"] = owner.lower().removeprefix("0x")
        self.meta["adapter"] = adapter_address.lower().removeprefix("0x")
        self.meta["authority_fingerprint"] = authority_fingerprint
        self.meta["policy_version"] = policy_version
        self.meta["created"] = _now_iso()
        return {"status": "INITIALIZED", "adapter": self.meta["adapter"]}

    def _sender(self) -> str:
        return gl.message.sender_address.as_hex.lower().removeprefix("0x")

    def _assert_owner(self) -> None:
        if self._sender() != self.meta.get("owner"):
            raise ValueError("PPA Producer: caller is not the producer owner")

    def _own_address(self) -> str:
        ca = gl.message.contract_address
        if isinstance(ca, (bytes, bytearray)):
            return "0x" + bytes(ca).hex()
        h = ca.as_hex if hasattr(ca, "as_hex") else str(ca)
        h = h.lower()
        return h if h.startswith("0x") else "0x" + h

    # ---------- question identity (owner, deterministic) ----------

    @gl.public.write
    def register_question(self, question_id: str, url: str, clause: str,
                          ttl_seconds: str) -> typing.Any:
        self._assert_owner()
        if not _valid_id(question_id) or self.questions.get(question_id):
            raise ValueError("PPA Producer: invalid or duplicate question id")
        if not isinstance(url, str) or not url.startswith("https://"):
            raise ValueError("PPA Producer: evidence url must be https")
        if not isinstance(clause, str) or not clause.strip() or len(clause) > 512:
            raise ValueError("PPA Producer: clause required (<=512 chars)")
        if not _positive_uint(ttl_seconds):
            raise ValueError("PPA Producer: invalid ttl_seconds")
        qhash = "sha256:" + _sha(json.dumps(
            {"url": url, "clause": clause}, sort_keys=True))
        rec = {
            "question_id": question_id, "url": url, "clause": clause,
            "question_hash": qhash, "ttl_seconds": str(int(ttl_seconds)),
            "created_at": _now_iso(),
        }
        self.questions[question_id] = json.dumps(rec)
        return {"status": "REGISTERED", "question_id": question_id,
                "question_hash": qhash}

    # ---------- adjudication (permissionless, the single nondet surface) ----------

    @gl.public.write
    def adjudicate(self, decision_id: str, question_id: str) -> typing.Any:
        if not _valid_id(decision_id):
            raise ValueError("PPA Producer: invalid decision id")
        if self.receipts.get(decision_id):
            return {"status": "REJECTED_REPLAY", "decision_id": decision_id,
                    "note": "decision already adjudicated"}
        raw = self.questions.get(question_id)
        if not raw:
            raise ValueError("PPA Producer: question not found")
        q = json.loads(raw)
        url = q["url"]
        clause = q["clause"]

        def leader_fn() -> dict:
            try:
                fetched = gl.nondet.web.render(url, mode="text")
                text = fetched if isinstance(fetched, str) else str(fetched)
            except Exception:
                return {"satisfied": False, "verdict": "ambiguous",
                        "confidence": "low", "reason": "evidence_unavailable",
                        "excerpt": "", "bytes": 0}
            prompt = (
                f"External evidence fetched at adjudication time from {url}:\n"
                f"{text[:5000]}\n\n"
                f"Clause to judge: {clause}\n\n"
                "Decide whether this evidence satisfies the clause. Respond "
                "ONLY as JSON: {\"satisfied\": true/false, \"verdict\": "
                "\"delivered|partial|not_delivered|ambiguous\", "
                "\"confidence\": \"high|medium|low\", \"reason\": \"<1 sentence>\"}. "
                "If evidence is missing, stale, off-topic, or unclear, respond "
                "satisfied=false verdict=ambiguous confidence=low."
            )
            res = gl.nondet.exec_prompt(prompt, response_format="json")
            if not isinstance(res, dict) or not (
                    "satisfied" in res or "verdict" in res):
                return {"satisfied": False, "verdict": "ambiguous",
                        "confidence": "low", "reason": "malformed_model_output",
                        "excerpt": text[:200], "bytes": len(text)}
            satisfied = res.get("satisfied") is True
            verdict = res.get("verdict")
            if not isinstance(verdict, str) or verdict not in _VERDICTS:
                verdict = "ambiguous"
            confidence = res.get("confidence")
            if not isinstance(confidence, str) or confidence not in _CONFIDENCES:
                confidence = "low"
            return {"satisfied": satisfied, "verdict": verdict,
                    "confidence": confidence,
                    "excerpt": text[:200], "bytes": len(text)}

        def validator_fn(leaders_res) -> bool:
            mine = leader_fn()
            try:
                theirs = leaders_res.calldata
            except Exception:
                return False
            if not isinstance(mine, dict) or not isinstance(theirs, dict):
                return False
            for field in ("satisfied", "verdict", "confidence"):
                if mine.get(field) is None or theirs.get(field) is None:
                    return False
                if mine[field] != theirs[field]:
                    return False
            if mine["verdict"] not in _VERDICTS or mine["confidence"] not in _CONFIDENCES:
                return False
            return True

        res = gl.vm.run_nondet(leader_fn, validator_fn)
        record = self._canonicalize(q, decision_id, res)
        return self._deliver(decision_id, record)

    def _canonicalize(self, q: dict, decision_id: str, res) -> dict:
        """Deterministic postcondition: exactly one terminal status, bound to
        the question and a content-derived evidence hash."""
        now = _now_iso()
        accepted = (
            isinstance(res, dict)
            and res.get("satisfied") is True
            and res.get("verdict") == "delivered"
            and res.get("confidence") == _HIGH
        )
        rejected = (
            isinstance(res, dict)
            and res.get("satisfied") is False
            and res.get("verdict") == "not_delivered"
            and res.get("confidence") == _HIGH
        )
        if accepted:
            status = "ACCEPTED"
        elif rejected:
            status = "REJECTED"
        else:
            status = "UNDETERMINED"
        envelope = json.dumps({
            "url": q["url"],
            "bytes": res.get("bytes") if isinstance(res, dict) else None,
            "excerpt": (res.get("excerpt") or "")[:200] if isinstance(res, dict) else None,
            "satisfied": res.get("satisfied") if isinstance(res, dict) else None,
            "verdict": res.get("verdict") if isinstance(res, dict) else None,
            "confidence": res.get("confidence") if isinstance(res, dict) else None,
            "retrieved_at": now,
        }, sort_keys=True)
        evidence_hash = "sha256:" + _sha(envelope)
        created_at = now
        expires_at = _iso(_ts(q["created_at"]) + int(q["ttl_seconds"]))
        receipt = {
            "decision_id": decision_id,
            "source_contract": self._own_address(),
            "authority_fingerprint": self.meta["authority_fingerprint"],
            "question_hash": q["question_hash"],
            "evidence_hash": evidence_hash,
            "decision_status": status,
            "equivalence_mode": "comparative",
            "policy_version": self.meta["policy_version"],
            "created_at": created_at,
            "expires_at": expires_at,
        }
        record = {"receipt": receipt, "status": status,
                  "question_id": q["question_id"],
                  "observation": {
                      "reason": res.get("reason") if isinstance(res, dict) else "consensus_unreachable",
                      "bytes": res.get("bytes") if isinstance(res, dict) else 0,
                      "excerpt": (res.get("excerpt") or "")[:200] if isinstance(res, dict) else "",
                  },
                  "adjudicated_at": now, "adapter_submit": "PENDING"}
        self.receipts[decision_id] = json.dumps(record)
        return record

    # ---------- delivery to the Adapter (deterministic, retryable) ----------

    def _deliver(self, decision_id: str, record: dict) -> typing.Any:
        adapter = self.meta.get("adapter")
        try:
            target = gl.get_contract_at(Address("0x" + adapter))
            target.emit(on="accepted").submit_decision_receipt(
                json.dumps(record["receipt"]))
            # The emit is queued for async delivery; this contract cannot
            # observe the Adapter's acceptance from here. Honest label:
            # QUEUED, verified by the Adapter receipt readback (off-chain).
            record["adapter_submit"] = "QUEUED"
        except Exception:
            record["adapter_submit"] = "EMIT_FAILED"
        self.receipts[decision_id] = json.dumps(record)
        return {"success": record["adapter_submit"] == "QUEUED",
                "status": record["status"], "decision_id": decision_id,
                "adapter_submit": record["adapter_submit"]}

    @gl.public.write
    def submit_receipt(self, decision_id: str) -> typing.Any:
        """Re-deliver a stored receipt whose Adapter emit failed before being
        queued. Idempotent at the Adapter: a duplicate decision_id there is
        rejected, never double-acted."""
        raw = self.receipts.get(decision_id)
        if not raw:
            raise ValueError("PPA Producer: decision not found")
        record = json.loads(raw)
        if record.get("adapter_submit") == "QUEUED":
            return {"status": record["status"], "decision_id": decision_id,
                    "adapter_submit": "ALREADY_QUEUED"}
        return self._deliver(decision_id, record)

    # ---------- views ----------

    @gl.public.view
    def get_question(self, question_id: str) -> typing.Any:
        raw = self.questions.get(question_id)
        if not raw:
            raise ValueError("PPA Producer: question not found")
        return json.loads(raw)

    @gl.public.view
    def get_receipt(self, decision_id: str) -> typing.Any:
        raw = self.receipts.get(decision_id)
        if not raw:
            raise ValueError("PPA Producer: decision not found")
        return json.loads(raw)

    @gl.public.view
    def get_meta(self) -> typing.Any:
        return {
            "owner": self.meta.get("owner"),
            "adapter": self.meta.get("adapter"),
            "authority_fingerprint": self.meta.get("authority_fingerprint"),
            "policy_version": self.meta.get("policy_version"),
            "created": self.meta.get("created"),
            "capital_methods": "NONE",
        }
