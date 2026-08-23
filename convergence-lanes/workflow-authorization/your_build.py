"""
workflow-authorization — independent fresh-context build (convergence lane).

Primitive: Nomos "Workflow Authorization (Path + Pact)", capability v0.1.0,
EXACT convergence mode, JUDGMENT_BOUNDARY = NONE.

Reimplemented solely from SPEC.md / INVARIANTS.md / THREAT_MODEL.md /
DECISION_BOUNDARY.md / CAPABILITY.json / vectors/v0.1.json. No reference to
any existing implementation code.

GenLayer-style contract conventions:
- State lives on the contract object (`self.state`), analogous to GenLayer
  contract storage; every write method takes an explicit `sender` argument
  (injected by the VM in a real deployment) and all timestamps are passed
  explicitly by the caller, keeping flows sender-neutral except where the
  spec requires principal authority (Pact acceptance).
- Deterministic gates only; fail-closed DENY decisions are structured
  results, never exceptions. Exceptions are reserved for invalid/rejected
  operations (malformed input, duplicates, unauthorized actions).

Vector runner: `python3 your_build.py <vectors.json>` prints PASS/FAIL per vector.
"""

import json
import sys

JUDGMENT_BOUNDARY = "NONE"

MAX_TERMS_BYTES = 4096

# Path statuses
PATH_ACTIVE = "ACTIVE"
PATH_REVOKED = "REVOKED"
PATH_EXPIRED = "EXPIRED"

# Pact statuses
PACT_PROPOSED = "PROPOSED"
PACT_ACCEPTED = "ACCEPTED"
PACT_EXECUTED = "EXECUTED"
PACT_VOID = "VOID"


class Rejected(Exception):
    """Deterministic rejection of an invalid/disallowed operation."""


def _norm_addr(addr):
    """Case/prefix-insensitive address normalization."""
    a = str(addr)
    if a.lower().startswith("0x"):
        a = a[2:]
    return a.strip().lower()


def _parse_int(value, field):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        raise Rejected("invalid %s" % field)


def _path_status(path, now):
    """Effective status: revocation is explicit; expiry is implicit by window."""
    if path["status"] == PATH_REVOKED:
        return PATH_REVOKED
    if now < path["valid_after"] or now > path["valid_until"]:
        return PATH_EXPIRED
    return PATH_ACTIVE


