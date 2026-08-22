# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
"""Claim Verification primitive — independent Partner-B build (GenLayer).

SEMANTIC convergence lane B for claim-verification v0.1. This is an
independent implementation of the same canonical authority (fingerprint
sha256:f0be8bab...) written without copying Partner A's code:

- different storage layout (single decisions map, same as required surface);
- different internal helper naming and validation ordering;
- identical bounded decision relation: status/reason_code vocabulary,
  mandatory status<->reason pairing, deterministic preconditions, size limits.

Convergence is judged on equivalenceFields {status, reason_code} only;
free-form analysis prose is nonCanonical by CAPABILITY.json.
"""

import json
from genlayer import *

DECISIONS = "decisions"

_STATUS_REASON = {
    "VERIFIED": "EVIDENCE_SUPPORTS_CLAIM",
    "CONFLICTED": "MATERIAL_CONFLICT",
    "INSUFFICIENT": "MISSING_ESSENTIAL_EVIDENCE",
    "UNDETERMINED": "EVIDENCE_AMBIGUOUS",
}

CLAIM_LIMIT = 16384
EVIDENCE_LIMIT = 32768


class ClaimVerificationB(gl.Contract):
    verdicts: TreeMap[str, str]

    def __init__(self):
        pass

    def _judge(self, claim_text: str, evidence_text: str) -> dict:
        question = (
            "You arbitrate a financial claim.\n"
            "CLAIM DOCUMENT:\n" + claim_text + "\n"
            "EVIDENCE PACKAGE:\n" + evidence_text + "\n"
            "Decide exactly one outcome:\n"
            "VERIFIED (evidence substantiates the claim, no contradiction),\n"
            "CONFLICTED (evidence contains a material contradiction),\n"
            "INSUFFICIENT (essential evidence absent),\n"
            "UNDETERMINED (evidence present but genuinely ambiguous).\n"
            'Answer {"status": <one of the four>, "reason_code": <paired code>,'
            ' "analysis": "<short>"} where reason_code is respectively'
            " EVIDENCE_SUPPORTS_CLAIM / MATERIAL_CONFLICT /"
            " MISSING_ESSENTIAL_EVIDENCE / EVIDENCE_AMBIGUOUS."
        )

        def leader() -> dict:
            raw = gl.nondet.exec_prompt(question, response_format="json")
            if not isinstance(raw, dict):
                raise gl.vm.UserError("ClaimVerificationB: non-object model output")
            status = raw.get("status")
            if status not in _STATUS_REASON:
                raise gl.vm.UserError("ClaimVerificationB: unknown status")
            if raw.get("reason_code") != _STATUS_REASON[status]:
                raise gl.vm.UserError("ClaimVerificationB: status/reason mismatch")
            return {
                "status": status,
                "reason_code": raw["reason_code"],
                "analysis": str(raw.get("analysis", "")),
            }

        def validators(leader_out) -> bool:
            if not isinstance(leader_out, gl.vm.Return):
                return False
            theirs = leader_out.calldata
            mine = leader()
            # Equivalence Principle: consensus binds the canonical fields only.
            return (
                theirs["status"] == mine["status"]
                and theirs["reason_code"] == mine["reason_code"]
            )

        return gl.vm.run_nondet_unsafe(leader, validators)

    @gl.public.write
    def verify_claim(
        self,
        verification_id: str,
        claim_id: str,
        evidence_digest: str,
        claim_json: str,
        evidence_json: str,
    ) -> str:
        vid = verification_id.strip()
        cid = claim_id.strip()
        digest = evidence_digest.strip()

        # Deterministic preconditions precede any nondeterministic work.
        if not vid or not cid or not digest:
            raise gl.vm.UserError("ClaimVerificationB: identifiers required")
        if vid in self.verdicts:
            raise gl.vm.UserError("ClaimVerificationB: duplicate verification_id")
        if len(claim_json.encode("utf-8")) > CLAIM_LIMIT:
            raise gl.vm.UserError("ClaimVerificationB: claim too large")
        if len(evidence_json.encode("utf-8")) > EVIDENCE_LIMIT:
            raise gl.vm.UserError("ClaimVerificationB: evidence too large")

        try:
            claim_obj = json.loads(claim_json)
            evidence_obj = json.loads(evidence_json)
        except Exception:
            raise gl.vm.UserError("ClaimVerificationB: malformed JSON")
        if not isinstance(claim_obj, dict):
            raise gl.vm.UserError("ClaimVerificationB: claim must be object")
        if not isinstance(evidence_obj, (dict, list)):
            raise gl.vm.UserError("ClaimVerificationB: evidence must be object/list")

        outcome = self._judge(claim_json, evidence_json)

        verdict = {
            "verification_id": vid,
            "claim_id": cid,
            "evidence_digest": digest,
            "status": outcome["status"],
            "reason_code": outcome["reason_code"],
            "requested_by": gl.message.sender_address.as_hex,
        }
        self.verdicts[vid] = json.dumps(
            verdict, sort_keys=True, separators=(",", ":")
        )
        return self.verdicts[vid]

    @gl.public.view
    def get_verification(self, verification_id: str) -> str:
        return self.verdicts.get(verification_id, "")

    @gl.public.view
    def has_verification(self, verification_id: str) -> bool:
        return verification_id in self.verdicts
