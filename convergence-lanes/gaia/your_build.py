"""Gaia - Exception, Reconciliation & Rectification - independent build
(convergence lane, capability v0.1.0).

Convergence mode: EXACT (judgmentBearing: false - JUDGMENT_BOUNDARY = NONE)

Dispute/exception plane: cases OPEN -> CLASSIFIED -> RESOLVED (terminal),
obligations PRESCRIBED -> DISCHARGED | WAIVED. Remedies are prescribed as
bounded compensating entries only - Gaia holds NO execution authority; any
refund/retry/correction must pass ordinary Workflow Authorization downstream.
All history is append-only: annotate, never rewrite.

Limits: facts <= 4096 bytes, 1..8 obligations per case, obligation ids
derived `<classification_id>-O<i>`, one classification per case, one
disposition per obligation.

GenLayer conventions: single contract class, writes return canonical JSON
(sorted keys, compact separators), views return canonical JSON or "".
Rejections raise.
"""

import json


JUDGMENT_BOUNDARY = "NONE"
PRIMITIVE_ID = "gaia"
CAPABILITY_VERSION = "0.1.0"

CASE_STATUSES = ("OPEN", "CLASSIFIED", "RESOLVED")
OBLIGATION_STATUSES = ("PRESCRIBED", "DISCHARGED", "WAIVED")
CATEGORIES = (
    "settlement-mismatch",
    "delivery-mismatch",
    "duplicate-execution",
    "stale-evidence",
    "unauthorized-action",
    "reconciliation-failure",
    "other",
)
OBLIGATION_TYPES = (
    "refund",
    "retry",
    "provide_evidence",
    "correct_usage_record",
    "reconcile",
    "manual_review",
)

MAX_FACTS_BYTES = 4096
MAX_OBLIGATIONS_PER_CASE = 8


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _require(cond, msg):
    if not cond:
        raise ValueError(msg)