class WorkflowAuthorization:
    """Canonical v0.1 slice: deterministic Path/Pact authorization machinery."""

    def __init__(self):
        # state ownership: paths + pacts only. No capital, no nonces,
        # no settlement, no policy interpretation.
        self.paths = {}
        self.pacts = {}

    # ---------------- writes ----------------

    def grant_path(self, sender, path_id, principal, agent, purpose_scope,
                   max_per_action, asset, valid_after, valid_until):
        pid = str(path_id)
        if not pid:
            raise Rejected("empty path_id")
        if pid in self.paths:
            raise Rejected("duplicate path_id")
        if not str(principal).strip() or not str(agent).strip():
            raise Rejected("empty party")
        if _norm_addr(principal) == _norm_addr(agent):
            raise Rejected("self-delegation rejected")
        if not str(purpose_scope).strip():
            raise Rejected("empty purpose_scope")
        max_per_action_i = _parse_int(max_per_action, "max_per_action")
        if max_per_action_i <= 0:
            raise Rejected("zero bound")
        if not str(asset).strip():
            raise Rejected("empty asset")
        va = _parse_int(valid_after, "valid_after")
        vu = _parse_int(valid_until, "valid_until")
        if va > vu:
            raise Rejected("inverted window")
        path = {
            "path_id": pid,
            "principal": str(principal),
            "agent": str(agent),
            "purpose_scope": str(purpose_scope),
            "max_per_action": str(max_per_action_i),
            "asset": str(asset),
            "valid_after": va,
            "valid_until": vu,
            "status": PATH_ACTIVE,
        }
        self.paths[pid] = path
        return self._canonical_path(path)

    def revoke_path(self, sender, path_id):
        path = self._get_path_or_raise(path_id)
        # Revocation is monotonic; already-revoked stays REVOKED (idempotent).
        if path["status"] != PATH_REVOKED:
            path["status"] = PATH_REVOKED
        return self._canonical_path(path)

    def propose_pact(self, sender, pact_id, path_id, workflow_ref, terms_json,
                     proposed_at):
        pxid = str(pact_id)
        if not pxid:
            raise Rejected("empty pact_id")
        if pxid in self.pacts:
            raise Rejected("duplicate pact_id")
        path = self._get_path_or_raise(path_id)
        if _path_status(path, _parse_int(proposed_at, "proposed_at")) != PATH_ACTIVE:
            # includes time-expired paths: stale authority cannot authorize
            raise Rejected("path not active at proposal time")
        if not str(workflow_ref).strip():
            raise Rejected("empty workflow_ref")
        try:
            terms = json.loads(terms_json)
        except (TypeError, ValueError):
            raise Rejected("malformed terms_json")
        if not isinstance(terms, dict):
            raise Rejected("terms must be a JSON object")
        raw = terms_json.encode("utf-8")
        if len(raw) > MAX_TERMS_BYTES:
            raise Rejected("terms exceed maxTermsBytes")
        pact = {
            "pact_id": pxid,
            "path_id": str(path_id),
            "workflow_ref": str(workflow_ref),
            "terms": terms,
            "proposed_at": _parse_int(proposed_at, "proposed_at"),
            "status": PACT_PROPOSED,
        }
        self.pacts[pxid] = pact
        return self._canonical_pact(pact)

    def accept_pact(self, sender, pact_id, at_timestamp=None):
        pact = self._get_pact_or_raise(pact_id)
        path = self._get_path_or_raise(pact["path_id"])
        # Only the Path principal may accept (sender compared insensitively).
        if _norm_addr(sender) != _norm_addr(path["principal"]):
            raise Rejected("only the Path principal may accept")
        if pact["status"] != PACT_PROPOSED:
            raise Rejected("pact not in PROPOSED state")
        ts = at_timestamp
        if ts is None:
            raise Rejected("acceptance requires a timestamp context")
        if _path_status(path, _parse_int(ts, "at_timestamp")) != PATH_ACTIVE:
            raise Rejected("acceptance requires an ACTIVE Path")
        pact["accepted_at"] = _parse_int(ts, "at_timestamp")
        pact["status"] = PACT_ACCEPTED
        return self._canonical_pact(pact)

    def void_pact(self, sender, pact_id):
        pact = self._get_pact_or_raise(pact_id)
        if pact["status"] in (PACT_EXECUTED, PACT_VOID):
            raise Rejected("terminal states immutable")
        pact["status"] = PACT_VOID
        return self._canonical_pact(pact)

    def execute_pact(self, sender, pact_id, action_amount, at_timestamp):
        """Fail-closed decision gate. DENY never mutates anything."""
        pact = self.pacts.get(str(pact_id))
        if pact is None:
            return self._decision("DENY", "PACT_NOT_ACCEPTED")
        if pact["status"] == PACT_EXECUTED:
            raise Rejected("executed pact reuse rejected")
        if pact["status"] != PACT_ACCEPTED:
            return self._decision("DENY", "PACT_NOT_ACCEPTED")
        path = self.paths.get(pact["path_id"])
        if path is None:
            return self._decision("DENY", "PATH_NOT_ACTIVE")
        ts = _parse_int(at_timestamp, "at_timestamp")
        eff = _path_status(path, ts)
        if eff == PATH_REVOKED:
            return self._decision("DENY", "PATH_NOT_ACTIVE")
        if eff == PATH_EXPIRED:
            return self._decision("DENY", "PATH_EXPIRED")
        amount = _parse_int(action_amount, "action_amount")
        if amount > int(path["max_per_action"]):
            return self._decision("DENY", "EXCEEDS_PATH_BOUND")
        pact["status"] = PACT_EXECUTED
        pact["executed_at"] = ts
        pact["executed_amount"] = str(amount)
        return self._decision("AUTHORIZE", "WITHIN_DELEGATED_AUTHORITY")

    # ---------------- views ----------------

    def get_path(self, path_id):
        path = self.paths.get(str(path_id))
        return "" if path is None else json.dumps(self._canonical_path(path))

    def get_pact(self, pact_id):
        pact = self.pacts.get(str(pact_id))
        return "" if pact is None else json.dumps(self._canonical_pact(pact))

    # ---------------- internals ----------------

    def _get_path_or_raise(self, path_id):
        path = self.paths.get(str(path_id))
        if path is None:
            raise Rejected("unknown path_id")
        return path

    def _get_pact_or_raise(self, pact_id):
        pact = self.pacts.get(str(pact_id))
        if pact is None:
            raise Rejected("unknown pact_id")
        return pact

    @staticmethod
    def _canonical_path(path):
        return {
            "path_id": path["path_id"],
            "principal": path["principal"],
            "agent": path["agent"],
            "purpose_scope": path["purpose_scope"],
            "max_per_action": path["max_per_action"],
            "asset": path["asset"],
            "valid_after": str(path["valid_after"]),
            "valid_until": str(path["valid_until"]),
            "status": path["status"],
        }

    @staticmethod
    def _canonical_pact(pact):
        out = {
            "pact_id": pact["pact_id"],
            "path_id": pact["path_id"],
            "workflow_ref": pact["workflow_ref"],
            "terms": json.dumps(pact["terms"], sort_keys=True),
            "proposed_at": str(pact["proposed_at"]),
            "status": pact["status"],
        }
        if "accepted_at" in pact:
            out["accepted_at"] = str(pact["accepted_at"])
        if "executed_at" in pact:
            out["executed_at"] = str(pact["executed_at"])
        if "executed_amount" in pact:
            out["executed_amount"] = pact["executed_amount"]
        return out

    @staticmethod
    def _decision(decision, reason_code):
        return {"decision": decision, "reason_code": reason_code}


