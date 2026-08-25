#!/usr/bin/env python3
"""Proof of Payable - Nomos primitive, independent convergence-lane build.

Capability version 0.1.0 · Convergence mode EXACT · JUDGMENT_BOUNDARY = NONE

GenLayer contract conventions (gl.Contract, TreeMap storage, decorators) are
expressed in the class below; a local shim lets the same file run the canonical
vectors on plain CPython via `python3 your_build.py <vectors.json>`.
"""

import json
import sys

# ---------------------------------------------------------------------------
# GenLayer runtime shims (no-op under real GenVM where `gl` exists)
# ---------------------------------------------------------------------------
try:
    import gl  # type: ignore
    from gl import Contract as _GLBase, TreeMap as _TreeMap  # type: ignore
except Exception:  # local vector-runner execution
    class _TreeMap(dict):
        """Minimal stand-in for gl.TreeMap keyed storage."""

        def has(self, k):
            return k in self

        def get(self, k):
            return self.get_(k)

        def get_(self, k):
            return dict.get(self, k)

        def set(self, k, v):
            self[k] = v

        def delete(self, k):
            dict.pop(self, k, None)

    class _GLBase:
        pass

    class gl:  # noqa: N801 - mirrors module name
        Contract = _GLBase
        TreeMap = _TreeMap

        @staticmethod
        def log(evt):  # event stub
            pass


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class Reject(Exception):
    """Deterministic rejection of a mutation."""


