"""Mandate Allocation - independent build (convergence lane, capability v0.1.0).

Convergence mode: EXACT (judgmentBearing: false - JUDGMENT_BOUNDARY = NONE)

Deterministic advisory evaluation of opportunities against a registered
mandate. Results are recommendations only: no authority, no commitment, no
encumbrance, no value movement. Evaluation ids are unique INCLUDING
INELIGIBLE attempts (attempts burn their id - auditable) but INELIGIBLE
attempts consume no exposure capacity. Assets bind via upstream composition:
the mandate's `asset` field is supplied by upstream composition and every
evaluation is bound to it through mandate_id.

GenLayer conventions: single contract class holding state, write methods
return canonical JSON strings (sorted keys, compact separators), view methods
return canonical JSON strings or "" for absent records. Rejections raise.
"""

import json


JUDGMENT_BOUNDARY = "NONE"
PRIMITIVE_ID = "mandate-allocation"
CAPABILITY_VERSION = "0.1.0"

ELIGIBILITY_VALUES = ("ELIGIBLE", "INELIGIBLE")
REASON_CODES = ("WITHIN_MANDATE", "CLASS_NOT_PERMITTED", "EXPOSURE_EXCEEDED")


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _uint(text, field):
    if not isinstance(text, str):
        raise ValueError(f"{field} must be uint-string")
    stripped = text.lstrip("0") or "0"
    if not stripped.isdigit():
        raise ValueError(f"invalid {field}: {text!r}")
    return int(stripped)


def _require(cond, msg) -> None:
    if not cond:
        raise ValueError(msg)


def _get(d, key):
    rec = d.get(key)
    _require(rec is not None, "unknown record")
    return rec


