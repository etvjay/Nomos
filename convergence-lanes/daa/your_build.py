"""Dynamic Authority Allocation (DAA) — independent reimplementation.

Nomos primitive: daa | capability 0.1.0 | convergence mode: EXACT
JUDGMENT_BOUNDARY = NONE (deterministic predicates only)

GenLayer-style contract. Authority is allocated as *capacity*: a request
lifecycle REQUESTED -> [EVALUATING] -> AWARDED | REJECTED | UNDETERMINED,
and an award lifecycle AWARDED -> REVOKED / EXPIRED(implicit by window).
Award creation is distinct from usage: downstream execution proves it is
within the award via verify_authority (fail-closed, mutating nothing).
Evaluation attempts consume monotonically increasing evaluation ids even
when the attempt is INELIGIBLE (auditable burn). Validity windows are
immutable after request time — activity never resets expiry.

Embedded vector runner:
    python3 your_build.py <vectors.json>
"""

from __future__ import annotations

import json
import sys

JUDGMENT_BOUNDARY = "NONE"

REQUEST_STATUSES = ("REQUESTED", "EVALUATING", "AWARDED", "REJECTED", "UNDETERMINED")
AWARD_STATUSES = ("AWARDED", "EXPIRED", "REVOKED")


class DaaError(Exception):
    """Deterministic rejection of a state transition."""