class Gaia:
    """Exception cases with declared categories/facts and bounded rectification
    obligations and their disposition state. Owns nothing else."""

    def __init__(self):
        self._cases = {}       # case_id -> record (mutable status fields only)
        self._obligations = {} # obligation_id -> record

    # ---------------- writes ----------------

    def open_case(self, case_id, category, subject_ref, facts_json):
        _require(isinstance(case_id, str) and case_id != "", "case_id required")
        _require(case_id not in self._cases, "duplicate case_id")
        _require(category in CATEGORIES, f"unknown category: {category!r}")
        _require(isinstance(subject_ref, str) and subject_ref != "",
                 "subject_ref required")
        try:
            facts = json.loads(facts_json)
        except Exception:
            raise ValueError("facts_json malformed")
        _require(isinstance(facts, dict), "facts_json must be a JSON object")
        _require(len(facts_json.encode("utf-8")) <= MAX_FACTS_BYTES,
                 "facts exceed 4096 bytes")

        rec = {
            "case_id": case_id,
            "category": category,
            "subject_ref": subject_ref,
            "facts": facts,
            "status": "OPEN",
            "classification_id": "",
            "obligation_ids": [],
            "resolution_evidence_hash": "",
        }
        self._cases[case_id] = rec
        return _canonical(rec)

    def classify_case(self, case_id, classification_id, obligations_json):
        case = self._cases.get(case_id)
        _require(case is not None, "unknown case_id")
        _require(case["status"] == "OPEN", "doubleClassification rejected")
        _require(isinstance(classification_id, str) and classification_id != "",
                 "classification_id required")
        try:
            obligations = json.loads(obligations_json)
        except Exception:
            raise ValueError("obligations_json malformed")
        _require(isinstance(obligations, list), "obligations must be a list")
        _require(1 <= len(obligations) <= MAX_OBLIGATIONS_PER_CASE,
                 "obligation count out of bounds 1..8")

        ids = []
        for i, ob in enumerate(obligations):
            _require(isinstance(ob, dict), "each obligation must be an object")
            ob_type = ob.get("type")
            _require(ob_type in OBLIGATION_TYPES,
                     f"unknown obligation type: {ob_type!r}")
            bound = ob.get("bound", {})
            _require(isinstance(bound, dict), "bound must be an object")
            oid = f"{classification_id}-O{i}"
            _require(oid not in self._obligations, "duplicate obligation id")
            self._obligations[oid] = {
                "obligation_id": oid,
                "case_id": case_id,
                "type": ob_type,
                "bound": bound,
                "status": "PRESCRIBED",
                "evidence_hash": "",
                "waiver_note": "",
            }
            ids.append(oid)

        # Append-only annotation of the case - prior fields never rewritten.
        case["classification_id"] = classification_id
        case["obligation_ids"] = ids
        case["status"] = "CLASSIFIED"
        return _canonical({
            "case_id": case_id,
            "classification_id": classification_id,
            "obligation_ids": ids,
            "status": "CLASSIFIED",
        })

    def discharge_obligation(self, obligation_id, evidence_hash):
        ob = self._obligations.get(obligation_id)
        _require(ob is not None, "unknown obligation_id")
        _require(ob["status"] == "PRESCRIBED", "doubleDisposition rejected")
        _require(isinstance(evidence_hash, str) and evidence_hash != "",
                 "dischargeWithoutEvidence rejected")
        ob["evidence_hash"] = evidence_hash
        ob["status"] = "DISCHARGED"
        return _canonical(ob)

    def waive_obligation(self, obligation_id, waiver_note):
        ob = self._obligations.get(obligation_id)
        _require(ob is not None, "unknown obligation_id")
        _require(ob["status"] == "PRESCRIBED", "doubleDisposition rejected")
        _require(isinstance(waiver_note, str) and waiver_note != "",
                 "waiveWithoutNote rejected")
        ob["waiver_note"] = waiver_note
        ob["status"] = "WAIVED"
        return _canonical(ob)

    def resolve_case(self, case_id, resolution_evidence_hash):
        case = self._cases.get(case_id)
        _require(case is not None, "unknown case_id")
        _require(case["status"] == "CLASSIFIED",
                 "resolve requires CLASSIFIED; RESOLVED is terminal")
        _require(isinstance(resolution_evidence_hash, str)
                 and resolution_evidence_hash != "",
                 "resolution_evidence_hash required")
        for oid in case["obligation_ids"]:
            _require(self._obligations[oid]["status"] in ("DISCHARGED", "WAIVED"),
                     f"undispositioned obligation remains: {oid}")
        case["status"] = "RESOLVED"
        case["resolution_evidence_hash"] = resolution_evidence_hash
        return _canonical(case)

    # ---------------- views ----------------

    def get_case(self, case_id):
        rec = self._cases.get(case_id)
        return _canonical(rec) if rec else ""

    def get_obligation(self, obligation_id):
        rec = self._obligations.get(obligation_id)
        return _canonical(rec) if rec else ""


# ---------------- canonical vector runner ----------------

def run_vectors(vector_path):
    """Run canonical v0.1 vectors. Expected dicts match as subsets; strings
    compare exactly; 'ok'/'reject' gate exceptions."""
    with open(vector_path) as fh:
        suite = json.load(fh)
    results = []
    for vec in suite["vectors"]:
        gaia = Gaia()
        failures = []
        for i, action in enumerate(vec["actions"]):
            op, args, expect = action["op"], action["args"], action["expect"]
            try:
                out = getattr(gaia, op)(*args)
                err = None
            except Exception as exc:  # noqa: BLE001 - rejection is data here
                out, err = None, exc
            if expect == "reject":
                if err is None:
                    failures.append(f"[{i}] {op} expected reject, got ok: {out}")
            elif expect == "ok":
                if err is not None:
                    failures.append(f"[{i}] {op} expected ok, got {err}")
            elif isinstance(expect, str):
                got = "" if err is not None else out
                if got != expect:
                    failures.append(f"[{i}] {op}: expected {expect!r}, got {got!r}")
            elif isinstance(expect, dict):
                if err is not None:
                    failures.append(f"[{i}] {op} raised {err}")
                else:
                    actual = json.loads(out)
                    for k, v in expect.items():
                        if actual.get(k) != v:
                            failures.append(
                                f"[{i}] {op}: field {k}: expected {v!r}, "
                                f"got {actual.get(k)!r}")
        results.append({"id": vec["id"], "pass": not failures,
                        "failures": failures})
    return suite["primitive"], results


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "vectors/v0.1.json"
    prim, res = run_vectors(path)
    ok = True
    for r in res:
        print(f"{'PASS' if r['pass'] else 'FAIL'}  {prim}/{r['id']}")
        for f in r["failures"]:
            print("   ", f)
    sys.exit(0 if ok else 1)
