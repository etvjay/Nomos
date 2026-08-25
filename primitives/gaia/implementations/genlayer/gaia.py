# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
"""Gaia — Exception, Reconciliation & Rectification (GenLayer) v0.1.

Cross-cutting exception plane: cases classify exceptional state and prescribe
bounded RectificationObligations. Gaia never executes remedies and never
rewrites history — resolution requires every obligation to be explicitly
discharged (with evidence hash) or waived, and the resolved state is terminal.

JUDGMENT_BOUNDARY = NONE for the v0.1 canonical slice. Classification of
ambiguous exceptions is expressed through a bounded obligation vocabulary
supplied by the caller (the interpreting party); the contract enforces the
deterministic skeleton: vocabulary membership, append-only history,
obligation-completeness gating, evidence binding. Free-form LLM
classification can be layered upstream without changing this surface.

Article V/X: failure does not create authority; executing any prescribed
remedy (retry, refund, correction) must pass ordinary Workflow Authorization.
"""

from genlayer import *
import json

_ALLOWED_TYPES = (
    "refund",
    "retry",
    "provide_evidence",
    "correct_usage_record",
    "reconcile",
    "manual_review",
)

_MAX_FACTS_BYTES = 4096
_MAX_OBLIGATIONS = 8

# Economic exception categories (open-ended but must be declared, not free text)
_ALLOWED_CATEGORIES = (
    "settlement-mismatch",
    "delivery-mismatch",
    "duplicate-execution",
    "stale-evidence",
    "unauthorized-action",
    "reconciliation-failure",
    "other",
)


def _canonical(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


class Gaia(gl.Contract):
    cases: TreeMap[str, str]
    obligations: TreeMap[str, str]

    def __init__(self) -> None:
        pass

    @gl.public.write
    def open_case(
        self,
        case_id: str,
        category: str,
        subject_ref: str,
        facts_json: str,
    ) -> str:
        if not case_id or not category or not subject_ref:
            raise ValueError("Gaia: empty required field")
        if category not in _ALLOWED_CATEGORIES:
            raise ValueError("Gaia: unknown case category")
        if len(facts_json.encode("utf-8")) > _MAX_FACTS_BYTES:
            raise ValueError("Gaia: facts too large")
        try:
            facts = json.loads(facts_json)
        except Exception:
            raise ValueError("Gaia: malformed facts JSON")
        if not isinstance(facts, dict):
            raise ValueError("Gaia: facts must be an object")
        if case_id in self.cases:
            raise ValueError("Gaia: case already exists")
        record = {
            "case_id": case_id,
            "category": category,
            "subject_ref": subject_ref,
            "facts": facts,
            "status": "OPEN",
            "resolution_evidence_hash": "",
        }
        canonical = _canonical(record)
        self.cases[case_id] = canonical
        return canonical

    @gl.public.write
    def classify_case(self, case_id: str, classification_id: str, obligations_json: str) -> str:
        """Attach bounded rectification obligations; OPEN -> CLASSIFIED.

        `obligations_json` is a list of {"type": <allowed>, "bound": {...}}.
        Obligation ids are derived deterministically as
        `<classification_id>-O<index>`.
        """
        case = self._get_case(case_id)
        if case["status"] != "OPEN":
            raise ValueError("Gaia: case already classified")
        if not classification_id:
            raise ValueError("Gaia: classification_id required")
        try:
            obligations = json.loads(obligations_json)
        except Exception:
            raise ValueError("Gaia: malformed obligations JSON")
        if not isinstance(obligations, list) or not (1 <= len(obligations) <= _MAX_OBLIGATIONS):
            raise ValueError("Gaia: obligations must be a non-empty list (max %d)" % _MAX_OBLIGATIONS)
        for ob in obligations:
            if not isinstance(ob, dict) or ob.get("type") not in _ALLOWED_TYPES:
                raise ValueError("Gaia: unknown obligation type")

        for i, ob in enumerate(obligations):
            record = {
                "obligation_id": "%s-O%d" % (classification_id, i),
                "case_id": case_id,
                "type": ob["type"],
                "bound": ob.get("bound", {}),
                "status": "PRESCRIBED",
                "evidence_hash": "",
                "waiver_note": "",
            }
            self.obligations[record["obligation_id"]] = _canonical(record)

        case["status"] = "CLASSIFIED"
        self.cases[case_id] = _canonical(case)
        return _canonical({
            "classification_id": classification_id,
            "case_id": case_id,
            "obligations": ["%s-O%d" % (classification_id, i) for i in range(len(obligations))],
        })

    @gl.public.write
    def discharge_obligation(self, obligation_id: str, evidence_hash: str) -> str:
        """Explicitly satisfy one obligation with auditable evidence."""
        obligation = self._get_obligation(obligation_id)
        if obligation["status"] != "PRESCRIBED":
            raise ValueError("Gaia: obligation already dispositioned")
        if not evidence_hash:
            raise ValueError("Gaia: discharge requires evidence hash")
        obligation["status"] = "DISCHARGED"
        obligation["evidence_hash"] = evidence_hash
        self.obligations[obligation_id] = _canonical(obligation)
        return _canonical(obligation)

    @gl.public.write
    def waive_obligation(self, obligation_id: str, waiver_note: str) -> str:
        """Explicitly waive one obligation with a recorded justification."""
        obligation = self._get_obligation(obligation_id)
        if obligation["status"] != "PRESCRIBED":
            raise ValueError("Gaia: obligation already dispositioned")
        if not waiver_note:
            raise ValueError("Gaia: waiver requires a note")
        obligation["status"] = "WAIVED"
        obligation["waiver_note"] = waiver_note
        self.obligations[obligation_id] = _canonical(obligation)
        return _canonical(obligation)

    @gl.public.write
    def resolve_case(self, case_id: str, resolution_evidence_hash: str) -> str:
        """Resolve a CLASSIFIED case once ALL obligations are dispositioned."""
        case = self._get_case(case_id)
        if case["status"] == "RESOLVED":
            raise ValueError("Gaia: case already resolved")
        if case["status"] != "CLASSIFIED":
            raise ValueError("Gaia: unclassified case cannot resolve")
        if not resolution_evidence_hash:
            raise ValueError("Gaia: resolution requires evidence hash")
        # Deterministic completeness gate over the classification namespace.
        # Obligation ids are <classification_id>-O<i>; we scan all obligations
        # bound to this case via the stored index built at classification time.
        for ob_id, ob_json in self.obligations.items():
            ob = json.loads(ob_json)
            if ob["case_id"] == case_id and ob["status"] == "PRESCRIBED":
                raise ValueError("Gaia: pending obligations remain")
        case["status"] = "RESOLVED"
        case["resolution_evidence_hash"] = resolution_evidence_hash
        self.cases[case_id] = _canonical(case)
        return _canonical(case)

    @gl.public.view
    def get_case(self, case_id: str) -> str:
        return self.cases.get(case_id, "")

    @gl.public.view
    def get_obligation(self, obligation_id: str) -> str:
        return self.obligations.get(obligation_id, "")

    def _get_case(self, case_id: str) -> dict:
        record = self.cases.get(case_id, "")
        if not record:
            raise ValueError("Gaia: unknown case")
        return json.loads(record)

    def _get_obligation(self, obligation_id: str) -> dict:
        record = self.obligations.get(obligation_id, "")
        if not record:
            raise ValueError("Gaia: unknown obligation")
        return json.loads(record)
