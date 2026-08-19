# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

"""Nomos Claim Verification v0.1.

Turns caller-supplied claim evidence into a bounded consensus-backed decision.
Canonical state intentionally stores only stable decision fields; free-form LLM
reasoning is not part of the financial state machine.
"""

import json
from genlayer import *


_ALLOWED_STATUS = (
    "VERIFIED",
    "CONFLICTED",
    "INSUFFICIENT",
    "UNDETERMINED",
)

_ALLOWED_REASON = (
    "EVIDENCE_SUPPORTS_CLAIM",
    "MATERIAL_CONFLICT",
    "MISSING_ESSENTIAL_EVIDENCE",
    "EVIDENCE_AMBIGUOUS",
)

_MAX_CLAIM_BYTES = 16_384
_MAX_EVIDENCE_BYTES = 32_768


class ClaimVerification(gl.Contract):
    """Reusable verification primitive for financial applications on GenLayer."""

    # verification_id -> canonical JSON decision
    decisions: TreeMap[str, str]

    def __init__(self):
        pass

    def _evaluate(self, claim_json: str, evidence_json: str) -> dict:
        """Run the non-deterministic evaluation under a narrow equivalence rule."""

        prompt = f"""
You are validating evidence for a financial claim.

CLAIM:
{claim_json}

EVIDENCE:
{evidence_json}

Classify ONLY whether the supplied evidence substantively supports the supplied
claim. Do not assess borrower creditworthiness, allocate capital, reserve funds,
or decide settlement.

Return JSON with exactly these fields:
{{
  "status": "VERIFIED" | "CONFLICTED" | "INSUFFICIENT" | "UNDETERMINED",
  "reason_code": "EVIDENCE_SUPPORTS_CLAIM" | "MATERIAL_CONFLICT" | "MISSING_ESSENTIAL_EVIDENCE" | "EVIDENCE_AMBIGUOUS",
  "analysis": "brief explanation"
}}

Interpretation:
- VERIFIED: evidence substantively supports the claim and contains no material conflict.
- CONFLICTED: supplied evidence contains a material contradiction affecting the claim.
- INSUFFICIENT: essential evidence needed to establish the claim is missing.
- UNDETERMINED: evidence is present but remains genuinely ambiguous.

The status and reason_code must correspond:
VERIFIED -> EVIDENCE_SUPPORTS_CLAIM
CONFLICTED -> MATERIAL_CONFLICT
INSUFFICIENT -> MISSING_ESSENTIAL_EVIDENCE
UNDETERMINED -> EVIDENCE_AMBIGUOUS
"""

        def leader_fn() -> dict:
            result = gl.nondet.exec_prompt(prompt, response_format="json")
            if not isinstance(result, dict):
                raise gl.vm.UserError("ClaimVerification: evaluator returned non-object")

            status = str(result.get("status", ""))
            reason = str(result.get("reason_code", ""))
            if status not in _ALLOWED_STATUS:
                raise gl.vm.UserError("ClaimVerification: invalid status")
            if reason not in _ALLOWED_REASON:
                raise gl.vm.UserError("ClaimVerification: invalid reason_code")

            expected_reason = {
                "VERIFIED": "EVIDENCE_SUPPORTS_CLAIM",
                "CONFLICTED": "MATERIAL_CONFLICT",
                "INSUFFICIENT": "MISSING_ESSENTIAL_EVIDENCE",
                "UNDETERMINED": "EVIDENCE_AMBIGUOUS",
            }[status]
            if reason != expected_reason:
                raise gl.vm.UserError("ClaimVerification: inconsistent status/reason_code")

            return {
                "status": status,
                "reason_code": reason,
                "analysis": str(result.get("analysis", "")),
            }

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False

            validator_result = leader_fn()
            leader_data = leader_result.calldata

            # Consensus concerns the financial decision, not prose wording.
            return (
                leader_data["status"] == validator_result["status"]
                and leader_data["reason_code"] == validator_result["reason_code"]
            )

        return gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

    @gl.public.write
    def verify_claim(
        self,
        verification_id: str,
        claim_id: str,
        evidence_digest: str,
        claim_json: str,
        evidence_json: str,
    ) -> str:
        """Create one immutable verification decision.

        `evidence_digest` is supplied by the caller/application so downstream
        systems can bind the result to the exact immutable evidence snapshot.
        Nomos v0.1 does not fetch or hash remote evidence inside this primitive.
        """

        verification_id = verification_id.strip()
        claim_id = claim_id.strip()
        evidence_digest = evidence_digest.strip()

        if not verification_id:
            raise gl.vm.UserError("ClaimVerification: verification_id required")
        if not claim_id:
            raise gl.vm.UserError("ClaimVerification: claim_id required")
        if not evidence_digest:
            raise gl.vm.UserError("ClaimVerification: evidence_digest required")
        if verification_id in self.decisions:
            raise gl.vm.UserError("ClaimVerification: verification_id already exists")
        if len(claim_json.encode("utf-8")) > _MAX_CLAIM_BYTES:
            raise gl.vm.UserError("ClaimVerification: claim payload too large")
        if len(evidence_json.encode("utf-8")) > _MAX_EVIDENCE_BYTES:
            raise gl.vm.UserError("ClaimVerification: evidence payload too large")

        # Deterministically reject malformed JSON before any non-deterministic work.
        try:
            claim_obj = json.loads(claim_json)
            evidence_obj = json.loads(evidence_json)
        except Exception:
            raise gl.vm.UserError("ClaimVerification: malformed JSON")

        if not isinstance(claim_obj, dict):
            raise gl.vm.UserError("ClaimVerification: claim must be an object")
        if not isinstance(evidence_obj, (dict, list)):
            raise gl.vm.UserError("ClaimVerification: evidence must be object or list")

        result = self._evaluate(claim_json, evidence_json)

        decision = {
            "verification_id": verification_id,
            "claim_id": claim_id,
            "evidence_digest": evidence_digest,
            "status": result["status"],
            "reason_code": result["reason_code"],
            "requested_by": gl.message.sender_address.as_hex,
        }
        canonical = json.dumps(decision, sort_keys=True, separators=(",", ":"))
        self.decisions[verification_id] = canonical
        return canonical

    @gl.public.view
    def get_verification(self, verification_id: str) -> str:
        return self.decisions.get(verification_id, "")

    @gl.public.view
    def has_verification(self, verification_id: str) -> bool:
        return verification_id in self.decisions
