#!/usr/bin/env python3
"""Independent reimplementation of Nomos primitive `policy-envelope` v0.1.0.

Built ONLY from SPEC.md, INVARIANTS.md, THREAT_MODEL.md,
DECISION_BOUNDARY.md, CAPABILITY.json and vectors/v0.1.json.
No existing implementation was consulted.

Convergence mode: EXACT. Equivalence binds {decision, reason_code}.

Deterministic gate surface:
  create_envelope / expire_envelope / attach_mandate_clause /
  evaluate_request (+ views get_envelope, get_request, used_amount,
  get_clause_interpretation).

Evaluation order (fail-closed):
  1. unknown envelope            -> reject (op-level error)
  2. ENVELOPE_INACTIVE           (status != ACTIVE)
  3. OUTSIDE_VALIDITY_WINDOW     (ts < valid_after or ts > valid_until)
  4. ASSET_MISMATCH              (asset != envelope asset)
  5. AMOUNT_EXCEEDS_LIMIT        (amount > max_amount)
  6. CAPACITY_EXHAUSTED          (used + amount > max_amount)

Denials are recorded as audit entries that mutate no accounting state,
consume no capacity, and do NOT consume the request id (a later ADMIT
may reuse it). Only ADMIT consumes the request id (replay guard) and
capacity. actor/target are bound to the decision record but not
enforced against registries (per CAPABILITY unsupported list).

Judgment component interpretation (see BUILD_REPORT.md): the declared
mandate clause surface (attach_mandate_clause / interpret_clause) is
implemented as a strictly subordinate, non-authoritative structured
surface returning ADMIT/DENY/UNDETERMINED. It can never relax a hard
limit, mutate accounting state, or veto an otherwise-admissible
deterministic request. The canonical v0.1 decision is purely the
deterministic gate above.
"""

import json
import sys


class Reject(Exception):
    """Op-level rejection: the operation itself is refused."""


