"""Adjudicated Receipt - independent convergence-lane reimplementation.

Nomos primitive: adjudicated-receipt | capability 0.2.0 | convergence mode: SEMANTIC
Lane scope: the DETERMINISTIC ENVELOPE only (registration identity/validation,
obligation-hash binding, cancellation terminal rule, unknown-receipt fail-closed
guards). Per SPEC.md section 13 and the v0.2 vector note, quorum verdict paths
(adjudicate/challenge/finalize/settle producing ACCEPTED/REJECTED/UNDETERMINED)
are judgment surface and are tested elsewhere (mocked-web direct tests + GLSim
integration). This lane enforces their deterministic preconditions and then
fails closed with a clearly-labelled JudgmentSurfaceNotInLaneScope error.

Derived semantics (authority files + vectors only; no reference implementation
was read):
- object lifecycle: OPEN -> CANCELLED (explicit owner cancellation, terminal)
  and OPEN -> SETTLED (only via an admitted settlement; receipts are never
  produced inside this lane, so the SETTLED branch of the gate is unreachable
  until the judgment surface records quorum receipts elsewhere).
- registered terms are immutable and bound into an obligation hash at
  registration; the hash derivation formula is lane-internal (vectors assert
  binding semantics, not the digest value).
- canonical JSON everywhere: sort_keys=True, separators=(",", ":").
- fresh contract instance per vector.

Embedded vector runner (dispatch semantics mirror tools/nomos_run_vectors.py:
"ok" = call must not raise, "reject" = call must raise, dict = subset key match
with string coercion):
    python3 your_build.py <vectors.json>
"""

from __future__ import annotations

import hashlib
import json
import sys

PRIMITIVE_ID = "adjudicated-receipt"
CAPABILITY_VERSION = "0.2.0"
CONVERGENCE_MODE = "SEMANTIC"

OBJECT_STATUSES = ("OPEN", "CANCELLED", "SETTLED")
RECEIPT_STATUSES = (
    "PROVISIONAL_ACCEPTED",
    "FINAL_ACCEPTED",
    "REJECTED",
    "UNDETERMINED",
    "UNDETERMINED_DELIVERY_UNCERTAIN",
    "CHALLENGED",
    "EXPIRED",
)
# CAPABILITY limits.acceptanceBar: satisfied=true AND verdict=delivered AND
# confidence=high. Encoded here as the bound the deterministic settlement gate
# admits; the gate itself never runs inside this lane (no receipts are created
# here), but the predicate is part of the documented envelope.
ACCEPTANCE_BAR = {"satisfied": True, "verdict": "delivered", "confidence": "high"}

MAX_ID_LEN = 64  # CAPABILITY limits.idLength: 1..64 chars
HTTPS_PREFIX = "https://"  # CAPABILITY limits.evidencePointerScheme: https only


class AdjudicatedReceiptError(Exception):
    """Deterministic fail-closed rejection of an operation."""


class JudgmentSurfaceNotInLaneScope(AdjudicatedReceiptError):
    """Deterministic preconditions passed, but the operation's outcome depends
    on a validator-quorum verdict (or its TTL/challenge-clock post-processing),
    which is judgment surface covered by direct/GLSim tests, not this lane."""