class MandateAllocation:
    """Advisory mandate evaluation registry. Owns mandate constraint objects
    and evaluation records/lineage only."""

    def __init__(self):
        self._mandates = {}      # mandate_id -> record
        self._evaluations = {}   # evaluation_id -> record

    # ---------------- writes ----------------

    def register_mandate(self, mandate_id, doc_hash, max_total_exposure,
                         asset, allowed_classes_json):
        _require(isinstance(mandate_id, str) and mandate_id != "",
                 "mandate_id required")
        _require(mandate_id not in self._mandates,
                 "duplicate mandate_id")
        _require(isinstance(doc_hash, str) and doc_hash != "",
                 "doc_hash required")
        exposure = _uint(max_total_exposure, "max_total_exposure")
        _require(exposure > 0, "max_total_exposure must be positive")
        _require(isinstance(asset, str) and asset != "", "asset required")
        try:
            classes = json.loads(allowed_classes_json)
        except Exception:
            raise ValueError("allowed_classes_json malformed")
        _require(isinstance(classes, list)
                 and all(isinstance(c, str) for c in classes),
                 "allowed_classes must be a list of strings")

        rec = {
            "mandate_id": mandate_id,
            "doc_hash": doc_hash,
            "max_total_exposure": str(exposure),
            "asset": asset,
            "allowed_classes": sorted(classes),
        }
        self._mandates[mandate_id] = rec
        return _canonical(rec)

    def evaluate_opportunity(self, evaluation_id, mandate_id, opportunity_ref,
                             opportunity_class, requested_amount,
                             at_timestamp):
        _require(isinstance(evaluation_id, str) and evaluation_id != "",
                 "evaluation_id required")
        # Ids burn on every attempt, ELIGIBLE or INELIGIBLE - auditable.
        _require(evaluation_id not in self._evaluations,
                 "duplicate evaluation_id")
        _require(at_timestamp is not None, "at_timestamp required")
        mandate = self._mandates.get(mandate_id)
        _require(mandate is not None, "unknown mandate_id")
        _require(isinstance(opportunity_ref, str) and opportunity_ref != "",
                 "opportunity_ref required")
        amount = _uint(requested_amount, "requested_amount")

        committed = self.committed_exposure_int(mandate_id)
        if opportunity_class not in mandate["allowed_classes"]:
            eligibility, reason = "INELIGIBLE", "CLASS_NOT_PERMITTED"
        elif committed + amount > int(mandate["max_total_exposure"]):
            eligibility, reason = "INELIGIBLE", "EXPOSURE_EXCEEDED"
        else:
            eligibility, reason = "ELIGIBLE", "WITHIN_MANDATE"

        rec = {
            "evaluation_id": evaluation_id,
            "mandate_id": mandate_id,
            "mandate_hash": mandate["doc_hash"],
            "asset": mandate["asset"],          # bound via upstream composition
            "opportunity_ref": opportunity_ref,
            "opportunity_class": opportunity_class,
            "requested_amount": str(amount),
            "eligibility": eligibility,
            "reason_code": reason,
            "recommended_amount": str(amount if eligibility == "ELIGIBLE" else 0),
            "status": "EVALUATED",
            "supersedes": "",
            "at_timestamp": str(int(str(at_timestamp))),
        }
        self._evaluations[evaluation_id] = rec
        return _canonical(rec)

    def supersede_evaluation(self, old_evaluation_id, new_evaluation_id,
                             note_json):
        _require(old_evaluation_id != new_evaluation_id, "self-supersede rejected")
        old = self._evaluations.get(old_evaluation_id)
        _require(old is not None, "unknown old_evaluation_id")
        _require(new_evaluation_id not in self._evaluations,
                 "duplicate new_evaluation_id")
        try:
            note = json.loads(note_json)
        except Exception:
            raise ValueError("note_json malformed")
        _require(isinstance(note, dict), "note_json must be a JSON object")
        _require(old["status"] == "EVALUATED",
                 "only EVALUATED records can be superseded")

        # Old record is preserved (history), marked SUPERSEDED; its advisory
        # exposure capacity moves to the successor unchanged.
        old["status"] = "SUPERSEDED"
        rec = dict(old)
        rec["evaluation_id"] = new_evaluation_id
        rec["status"] = "EVALUATED"
        rec["supersedes"] = old_evaluation_id
        rec["supersede_note"] = note
        self._evaluations[new_evaluation_id] = rec

        lineage = {
            "old_evaluation_id": old_evaluation_id,
            "new_evaluation_id": new_evaluation_id,
            "supersedes": old_evaluation_id,
            "status": "EVALUATED",
            "note": note,
        }
        return _canonical(lineage)

    # ---------------- views ----------------

    def get_mandate(self, mandate_id):
        rec = self._mandates.get(mandate_id)
        return _canonical(rec) if rec else ""

    def get_evaluation(self, evaluation_id):
        rec = self._evaluations.get(evaluation_id)
        return _canonical(rec) if rec else ""

    def committed_exposure_int(self, mandate_id):
        return sum(
            int(r["recommended_amount"])
            for r in self._evaluations.values()
            if r["mandate_id"] == mandate_id
            and r["eligibility"] == "ELIGIBLE"
            and r["status"] == "EVALUATED"
        )

    def committed_exposure(self, mandate_id):
        if mandate_id not in self._mandates:
            return ""
        return str(self.committed_exposure_int(mandate_id))


# ---------------- canonical vector runner ----------------

def run_vectors(vector_path):
    """Run canonical v0.1 vectors. Expected dicts match as subsets; strings
    compare exactly; 'ok'/'reject' gate exceptions."""
    with open(vector_path) as fh:
        suite = json.load(fh)
    results = []
    for vec in suite["vectors"]:
        contract = MandateAllocation()
        failures = []
        for i, action in enumerate(vec["actions"]):
            op, args, expect = action["op"], action["args"], action["expect"]
            try:
                out = getattr(contract, op)(*args)
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
        ok = ok and r["pass"]
    sys.exit(0 if ok else 1)