class PolicyEnvelope:
    def __init__(self):
        self._envelopes = {}       # eid -> envelope dict (incl. usage)
        self._requests = {}        # (eid, request_id) -> decision record
        self._clauses = {}         # (eid, clause_id) -> clause dict
        self._interpretations = {} # interpretation_id -> interp record
        self._audit = []           # append-only audit log of decisions

    # ---------- writes ----------

    def create_envelope(self, envelope_id, policy_hash, max_amount,
                        asset, valid_after, valid_until):
        if not envelope_id or not policy_hash:
            raise Reject("empty_id_or_hash")
        try:
            amt = int(max_amount)
            va = int(valid_after)
            vu = int(valid_until)
        except (TypeError, ValueError):
            raise Reject("invalid_numeric")
        if amt <= 0:
            raise Reject("non_positive_amount")
        if va >= vu:
            raise Reject("inverted_window")
        if envelope_id in self._envelopes:
            raise Reject("duplicate_envelope_id")
        env = {
            "envelope_id": envelope_id,
            "policy_hash": policy_hash,
            "max_amount": str(amt),
            "asset": asset,
            "valid_after": str(va),
            "valid_until": str(vu),
            "status": "ACTIVE",
            "_used": 0,
        }
        self._envelopes[envelope_id] = env
        return self._public(env)

    def expire_envelope(self, envelope_id):
        env = self._get_env(envelope_id)
        env["status"] = "EXPIRED"
        return self._public(env)

    def attach_mandate_clause(self, envelope_id, clause_id, clause_text):
        env = self._get_env(envelope_id)
        if not clause_id:
            raise Reject("empty_clause_id")
        cb = clause_text.encode("utf-8") if isinstance(clause_text, str) else b""
        if len(cb) > 4096:
            raise Reject("clause_too_large")
        key = (envelope_id, clause_id)
        if key in self._clauses:
            raise Reject("duplicate_clause_id")
        rec = {
            "envelope_id": envelope_id,
            "clause_id": clause_id,
            "clause_text": clause_text,
            "status": "DECLARED",
        }
        self._clauses[key] = rec
        return {"envelope_id": envelope_id, "clause_id": clause_id,
                "status": "DECLARED"}

    def interpret_clause(self, envelope_id, clause_id, facts_json,
                         interpretation_id):
        # Bounded, subordinate judgment surface. In this deterministic
        # reference build the interpretation is UNDETERMINED unless a
        # caller supplies explicit facts {"decision": "..."}; either way
        # it never mutates accounting state nor creates authority.
        self._get_env(envelope_id)
        key = (envelope_id, clause_id)
        if key not in self._clauses:
            raise Reject("unknown_clause")
        fb = facts_json.encode("utf-8") if isinstance(facts_json, str) else b""
        if len(fb) > 4096:
            raise Reject("facts_too_large")
        if not interpretation_id:
            raise Reject("empty_interpretation_id")
        if interpretation_id in self._interpretations:
            raise Reject("duplicate_interpretation_id")
        try:
            facts = json.loads(facts_json) if facts_json else {}
        except ValueError:
            facts = {}
        proposed = facts.get("decision") if isinstance(facts, dict) else None
        if proposed in ("ADMIT", "DENY"):
            idecision = proposed
        else:
            idecision = "UNDETERMINED"
        rec = {
            "interpretation_id": interpretation_id,
            "envelope_id": envelope_id,
            "clause_id": clause_id,
            "interpretation_decision": idecision,
            # analysis is explicitly non-canonical prose
            "analysis": "bounded interpretation; subordinate to hard limits",
        }
        self._interpretations[interpretation_id] = rec
        return {"interpretation_id": interpretation_id,
                "envelope_id": envelope_id,
                "clause_id": clause_id,
                "interpretation_decision": idecision}

    def evaluate_request(self, envelope_id, request_id, amount, asset,
                         actor, target, at_timestamp):
        env = self._get_env(envelope_id)
        try:
            amt = int(amount)
            ts = int(at_timestamp)
        except (TypeError, ValueError):
            raise Reject("invalid_numeric")

        # Denied requests do NOT consume the request id; only admitted
        # request ids become replay-guarded.
        rid_key = (envelope_id, request_id)
        if rid_key in self._requests and \
                self._requests[rid_key]["decision"] == "ADMIT":
            raise Reject("duplicate_admitted_request_id")

        decision, reason = self._gate(env, amt, asset, ts)
        record = {
            "envelope_id": envelope_id,
            "request_id": request_id,
            "amount": str(amt),
            "asset": asset,
            "actor": actor,
            "target": target,
            "at_timestamp": str(ts),
            "decision": decision,
            "reason_code": reason,
        }
        self._audit.append(record)
        if decision == "ADMIT":
            self._requests[rid_key] = dict(record)
            env["_used"] += amt
        return {"decision": decision, "reason_code": reason}

    def _gate(self, env, amt, asset, ts):
        if env["status"] != "ACTIVE":
            return "DENY", "ENVELOPE_INACTIVE"
        if ts < int(env["valid_after"]) or ts > int(env["valid_until"]):
            return "DENY", "OUTSIDE_VALIDITY_WINDOW"
        if asset != env["asset"]:
            return "DENY", "ASSET_MISMATCH"
        max_amt = int(env["max_amount"])
        if amt > max_amt:
            return "DENY", "AMOUNT_EXCEEDS_LIMIT"
        if env["_used"] + amt > max_amt:
            return "DENY", "CAPACITY_EXHAUSTED"
        return "ADMIT", "WITHIN_HARD_LIMITS"

    # ---------- views ----------

    def _get_env(self, envelope_id):
        env = self._envelopes.get(envelope_id)
        if env is None:
            raise Reject("unknown_envelope")
        return env

    @staticmethod
    def _public(env):
        return {k: v for k, v in env.items() if not k.startswith("_")}

    def get_envelope(self, envelope_id):
        env = self._envelopes.get(envelope_id)
        return self._public(env) if env else ""

    def get_request(self, envelope_id, request_id):
        return self._requests.get((envelope_id, request_id), "")

    def used_amount(self, envelope_id):
        env = self._envelopes.get(envelope_id)
        return str(env["_used"]) if env else ""

    def get_clause_interpretation(self, interpretation_id):
        return self._interpretations.get(interpretation_id, "")


# ---------------- vector runner ----------------

def run_vector(pe, vec):
    for action in vec["actions"]:
        op, args = action["op"], action["args"]
        expect = action["expect"]
        try:
            result = getattr(pe, op)(*args)
            rejected = False
        except Reject:
            result, rejected = None, True
        if expect == "ok":
            if rejected:
                return f"{vec['id']}: FAIL ({op}{args} rejected, expected ok)"
        elif expect == "reject":
            if not rejected:
                return f"{vec['id']}: FAIL ({op}{args} accepted, expected reject)"
        elif isinstance(expect, dict):
            if not isinstance(result, dict):
                return f"{vec['id']}: FAIL ({op} returned non-object)"
            for k, v in expect.items():
                if result.get(k) != v:
                    return (f"{vec['id']}: FAIL ({op} field {k}={result.get(k)!r}"
                            f" expected {v!r})")
        else:  # scalar expectation, e.g. "" for empty views
            if result != expect:
                return f"{vec['id']}: FAIL ({op} returned {result!r}, expected {expect!r})"
    return f"{vec['id']}: PASS"


def main():
    if len(sys.argv) != 2:
        print("usage: python3 your_build.py <vectors.json>", file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1]) as f:
        doc = json.load(f)
    all_pass = True
    for vec in doc["vectors"]:
        line = run_vector(PolicyEnvelope(), vec)
        if ": PASS" not in line:
            all_pass = False
        print(line)
    print("ALL PASS" if all_pass else "FAILURES PRESENT")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