def canonical(obj) -> str:
    """Canonical serialization: sorted keys, compact separators."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _require(cond, code: str) -> None:
    if not cond:
        raise AdjudicatedReceiptError(code)


def _valid_id(value, name: str) -> str:
    _require(isinstance(value, str) and 1 <= len(value) <= MAX_ID_LEN,
             f"INVALID_{name}")
    return value


def _non_empty(value, name: str) -> str:
    _require(isinstance(value, str) and value != "", f"EMPTY_{name}")
    return value


def _positive_uint_string(value, name: str) -> str:
    _require(isinstance(value, str) and value.isascii() and value.isdigit(),
             f"INVALID_{name}")
    _require(int(value) > 0, f"NONPOSITIVE_{name}")
    return str(int(value))


def _https_url(value) -> str:
    _non_empty(value, "EVIDENCE_POINTER")
    _require(value.startswith(HTTPS_PREFIX)
             and len(value) > len(HTTPS_PREFIX),
             "EVIDENCE_POINTER_MUST_BE_HTTPS")
    return value


def _derive_obligation_hash(terms: list) -> str:
    """Lane-internal obligation hash.

    SPEC.md section 14: "canonical digest = ordered concatenation of registered
    terms (upgrade path: content hash of canonical JSON)". This lane takes the
    upgrade path: sha256 over canonical JSON of the registered terms in their
    registration order. The vectors do not pin the formula - they pin that an
    obligation hash IS derived at registration and that settlement binds to it.
    """
    return hashlib.sha256(canonical(terms).encode("utf-8")).hexdigest()


class AdjudicatedReceipt:
    """Deterministic envelope state machine.

    State owned (per CAPABILITY stateOwnership.owns):
      - registered release objects keyed by invoice_id,
      - immutable adjudication receipts keyed by receipt_id (one-way consumed
        bit; never created inside this lane),
      - challenge records keyed by receipt_id (never created inside this lane),
      - release records keyed by pay-<receipt_id>.
    Not owned: spending policy, delegation, capital reservation, encumbrance,
    token movement, rectification. Releases are recorded obligations only.
    """

    def __init__(self):
        self._owner: str | None = None
        # GenLayer msg.sender is not expressible in the lane arg surface; the
        # caller attribute models transaction context and defaults to the owner
        # (vectors always act as the initializing owner). Non-owner settlement
        # attempts are direct-test/GLSim scope.
        self._caller: str | None = None
        self._objects: dict[str, dict] = {}
        self._receipts: dict[str, dict] = {}
        self._releases: dict[str, dict] = {}
        self._challenges: dict[str, dict] = {}
        self._registration_seq = 0

    # ------------------------------------------------------------------ #
    # writes                                                             #
    # ------------------------------------------------------------------ #

    def initialize(self, owner) -> str:
        _require(self._owner is None, "ALREADY_INITIALIZED")
        _non_empty(owner, "OWNER")
        self._owner = owner
        self._caller = owner
        return "initialized"

    def register_release(self, invoice_id, object_ref, surrender_value,
                         surrender_asset, evidence_pointer, adjudication_clause,
                         valid_for_seconds, challenge_window, policy_version,
                         expected_source_id) -> str:
        """Register a release object; binds immutable registered terms into an
        obligation hash. Returns 'release_registered'."""
        self._require_initialized()
        _valid_id(invoice_id, "INVOICE_ID")
        _require(invoice_id not in self._objects, "DUPLICATE_OBJECT_ID")
        object_ref = _non_empty(object_ref, "OBJECT_REF")
        surrender_value = _positive_uint_string(surrender_value,
                                                "SURRENDER_VALUE")
        surrender_asset = _non_empty(surrender_asset, "SURRENDER_ASSET")
        evidence_pointer = _https_url(evidence_pointer)
        adjudication_clause = _non_empty(adjudication_clause,
                                         "ADJUDICATION_CLAUSE")
        valid_for_seconds = _positive_uint_string(valid_for_seconds,
                                                  "VALID_FOR_SECONDS")
        challenge_window = _positive_uint_string(challenge_window,
                                                 "CHALLENGE_WINDOW")
        policy_version = _non_empty(policy_version, "POLICY_VERSION")
        expected_source_id = _non_empty(expected_source_id,
                                        "EXPECTED_SOURCE_ID")

        self._registration_seq += 1
        obligation_hash = _derive_obligation_hash([
            invoice_id, object_ref, surrender_value, surrender_asset,
            evidence_pointer, adjudication_clause, valid_for_seconds,
            challenge_window, policy_version, expected_source_id,
        ])
        record = {
            "invoice_id": invoice_id,
            "object_ref": object_ref,
            "surrender_value": surrender_value,
            "surrender_asset": surrender_asset,
            "evidence_pointer": evidence_pointer,
            "adjudication_clause": adjudication_clause,
            # Lane has no clock; registered_at is a logical registration
            # sequence number. TTL freshness enforcement (registered_at +
            # valid_for_seconds vs tx time) is deterministic but time-bound
            # and covered by direct/GLSim tests, not this lane.
            "registered_at": str(self._registration_seq),
            "valid_for_seconds": valid_for_seconds,
            "challenge_window": challenge_window,
            "policy_version": policy_version,
            "expected_source_id": expected_source_id,
            "obligation_hash": obligation_hash,
            "status": "OPEN",
        }
        self._objects[invoice_id] = record
        return "release_registered"

    def cancel_release(self, invoice_id) -> str:
        """Explicit terminal cancellation. Only an OPEN object can be
        cancelled; CANCELLED (and SETTLED) are terminal - re-cancellation
        rejects. Returns the canonical cancellation object."""
        self._require_initialized()
        obj = self._object(invoice_id)
        _require(obj["status"] == "OPEN", "OBJECT_NOT_OPEN")
        obj["status"] = "CANCELLED"
        return canonical({
            "invoice_id": invoice_id,
            "reason_code": "OWNER_CANCELLED",
            "status": "CANCELLED",
        })


    def adjudicate_object(self, invoice_id, receipt_id) -> str:
        """Deterministic preconditions only: object must exist and be OPEN,
        receipt id must be fresh (1..64 chars, globally unique). The quorum
        verdict itself is judgment surface -> fail closed with a labelled
        error; this lane never records receipts."""
        self._require_initialized()
        obj = self._object(invoice_id)
        _require(obj["status"] == "OPEN", "OBJECT_NOT_OPEN")
        _valid_id(receipt_id, "RECEIPT_ID")
        _require(receipt_id not in self._receipts, "DUPLICATE_RECEIPT_ID")
        raise JudgmentSurfaceNotInLaneScope(
            "adjudicate_object: deterministic preconditions OK; quorum verdict "
            "production is judgment surface, not in deterministic-envelope "
            "lane scope")

    def challenge_release(self, receipt_id, bond, counterevidence_hash,
                          reason) -> str:
        self._require_initialized()
        _require(receipt_id in self._receipts, "UNKNOWN_RECEIPT_ID")
        _positive_uint_string(bond, "BOND")
        _non_empty(counterevidence_hash, "COUNTEREVIDENCE_HASH")
        _non_empty(reason, "REASON")
        raise JudgmentSurfaceNotInLaneScope(
            "challenge_release: deterministic preconditions OK; challenge "
            "lifecycle/resolution is judgment surface, not in "
            "deterministic-envelope lane scope")

    def finalize_release(self, receipt_id) -> str:
        self._require_initialized()
        _require(receipt_id in self._receipts, "UNKNOWN_RECEIPT_ID")
        receipt = self._receipts[receipt_id]
        _require(receipt["status"] == "PROVISIONAL_ACCEPTED",
                 "RECEIPT_NOT_PROVISIONAL_ACCEPTED")
        _require(receipt_id not in self._challenges, "RECEIPT_CHALLENGED")
        raise JudgmentSurfaceNotInLaneScope(
            "finalize_release: deterministic preconditions OK; finalization "
            "(challenge-deadline/TTL clock post-processing) is judgment/"
            "time-bound surface, not in deterministic-envelope lane scope")

    def settle_release(self, receipt_id) -> str:
        """Deterministic settlement gate. Unknown receipts fail closed. For
        known receipts the full deterministic gate is evaluated (FINAL_ACCEPTED
        only, unconsumed, obligation-hash binding to the current object terms,
        object still OPEN, owner-held authority); the unknown-id branch is the
        only one reachable inside this lane because receipts are never created
        here."""
        self._require_initialized()
        _require(receipt_id in self._receipts, "UNKNOWN_RECEIPT_ID")
        receipt = self._receipts[receipt_id]
        _require(receipt["status"] == "FINAL_ACCEPTED",
                 "RECEIPT_NOT_FINAL_ACCEPTED")
        _require(receipt["consumed"] is False, "RECEIPT_ALREADY_CONSUMED")
        obj = self._objects.get(receipt["invoice_id"])
        _require(obj is not None, "UNKNOWN_OBJECT_ID")
        _require(obj["obligation_hash"] == receipt["obligation_hash"],
                 "BINDING_MISMATCH")
        _require(obj["status"] == "OPEN", "OBJECT_NOT_OPEN")
        _require(self._caller == self._owner, "NOT_OWNER")

        receipt["consumed"] = True  # one-way consumption bit
        obj["status"] = "SETTLED"
        payment_id = f"pay-{receipt_id}"
        release = {
            "amount": obj["surrender_value"],
            "asset": obj["surrender_asset"],
            "invoice_id": receipt["invoice_id"],
            "payment_id": payment_id,
            "receipt_id": receipt_id,
            "status": "SETTLED",
            "to": self._owner,
        }
        self._releases[payment_id] = release
        return canonical(release)


    # ------------------------------------------------------------------ #
    # views                                                              #
    # ------------------------------------------------------------------ #

    def get_object(self, invoice_id) -> str:
        self._require_initialized()
        return canonical(dict(self._object(invoice_id)))

    def get_receipt(self, receipt_id) -> str:
        self._require_initialized()
        _require(receipt_id in self._receipts, "UNKNOWN_RECEIPT_ID")
        return canonical(dict(self._receipts[receipt_id]))

    def get_release(self, payment_id) -> str:
        self._require_initialized()
        _require(payment_id in self._releases, "UNKNOWN_PAYMENT_ID")
        return canonical(dict(self._releases[payment_id]))

    def get_challenge(self, receipt_id) -> str:
        self._require_initialized()
        _require(receipt_id in self._challenges, "UNKNOWN_CHALLENGE")
        return canonical(dict(self._challenges[receipt_id]))

    # ------------------------------------------------------------------ #
    # internal helpers                                                   #
    # ------------------------------------------------------------------ #

    def _require_initialized(self) -> None:
        _require(self._owner is not None, "NOT_INITIALIZED")

    def _object(self, invoice_id) -> dict:
        obj = self._objects.get(invoice_id)
        _require(obj is not None, "UNKNOWN_OBJECT_ID")
        return obj



# ---------------------------------------------------------------------- #
# Vector runner (dispatch semantics mirror tools/nomos_run_vectors.py)   #
# ---------------------------------------------------------------------- #


def _coerce(value) -> str:
    return value if isinstance(value, str) else json.dumps(value)


def run_vector(contract: AdjudicatedReceipt, vec: dict) -> tuple[bool, str]:
    for action in vec.get("actions", []):
        op = action["op"]
        args = action.get("args", [])
        expect = action.get("expect")
        step = f"{vec.get('id')} {op}({', '.join(str(a) for a in args)})"
        method = getattr(contract, op, None)
        if method is None:
            return False, f"{step}: unknown op"
        try:
            result = method(*args)
        except Exception as exc:  # fail-closed rejections and lane-scope errors
            if expect == "reject":
                continue
            return False, f"{step}: expected ok, raised {type(exc).__name__}: {exc}"
        if expect == "reject":
            return False, f"{step}: expected reject, but call succeeded"
        if expect == "ok":
            continue
        if isinstance(expect, dict):
            try:
                parsed = json.loads(result) if isinstance(result, str) else dict(result)
            except Exception:
                return False, f"{step}: expected object, got unparseable {result!r}"
            mismatches = {
                key: (parsed.get(key), val)
                for key, val in expect.items()
                if _coerce(parsed.get(key)) != _coerce(val)
            }
            if mismatches:
                return False, f"{step}: mismatch {mismatches}"
            continue
        if _coerce(result) != _coerce(expect):
            return False, f"{step}: expected {_coerce(expect)!r}, got {_coerce(result)!r}"
    return True, f"{vec.get('id')}: PASS"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python3 your_build.py <vectors.json>", file=sys.stderr)
        return 2
    with open(argv[1]) as fh:
        doc = json.load(fh)
    failures = 0
    vectors = doc.get("vectors", [])
    for vec in vectors:
        ok, msg = run_vector(AdjudicatedReceipt(), vec)  # fresh instance per vector
        print(("PASS" if ok else "FAIL"), "-", msg)
        failures += 0 if ok else 1
    total = len(vectors)
    print(f"\n{total - failures}/{total} vectors PASS")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
