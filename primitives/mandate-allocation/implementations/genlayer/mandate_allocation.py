# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
"""Mandate Allocation primitive (GenLayer) v0.1.

Evaluates admissible opportunities against a financing mandate and returns a
structured advisory recommendation. Deterministic hard constraints (asset,
opportunity class, exposure capacity) gate eligibility; qualitative mandate
preferences are expressed upstream via Policy Envelope interpretation and
bound here only as a hash, so the v0.1 canonical decision is fully
deterministic (EXACT).

Article V: a result is NOT authority, commitment, or encumbrance; it cannot
move value. DAA must independently create any downstream authority grant.
`committed_exposure` is advisory bookkeeping inside this primitive only -
it reserves nothing in any pool.

JUDGMENT_BOUNDARY = NONE for v0.1. Comparative/qualitative ranking composes
upstream (Claim Verification + Policy Envelope interpret_clause) without
changing this surface.
"""

from genlayer import *
import json

_MAX_CLASSES_BYTES = 2048


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


def _valid_int_ts(s: str) -> bool:
    if not s:
        return False
    body = s[1:] if s.startswith("-") else s
    return body.isdecimal()


def _canonical(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


class MandateAllocation(gl.Contract):
    mandates: TreeMap[str, str]
    evaluations: TreeMap[str, str]

    def __init__(self) -> None:
        pass

    @gl.public.write
    def register_mandate(
        self,
        mandate_id: str,
        doc_hash: str,
        max_total_exposure: str,
        asset: str,
        allowed_classes_json: str,
    ) -> str:
        if not mandate_id or not doc_hash or not asset:
            raise ValueError("MandateAllocation: empty required field")
        if not _valid_uint(max_total_exposure):
            raise ValueError("MandateAllocation: max_total_exposure must be positive uint-string")
        try:
            allowed_classes = json.loads(allowed_classes_json)
        except Exception:
            raise ValueError("MandateAllocation: malformed allowed_classes JSON")
        if not isinstance(allowed_classes, list):
            raise ValueError("MandateAllocation: allowed_classes must be a list")
        if len(allowed_classes_json.encode("utf-8")) > _MAX_CLASSES_BYTES:
            raise ValueError("MandateAllocation: allowed_classes too large")
        if mandate_id in self.mandates:
            raise ValueError("MandateAllocation: mandate already exists")
        record = {
            "mandate_id": mandate_id,
            "doc_hash": doc_hash,
            "max_total_exposure": max_total_exposure,
            "asset": asset,
            "allowed_classes": allowed_classes,
            "committed_exposure": "0",
        }
        canonical = _canonical(record)
        self.mandates[mandate_id] = canonical
        return canonical

    @gl.public.write
    def evaluate_opportunity(
        self,
        evaluation_id: str,
        mandate_id: str,
        opportunity_ref: str,
        opportunity_class: str,
        requested_amount: str,
        at_timestamp: str,
    ) -> str:
        """Deterministic advisory evaluation against hard mandate constraints."""
        mandate_record = self.mandates.get(mandate_id, "")
        if not mandate_record:
            raise ValueError("MandateAllocation: unknown mandate")
        if not evaluation_id or not opportunity_ref:
            raise ValueError("MandateAllocation: empty required field")
        if evaluation_id in self.evaluations:
            raise ValueError("MandateAllocation: evaluation already exists")
        if not _valid_uint(requested_amount):
            raise ValueError("MandateAllocation: requested_amount must be positive uint-string")
        if not _valid_int_ts(at_timestamp):
            raise ValueError("MandateAllocation: invalid timestamp")

        mandate = json.loads(mandate_record)

        # Fail-closed deterministic gates.
        # v0.1: opportunity assets are bound by upstream composition
        # (claim-verification / proof-of-payable validate the underlying claim);
        # the mandate's own asset is the admissible one here.
        if opportunity_class not in mandate["allowed_classes"]:
            return self._record(evaluation_id, mandate_id, opportunity_ref, requested_amount,
                                "INELIGIBLE", "CLASS_NOT_PERMITTED")
        if int(requested_amount) > int(mandate["max_total_exposure"]):
            return self._record(evaluation_id, mandate_id, opportunity_ref, requested_amount,
                                "INELIGIBLE", "EXPOSURE_EXCEEDED")
        committed = int(mandate["committed_exposure"])
        if committed + int(requested_amount) > int(mandate["max_total_exposure"]):
            return self._record(evaluation_id, mandate_id, opportunity_ref, requested_amount,
                                "INELIGIBLE", "EXPOSURE_EXCEEDED")

        # ELIGIBLE consumes advisory exposure capacity.
        mandate["committed_exposure"] = str(committed + int(requested_amount))
        self.mandates[mandate_id] = _canonical(mandate)
        return self._record(evaluation_id, mandate_id, opportunity_ref, requested_amount,
                            "ELIGIBLE", "WITHIN_MANDATE")

    @gl.public.write
    def supersede_evaluation(self, old_evaluation_id: str, new_evaluation_id: str, note_json: str) -> str:
        """Mark an older evaluation SUPERSEDED and link its successor."""
        old = self._get_evaluation(old_evaluation_id)
        if old["status"] != "EVALUATED":
            raise ValueError("MandateAllocation: evaluation not supersable")
        if old_evaluation_id == new_evaluation_id:
            raise ValueError("MandateAllocation: cannot supersede with itself")
        if new_evaluation_id in self.evaluations:
            raise ValueError("MandateAllocation: successor already exists")
        try:
            note = json.loads(note_json)
        except Exception:
            raise ValueError("MandateAllocation: malformed note JSON")

        # Pre-register the successor binding so lineage stays auditable.
        self.evaluations[new_evaluation_id] = _canonical({
            "evaluation_id": new_evaluation_id,
            "mandate_id": old["mandate_id"],
            "opportunity_ref": old["opportunity_ref"],
            "eligibility": old["eligibility"],
            "reason_code": old["reason_code"],
            "recommended_amount": old["recommended_amount"],
            "status": "EVALUATED",
            "supersedes": old_evaluation_id,
            "note": note,
        })
        old["status"] = "SUPERSEDED"
        self.evaluations[old_evaluation_id] = _canonical(old)
        return _canonical({
            "superseded": old_evaluation_id,
            "successor": new_evaluation_id,
        })

    def _record(self, evaluation_id, mandate_id, opportunity_ref, amount, eligibility, reason_code) -> str:
        record = {
            "evaluation_id": evaluation_id,
            "mandate_id": mandate_id,
            "opportunity_ref": opportunity_ref,
            "eligibility": eligibility,
            "reason_code": reason_code,
            "recommended_amount": amount,
            "status": "EVALUATED",
        }
        canonical = _canonical(record)
        self.evaluations[evaluation_id] = canonical
        return canonical

    @gl.public.view
    def get_mandate(self, mandate_id: str) -> str:
        return self.mandates.get(mandate_id, "")

    @gl.public.view
    def get_evaluation(self, evaluation_id: str) -> str:
        return self.evaluations.get(evaluation_id, "")

    @gl.public.view
    def committed_exposure(self, mandate_id: str) -> str:
        record = self.mandates.get(mandate_id, "")
        if not record:
            return ""
        return json.loads(record)["committed_exposure"]

    def _get_evaluation(self, evaluation_id: str) -> dict:
        record = self.evaluations.get(evaluation_id, "")
        if not record:
            raise ValueError("MandateAllocation: unknown evaluation")
        return json.loads(record)