# ---------------------------------------------------------------------------
# Canonical helpers
# ---------------------------------------------------------------------------
def canonical(obj):
    """Canonical JSON serialization: sorted keys, no whitespace."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def valid_uint_string(s):
    if not isinstance(s, str) or s == "":
        return False
    if not s.isdigit():  # rejects '', '-5', 'abc', '1.0', '+1', whitespace
        return False
    stripped = s.lstrip("0")
    return True if stripped else False  # '0' and '00' are non-positive


def require_nonempty(s):
    if not isinstance(s, str) or s == "":
        raise Reject("empty identifier")
    return s


MAX_METADATA_BYTES = 4096


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------
class ProofOfPayable(gl.Contract):
    """
    State ownership:
      claims:   claim_id -> canonical-claim record (identity + lifecycle)
      proofs:   proof_id -> proof record (globally unique, append-only)
      lineage:  claim_id -> ordered list of proof_id (append-only)
      counts:   claim_id -> evidence count (string)

    Does NOT own: capital allocation/reservation/encumbrance/settlement,
    verification judgment over evidence content, replay lanes.
    """

    JUDGMENT_BOUNDARY = "NONE"

    STATUSES = ("DRAFT", "EVIDENCED", "ATTESTED", "DISPUTED",
                "REJECTED", "SETTLED", "VOID")
    LIVE = ("DRAFT", "EVIDENCED", "ATTESTED")
    TERMINAL = ("REJECTED", "SETTLED", "VOID")

    def __init__(self):
        self.claims = gl.TreeMap()
        self.proofs = gl.TreeMap()
        self.lineage = gl.TreeMap()
        self.counts = gl.TreeMap()

    # -- internal -----------------------------------------------------------
    def _claim_or_reject(self, claim_id):
        require_nonempty(claim_id)
        rec = self.claims.get(claim_id)
        if rec is None:
            raise Reject("unknown claim")
        return rec

    def _require_live(self, claim_id):
        rec = self._claim_or_reject(claim_id)
        if rec["status"] not in self.LIVE:
            raise Reject("terminal status rejects every mutation")
        return rec

    def _save_claim(self, rec):
        self.claims[rec["claim_id"]] = rec

    # -- write surface ------------------------------------------------------
    def open_claim(self, claim_id: str, amount: str, external_ref: str,
                   obligor: str) -> str:
        require_nonempty(claim_id)
        if not valid_uint_string(amount):
            raise Reject("amount must be a positive uint string")
        require_nonempty(external_ref)
        require_nonempty(obligor)
        if self.claims.has(claim_id):
            raise Reject("duplicate claim id")
        rec = {
            "claim_id": claim_id,
            "amount": amount,
            "external_ref": external_ref,
            "obligor": obligor,
            "status": "DRAFT",
            "evidence_count": "0",
            "latest_proof_hash": "",
            "created_at": "",
            "created_by": "",
        }
        self.claims[claim_id] = rec
        self.lineage[claim_id] = []
        self.counts[claim_id] = "0"
        gl.log({"event": "ClaimOpened", **{k: rec[k] for k in
               ("claim_id", "amount", "external_ref", "obligor")}})
        return self._public_claim(rec)

    def attach_evidence(self, claim_id: str, proof_id: str, proof_hash: str,
                        metadata_json: str) -> str:
        rec = self._require_live(claim_id)  # terminal states reject re-attach
        require_nonempty(proof_id)
        require_nonempty(proof_hash)
        if not isinstance(metadata_json, str):
            raise Reject("metadata must be a string")
        if len(metadata_json.encode("utf-8")) > MAX_METADATA_BYTES:
            raise Reject("metadata exceeds maxMetadataBytes")
        if self.proofs.has(proof_id):
            raise Reject("duplicate proof id")  # append-only lineage
        proof = {
            "proof_id": proof_id,
            "claim_id": claim_id,
            "proof_hash": proof_hash,
            "metadata_json": metadata_json,
            "status": "ATTACHED",
            "attached_at": "",
            "attached_by": "",
        }
        self.proofs[proof_id] = proof
        lineage = self.lineage.get(claim_id)
        if lineage is None:
            lineage = []
        lineage.append(proof_id)
        self.lineage[claim_id] = lineage
        n = int(rec["evidence_count"]) + 1
        rec["evidence_count"] = str(n)
        rec["latest_proof_hash"] = proof_hash
        if rec["status"] == "DRAFT":
            rec["status"] = "EVIDENCED"  # automatic DRAFT->EVIDENCED
        self._save_claim(rec)
        gl.log({"event": "EvidenceAttached", "proof_id": proof_id,
                "claim_id": claim_id, "proof_hash": proof_hash})
        return self._public_proof(proof)

    def attest_claim(self, claim_id: str) -> str:
        rec = self._claim_or_reject(claim_id)
        if rec["status"] not in ("EVIDENCED", "ATTESTED"):
            raise Reject("attest requires EVIDENCED status and evidence >= 1")
        if int(rec["evidence_count"]) < 1:
            raise Reject("attest requires evidence_count >= 1")
        rec["status"] = "ATTESTED"
        self._save_claim(rec)
        gl.log({"event": "ClaimAttested", "claim_id": claim_id})
        return self._public_claim(rec)

    def dispute_claim(self, claim_id: str) -> str:
        rec = self._require_live(claim_id)  # live statuses only
        rec["status"] = "DISPUTED"
        self._save_claim(rec)
        gl.log({"event": "ClaimDisputed", "claim_id": claim_id})
        return self._public_claim(rec)

    def reject_claim(self, claim_id: str) -> str:
        rec = self._claim_or_reject(claim_id)
        if rec["status"] != "DISPUTED":
            raise Reject("reject requires DISPUTED status")
        rec["status"] = "REJECTED"
        self._save_claim(rec)
        gl.log({"event": "ClaimRejected", "claim_id": claim_id})
        return self._public_claim(rec)

    def settle_claim(self, claim_id: str) -> str:
        rec = self._claim_or_reject(claim_id)
        if rec["status"] != "ATTESTED":
            raise Reject("settle requires ATTESTED status")
        if int(rec["evidence_count"]) < 1:
            raise Reject("settle requires evidence_count >= 1")
        rec["status"] = "SETTLED"
        self._save_claim(rec)
        gl.log({"event": "ClaimSettled", "claim_id": claim_id})
        return self._public_claim(rec)

    def void_claim(self, claim_id: str) -> str:
        rec = self._require_live(claim_id)  # live -> VOID only
        rec["status"] = "VOID"
        self._save_claim(rec)
        gl.log({"event": "ClaimVoided", "claim_id": claim_id})
        return self._public_claim(rec)

    # -- view surface -------------------------------------------------------
    def get_claim(self, claim_id: str) -> str:
        rec = self.claims.get(claim_id)
        if rec is None:
            return ""
        return self._public_claim(rec)

    def get_evidence(self, proof_id: str) -> str:
        proof = self.proofs.get(proof_id)
        if proof is None:
            return ""
        return self._public_proof(proof)

    # -- canonical public projections ----------------------------------------
    def _public_claim(self, rec):
        return canonical({
            "claim_id": rec["claim_id"],
            "amount": rec["amount"],
            "external_ref": rec["external_ref"],
            "obligor": rec["obligor"],
            "status": rec["status"],
            "evidence_count": rec["evidence_count"],
            "latest_proof_hash": rec["latest_proof_hash"],
        })

    def _public_proof(self, proof):
        return canonical({
            "proof_id": proof["proof_id"],
            "claim_id": proof["claim_id"],
            "proof_hash": proof["proof_hash"],
            "status": proof["status"],
        })


# ---------------------------------------------------------------------------
# Canonical vector runner
# ---------------------------------------------------------------------------
OPS_WRITE = {"open_claim", "attach_evidence", "attest_claim", "dispute_claim",
             "reject_claim", "settle_claim", "void_claim"}
OPS_VIEW = {"get_claim", "get_evidence"}

OP_IMPL = {
    "open_claim": lambda c, a: c.open_claim(*a),
    "attach_evidence": lambda c, a: c.attach_evidence(*a),
    "attest_claim": lambda c, a: c.attest_claim(*a),
    "dispute_claim": lambda c, a: c.dispute_claim(*a),
    "reject_claim": lambda c, a: c.reject_claim(*a),
    "settle_claim": lambda c, a: c.settle_claim(*a),
    "void_claim": lambda c, a: c.void_claim(*a),
    "get_claim": lambda c, a: c.get_claim(*a),
    "get_evidence": lambda c, a: c.get_evidence(*a),
}


def run_vector(vec):
    contract = ProofOfPayable()
    failures = []
    for i, action in enumerate(vec["actions"]):
        op, args, expect = action["op"], action["args"], action["expect"]
        try:
            result = OP_IMPL[op](contract, args)
            err = None
        except Reject as e:
            result, err = None, str(e)
        if expect == "ok":
            ok = err is None and isinstance(result, str) and result != ""
        elif expect == "reject":
            ok = err is not None
        elif expect == "":
            ok = err is None and result == ""
        else:  # canonical JSON object expectation
            ok = err is None and result == canonical(expect)
        if not ok:
            failures.append(
                f"{vec['id']} step {i} ({op} {args!r}): expected "
                f"{expect!r}, got error={err} result={result!r}")
    return failures


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else \
        "primitives/proof-of-payable/vectors/v0.1.json"
    with open(path) as f:
        suite = json.load(f)
    all_ok = True
    for vec in suite["vectors"]:
        failures = run_vector(vec)
        if failures:
            all_ok = False
            print(f"FAIL {vec['id']}")
            for fl in failures:
                print(f"     {fl}")
        else:
            print(f"PASS {vec['id']}")
    print(("ALL PASS" if all_ok else "FAILURES PRESENT"))
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