def _require_uint(value: str, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise DaaError(f"INVALID_{name}")
    text = str(value)
    if not text.isdigit():
        raise DaaError(f"INVALID_{name}")
    return int(text)


def _require_int(value: str, name: str) -> int:
    text = str(value)
    body = text[1:] if text.startswith("-") else text
    if not body.isdigit():
        raise DaaError(f"INVALID_{name}")
    return int(text)


def canonical(obj) -> str:
    """Canonical serialization: sorted keys, compact separators."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


class Daa:
    """DAA contract state machine. Owns ONLY allocation requests and awards."""

    def __init__(self):
        # requests: request_id -> canonical request record
        self._requests: dict[str, dict] = {}
        # awards: allocation_id -> canonical award record (immutable once final)
        self._awards: dict[str, dict] = {}
        # allocation_id per request (set only when AWARDED)
        self._request_award: dict[str, str] = {}
        # evaluation ledger: monotonic ids burned by every evaluation attempt,
        # including INELIGIBLE ones (auditable).
        self._evaluations: list[dict] = []
        self._evaluation_seq = 0
        self._request_eval_seq: dict[str, int] = {}

    # ------------------------------------------------------------------ #
    # write methods                                                      #
    # ------------------------------------------------------------------ #

    def request_allocation(self, sender: str, request_id: str, resource: str,
                           asset: str, beneficiary: str, purpose: str,
                           requested_bound: str, policy_hash: str,
                           valid_after: str, valid_until: str) -> str:
        for label, value in (("REQUEST_ID", request_id), ("RESOURCE", resource),
                             ("ASSET", asset), ("BENEFICIARY", beneficiary),
                             ("PURPOSE", purpose), ("POLICY_HASH", policy_hash)):
            if not isinstance(value, str) or value == "":
                raise DaaError(f"EMPTY_{label}")
        bound = _require_uint(requested_bound, "BOUND")
        if bound <= 0:
            raise DaaError("ZERO_BOUND")
        va = _require_int(valid_after, "VALID_AFTER")
        vu = _require_int(valid_until, "VALID_UNTIL")
        if va > vu:
            raise DaaError("INVERTED_WINDOW")
        if request_id in self._requests:
            raise DaaError("DUPLICATE_REQUEST")
        record = {
            "request_id": request_id,
            "resource": resource,
            "asset": asset,
            "beneficiary": beneficiary,
            "purpose": purpose,
            "requested_bound": str(bound),
            "policy_hash": policy_hash,
            "valid_after": str(va),
            "valid_until": str(vu),
            "authority_source": sender,
            "status": "REQUESTED",
        }
        self._requests[request_id] = record
        return canonical(record)

    def begin_evaluation(self, sender: str, request_id: str,
                         evaluation_id: str) -> str:
        """Authority source opens deterministic evaluation of a request."""
        req = self._require_request(request_id)
        self._require_authority(req, sender)
        if req["status"] != "REQUESTED":
            raise DaaError("NOT_REQUESTED")
        req["status"] = "EVALUATING"
        return canonical(req)

    def record_evaluation(self, sender: str, request_id: str,
                          eligibility: str) -> str:
        """Burn an evaluation id. INELIGIBLE attempts still burn their id."""
        req = self._require_request(request_id)
        self._require_authority(req, sender)
        if req["status"] != "EVALUATING":
            raise DaaError("NOT_EVALUATING")
        if eligibility not in ("ELIGIBLE", "INELIGIBLE"):
            raise DaaError("INVALID_ELIGIBILITY")
        self._evaluation_seq += 1
        entry = {
            "evaluation_id": f"EVAL-{self._evaluation_seq}",
            "request_id": request_id,
            "eligibility": eligibility,
            "burned": True,
        }
        self._evaluations.append(entry)
        self._request_eval_seq[request_id] = self._evaluation_seq
        # Evaluation outcome does not itself finalize the request; the
        # authority source still decides award/reject/undetermine.
        return canonical(entry)

    def award(self, sender: str, request_id: str, allocation_id: str,
              max_authority: str, awarded_at: str) -> str:
        req = self._require_request(request_id)
        self._require_authority(req, sender)
        if req["status"] not in ("REQUESTED", "EVALUATING"):
            raise DaaError("NOT_AWARDABLE")
        if not isinstance(allocation_id, str) or allocation_id == "":
            raise DaaError("EMPTY_ALLOCATION_ID")
        if allocation_id in self._awards:
            raise DaaError("DUPLICATE_ALLOCATION_ID")
        if request_id in self._request_award:
            raise DaaError("ALREADY_AWARDED")  # one award per request
        bound = _require_uint(max_authority, "MAX_AUTHORITY")
        if bound <= 0:
            raise DaaError("ZERO_BOUND")
        requested = int(req["requested_bound"])
        if bound > requested:
            # Bound escalation structurally impossible.
            raise DaaError("EXCEEDS_REQUESTED_BOUND")
        awarded_at_i = _require_int(awarded_at, "AWARDED_AT")
        va, vu = int(req["valid_after"]), int(req["valid_until"])
        if awarded_at_i < va or awarded_at_i > vu:
            raise DaaError("AWARD_OUTSIDE_WINDOW")
        award = {
            "allocation_id": allocation_id,
            "request_id": request_id,
            "authority_source": req["authority_source"],
            "beneficiary": req["beneficiary"],
            "resource": req["resource"],
            "asset": req["asset"],
            "max_authority": str(bound),
            "requested_bound": req["requested_bound"],
            "purpose": req["purpose"],
            "policy_hash": req["policy_hash"],
            "valid_after": req["valid_after"],
            "valid_until": req["valid_until"],  # immutable; never resets
            "awarded_at": str(awarded_at_i),
            "status": "AWARDED",
        }
        self._awards[allocation_id] = award
        self._request_award[request_id] = allocation_id
        req["status"] = "AWARDED"
        return canonical(award)

    def reject_request(self, sender: str, request_id: str) -> str:
        req = self._require_request(request_id)
        self._require_authority(req, sender)
        if req["status"] not in ("REQUESTED", "EVALUATING"):
            raise DaaError("NOT_REJECTABLE")
        req["status"] = "REJECTED"  # creates no authority
        return canonical({k: v for k, v in req.items()})

    def undetermine_request(self, sender: str, request_id: str) -> str:
        req = self._require_request(request_id)
        self._require_authority(req, sender)
        if req["status"] not in ("REQUESTED", "EVALUATING"):
            raise DaaError("NOT_UNDETERMINABLE")
        req["status"] = "UNDETERMINED"  # creates no authority
        return canonical(dict(req))

    def revoke_award(self, sender: str, allocation_id: str) -> str:
        award = self._awards.get(allocation_id)
        if award is None:
            raise DaaError("UNKNOWN_ALLOCATION")
        self._require_authority(award, sender)
        if award["status"] != "AWARDED":
            raise DaaError("NOT_REVOCABLE")
        award["status"] = "REVOKED"
        return canonical(dict(award))

    # ------------------------------------------------------------------ #
    # view methods (fail-closed, mutating nothing)                       #
    # ------------------------------------------------------------------ #

    def effective_status(self, award: dict, at_timestamp: str) -> str:
        """EXPIRED is implicit by window; windows are immutable so activity
        can never reset expiry."""
        ts = _require_int(at_timestamp, "TIMESTAMP")
        if int(award["valid_until"]) <= ts or ts < int(award["valid_after"]):
            return "EXPIRED"
        return award["status"]

    def verify_authority(self, allocation_id: str, actor: str, resource: str,
                         purpose: str, action_amount: str,
                         at_timestamp: str) -> str:
        award = self._awards.get(allocation_id)
        if award is None:
            return canonical({"decision": "DENY", "reason_code": "AWARD_NOT_FOUND"})
        status = self.effective_status(award, at_timestamp)
        if status == "REVOKED":
            return canonical({"decision": "DENY", "reason_code": "AWARD_REVOKED"})
        if status == "EXPIRED":
            return canonical({"decision": "DENY", "reason_code": "AWARD_EXPIRED"})
        if actor != award["beneficiary"]:
            return canonical({"decision": "DENY", "reason_code": "BENEFICIARY_MISMATCH"})
        if resource != award["resource"]:
            return canonical({"decision": "DENY", "reason_code": "RESOURCE_MISMATCH"})
        if purpose != award["purpose"]:
            return canonical({"decision": "DENY", "reason_code": "PURPOSE_MISMATCH"})
        amount = _require_uint(action_amount, "AMOUNT")
        if amount > int(award["max_authority"]):
            return canonical({"decision": "DENY", "reason_code": "EXCEEDS_AWARD_BOUND"})
        return canonical({"decision": "AUTHORIZE", "reason_code": "WITHIN_AWARD"})

    def get_request(self, request_id: str) -> str:
        req = self._requests.get(request_id)
        return "" if req is None else canonical(dict(req))

    def get_award(self, allocation_id: str) -> str:
        award = self._awards.get(allocation_id)
        return "" if award is None else canonical(dict(award))

    def list_evaluations(self) -> str:
        return canonical(self._evaluations)

    # ------------------------------------------------------------------ #
    # internal helpers                                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _require_authority(record: dict, sender: str) -> None:
        # Only the recorded authority source may award/reject/undetermine/revoke.
        if sender != record["authority_source"]:
            raise DaaError("NOT_AUTHORITY_SOURCE")

    def _require_request(self, request_id: str) -> dict:
        req = self._requests.get(request_id)
        if req is None:
            raise DaaError("UNKNOWN_REQUEST")
        return req


# ---------------------------------------------------------------------- #
# Vector runner                                                          #
# ---------------------------------------------------------------------- #

_DEFAULT_SENDER = "AUTHORITY-SOURCE-1"


def run_vector(contract: Daa, vec: dict) -> tuple[bool, str]:
    for action in vec.get("actions", []):
        op = action["op"]
        args = action.get("args", [])
        expect = action.get("expect")
        sender = action.get("sender", _DEFAULT_SENDER)
        method = getattr(contract, op, None)
        if method is None:
            return False, f"{vec['id']}: unknown op {op}"
        is_view = op in ("verify_authority", "get_request", "get_award")
        call_args = args if is_view else [sender, *args]
        try:
            result = method(*call_args)
        except DaaError as exc:
            if expect == "reject":
                continue
            return False, f"{vec['id']}/{op}: unexpected DaaError {exc}"
        except TypeError as exc:
            return False, f"{vec['id']}/{op}: arg mismatch ({exc})"
        if expect == "reject":
            return False, f"{vec['id']}/{op}: expected reject, got ok"
        if expect == "ok":
            continue
        if isinstance(expect, dict):
            try:
                actual = json.loads(result)
            except (TypeError, json.JSONDecodeError):
                return False, f"{vec['id']}/{op}: non-json output"
            missing = {k: v for k, v in expect.items() if actual.get(k) != v}
            if missing:
                return False, f"{vec['id']}/{op}: mismatch {missing} vs {actual}"
            continue
        if expect == "":
            if result != "":
                return False, f"{vec['id']}/{op}: expected empty, got {result}"
            continue
        if result != expect:
            return False, f"{vec['id']}/{op}: {result!r} != {expect!r}"
    return True, f"{vec['id']}: PASS"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python3 your_build.py <vectors.json>", file=sys.stderr)
        return 2
    with open(argv[1]) as fh:
        doc = json.load(fh)
    failures = 0
    for vec in doc.get("vectors", []):
        ok, msg = run_vector(Daa(), vec)
        print(("PASS" if ok else "FAIL"), "-", msg)
        failures += 0 if ok else 1
    total = len(doc.get("vectors", []))
    print(f"\n{total - failures}/{total} vectors PASS")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
