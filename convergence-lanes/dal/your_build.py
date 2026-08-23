#!/usr/bin/env python3
"""Independent reimplementation of Nomos primitive `dal` v0.1.0
(Dynamic Authorization Lanes / Delegation Authorization Lanes).

Built ONLY from SPEC.md, INVARIANTS.md, THREAT_MODEL.md,
DECISION_BOUNDARY.md, CAPABILITY.json and vectors/v0.1.json.
No existing implementation was consulted.

Convergence mode: EXACT. Equivalence binds {decision, reason_code}.

State machine (per CAPABILITY.stateMachine):
  - one lane per (issuer, domain_id); revoked lanes cannot be reopened;
  - expected nonce starts at 1, advances exactly once per AUTHORIZE;
  - nonce < expected -> NONCE_REUSED; nonce == 0 or > expected ->
    NONCE_INVALID; denials mutate nothing;
  - exercise after expiry_window denies fail-closed.

Fail-closed validation order in exercise():
  1. unknown lane            -> reject (op-level error)
  2. LANE_REVOKED            (explicit revocation dominates)
  3. LANE_EXPIRED            (at_timestamp > expiry_window)
  4. nonce checks: zero/ahead -> NONCE_INVALID; below expected ->
     NONCE_REUSED
  Only then is the nonce consumed atomically (expected += 1).
"""

import json
import sys


class Reject(Exception):
    """Op-level rejection: the operation itself is refused."""


class Dal:
    def __init__(self):
        self._lanes = {}  # (issuer, domain_id) -> lane dict

    def open_lane(self, issuer, domain_id, expiry_window):
        if not issuer or not domain_id:
            raise Reject("empty_key")
        try:
            ew = int(expiry_window)
        except (TypeError, ValueError):
            raise Reject("invalid_numeric")
        key = (issuer, domain_id)
        if key in self._lanes:
            # includes revoked lanes: they can never be reopened
            raise Reject("duplicate_lane")
        lane = {
            "issuer": issuer,
            "domain_id": domain_id,
            "expiry_window": str(ew),
            "nonce": "1",       # expected next nonce
            "status": "ACTIVE",
        }
        self._lanes[key] = lane
        return {k: v for k, v in lane.items()}

    def exercise(self, issuer, domain_id, nonce, at_timestamp):
        key = (issuer, domain_id)
        lane = self._lanes.get(key)
        if lane is None:
            raise Reject("unknown_lane")
        try:
            n = int(nonce)
            ts = int(at_timestamp)
        except (TypeError, ValueError):
            raise Reject("invalid_numeric")

        decision, reason = self._gate(lane, n, ts)
        if decision == "AUTHORIZE":
            # atomic single-advance of the monotonic nonce
            lane["nonce"] = str(int(lane["nonce"]) + 1)
        return {"decision": decision, "reason_code": reason}

    def _gate(self, lane, n, ts):
        if lane["status"] == "REVOKED":
            return "DENY", "LANE_REVOKED"
        if ts > int(lane["expiry_window"]):
            return "DENY", "LANE_EXPIRED"
        expected = int(lane["nonce"])
        if n == 0 or n > expected:
            return "DENY", "NONCE_INVALID"
        if n < expected:
            return "DENY", "NONCE_REUSED"
        return "AUTHORIZE", "NONCE_VALID"

    def revoke_lane(self, issuer, domain_id):
        lane = self._lanes.get((issuer, domain_id))
        if lane is None:
            raise Reject("unknown_lane")
        lane["status"] = "REVOKED"
        return {k: v for k, v in lane.items()}

    def get_lane(self, issuer, domain_id):
        lane = self._lanes.get((issuer, domain_id))
        return {k: v for k, v in lane.items()} if lane else ""


# ---------------- vector runner ----------------

def run_vector(dal, vec):
    for action in vec["actions"]:
        op, args = action["op"], action["args"]
        expect = action["expect"]
        try:
            result = getattr(dal, op)(*args)
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
        else:
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
        line = run_vector(Dal(), vec)
        if ": PASS" not in line:
            all_pass = False
        print(line)
    print("ALL PASS" if all_pass else "FAILURES PRESENT")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
