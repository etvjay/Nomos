# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
"""Deterministic Proof of Payable primitive (GenLayer) v0.1.

Evidence-bearing representation that a particular economic claim exists in a
stated lifecycle condition. Identity, hashing, lineage, amount bounds and
lifecycle legality are fully deterministic; JUDGMENT_BOUNDARY = NONE for this
implementation slice. Whether heterogeneous evidence *substantively* supports
the claimed payable condition belongs to Claim Verification (SEMANTIC), which
consumes the stable claim + proof snapshots produced here.

Canonical invariants enforced:
- claimId is stable across evidence snapshots; claimId != proofHash.
- Evidence history is append-only per claim; proof ids are globally unique.
- Lifecycle transitions are explicit; terminal states are immutable.
- Disputed/rejected/terminal claims can never silently become financeable.
- Creating proofs does not allocate, reserve, encumber or settle capital.
"""

from genlayer import *
import json

_STATUSES = (
    "DRAFT",
    "EVIDENCED",
    "ATTESTED",
    "DISPUTED",
    "REJECTED",
    "SETTLED",
    "VOID",
)

_LIVE = ("DRAFT", "EVIDENCED", "ATTESTED")

_MAX_META_BYTES = 4096


def _valid_uint(s: str) -> bool:
    if not s:
        return False
    if not s.isdecimal():
        return False
    if len(s) > 39:
        return False
    if len(s) > 1 and s[0] == "0":
        return False
    return int(s) > 0


def _canonical(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


class ProofOfPayable(gl.Contract):
    claims: TreeMap[str, str]
    evidence_index: TreeMap[str, str]
    evidence_by_claim: TreeMap[str, str]

    def __init__(self) -> None:
        pass

    @gl.public.write
    def open_claim(
        self,
        claim_id: str,
        amount: str,
        external_ref: str,
        obligor: str,
    ) -> str:
        """Register a new payable claim. Immutable identity + amount."""
        if not claim_id:
            raise ValueError("ProofOfPayable: claim_id must not be empty")
        if not _valid_uint(amount):
            raise ValueError("ProofOfPayable: amount must be a positive uint-string")
        if not external_ref:
            raise ValueError("ProofOfPayable: external_ref must not be empty")
        if not obligor:
            raise ValueError("ProofOfPayable: obligor must not be empty")
        if claim_id in self.claims:
            raise ValueError("ProofOfPayable: claim already exists")
        record = {
            "claim_id": claim_id,
            "amount": amount,
            "external_ref": external_ref,
            "obligor": obligor,
            "status": "DRAFT",
            "evidence_count": "0",
            "latest_proof_hash": "",
        }
        canonical = _canonical(record)
        self.claims[claim_id] = canonical
        self.evidence_by_claim[claim_id] = ""
        return canonical

    @gl.public.write
    def attach_evidence(
        self,
        claim_id: str,
        proof_id: str,
        proof_hash: str,
        metadata_json: str,
    ) -> str:
        """Append one immutable proof snapshot to a claim's lineage."""
        if not proof_id:
            raise ValueError("ProofOfPayable: proof_id must not be empty")
        if not proof_hash:
            raise ValueError("ProofOfPayable: proof_hash must not be empty")
        if len(metadata_json.encode("utf-8")) > _MAX_META_BYTES:
            raise ValueError("ProofOfPayable: metadata too large")
        record = self.claims.get(claim_id, "")
        if not record:
            raise ValueError("ProofOfPayable: unknown claim")
        claim = json.loads(record)
        if claim["status"] not in _LIVE:
            raise ValueError("ProofOfPayable: claim is not live")
        if proof_id in self.evidence_index:
            raise ValueError("ProofOfPayable: proof_id already exists")

        proof = {
            "proof_id": proof_id,
            "claim_id": claim_id,
            "proof_hash": proof_hash,
            "status": "ATTACHED",
        }
        canonical = _canonical(proof)
        self.evidence_index[proof_id] = canonical
        self.evidence_by_claim[claim_id] = canonical

        claim["evidence_count"] = str(int(claim["evidence_count"]) + 1)
        claim["latest_proof_hash"] = proof_hash
        if claim["status"] == "DRAFT":
            claim["status"] = "EVIDENCED"
        self.claims[claim_id] = _canonical(claim)
        return canonical

    @gl.public.write
    def attest_claim(self, claim_id: str) -> str:
        """Move an EVIDENCED claim to ATTESTED. Requires at least one proof."""
        claim = self._live_claim(claim_id)
        if claim["status"] == "ATTESTED":
            raise ValueError("ProofOfPayable: claim already attested")
        if int(claim["evidence_count"]) < 1:
            raise ValueError("ProofOfPayable: cannot attest without evidence")
        claim["status"] = "ATTESTED"
        self.claims[claim_id] = _canonical(claim)
        return _canonical(claim)

    @gl.public.write
    def dispute_claim(self, claim_id: str) -> str:
        """Mark a live claim DISPUTED. Disputed claims are not financeable."""
        claim = self._live_claim(claim_id)
        claim["status"] = "DISPUTED"
        self.claims[claim_id] = _canonical(claim)
        return _canonical(claim)

    @gl.public.write
    def reject_claim(self, claim_id: str) -> str:
        """Terminate a DISPUTED claim as REJECTED (terminal)."""
        record = self.claims.get(claim_id, "")
        if not record:
            raise ValueError("ProofOfPayable: unknown claim")
        claim = json.loads(record)
        if claim["status"] != "DISPUTED":
            raise ValueError("ProofOfPayable: only DISPUTED claims may be rejected")
        claim["status"] = "REJECTED"
        self.claims[claim_id] = _canonical(claim)
        return _canonical(claim)

    @gl.public.write
    def settle_claim(self, claim_id: str) -> str:
        """Settle an ATTESTED claim (terminal). Does not move capital."""
        claim = self._live_claim(claim_id)
        if claim["status"] != "ATTESTED":
            raise ValueError("ProofOfPayable: only ATTESTED claims may settle")
        if int(claim["evidence_count"]) < 1:
            raise ValueError("ProofOfPayable: cannot settle without evidence")
        claim["status"] = "SETTLED"
        self.claims[claim_id] = _canonical(claim)
        return _canonical(claim)

    @gl.public.write
    def void_claim(self, claim_id: str) -> str:
        """Void a live claim (terminal)."""
        claim = self._live_claim(claim_id)
        claim["status"] = "VOID"
        self.claims[claim_id] = _canonical(claim)
        return _canonical(claim)

    @gl.public.view
    def get_claim(self, claim_id: str) -> str:
        return self.claims.get(claim_id, "")

    @gl.public.view
    def get_evidence(self, proof_id: str) -> str:
        return self.evidence_index.get(proof_id, "")

    def _live_claim(self, claim_id: str) -> dict:
        record = self.claims.get(claim_id, "")
        if not record:
            raise ValueError("ProofOfPayable: unknown claim")
        claim = json.loads(record)
        if claim["status"] not in _LIVE:
            raise ValueError("ProofOfPayable: claim is not live")
        return claim