# ================= vector runner =================

def run_vectors(vectors_doc):
    results = []
    for vec in vectors_doc.get("vectors", []):
        contract = WorkflowAuthorization()
        ok = True
        detail = []
        for action in vec.get("actions", []):
            op = action["op"]
            args = action.get("args", [])
            expect = action.get("expect", "ok")
            try:
                outcome = _invoke(contract, op, args)
                step_ok = _matches(outcome, expect)
            except Rejected:
                step_ok = expect == "reject"
            except Exception as e:  # unexpected failure => FAIL
                step_ok = False
                outcome = "unexpected:%s" % e
            if not step_ok:
                ok = False
                detail.append({"op": op, "args": args, "expect": repr(expect),
                               "got": repr(outcome)})
        results.append({"id": vec["id"], "pass": ok, "failures": detail})
    return results


def _invoke(contract, op, args):
    """Sender-neutral dispatch under a single fixed runner sender.

    The runner operates as one fixed sender (per the vector-file note);
    principal-only acceptance therefore lives in direct tests, while the
    deterministic gates exercised by the vectors are sender-independent.
    """
    def _unwrap(result):
        return json.loads(result) if isinstance(result, str) else result

    fixed_sender = "PRINCIPAL-A"
    if op == "grant_path":
        return _unwrap(contract.grant_path(fixed_sender, *args))
    if op == "revoke_path":
        return _unwrap(contract.revoke_path(fixed_sender, *args))
    if op == "propose_pact":
        return _unwrap(contract.propose_pact(fixed_sender, *args))
    if op == "void_pact":
        return _unwrap(contract.void_pact(fixed_sender, *args))
    if op == "execute_pact":
        r = contract.execute_pact(fixed_sender, *args)
        return r if isinstance(r, dict) else json.loads(r)
    if op == "get_path":
        raw = contract.get_path(*args)
        return "" if raw == "" else json.loads(raw)
    if op == "get_pact":
        raw = contract.get_pact(*args)
        return "" if raw == "" else json.loads(raw)
    raise Rejected("unknown op %s" % op)


def _matches(outcome, expect):
    if expect == "ok":
        return isinstance(outcome, dict)
    if expect == "reject":
        return False  # only reachable via caught Rejected
    if expect == "":
        return outcome == ""
    if isinstance(expect, dict):
        if not isinstance(outcome, dict):
            return False
        return all(k in outcome and str(outcome[k]) == str(v)
                   for k, v in expect.items())
    return outcome == expect


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python3 your_build.py <vectors.json>")
        sys.exit(2)
    with open(sys.argv[1]) as f:
        doc = json.load(f)
    all_pass = True
    for res in run_vectors(doc):
        status = "PASS" if res["pass"] else "FAIL"
        print("%s %s" % (res["id"], status))
        for f_ in res["failures"]:
            print("   step mismatch: %s -> %s" % (f_["op"], f_["got"]))
            print("     expected: %s" % f_["expect"])
        all_pass = all_pass and res["pass"]
    sys.exit(0 if all_pass else 1)
