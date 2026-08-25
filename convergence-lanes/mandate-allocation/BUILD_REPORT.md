# BUILD_REPORT - mandate-allocation (convergence lane)

## Result
- **PASS** - all 9 canonical v0.1 vectors pass in EXACT mode.
- Build: `your_build.py` (independent reimplementation from spec artifacts only).

## Inputs read
Only: `primitives/mandate-allocation/{SPEC.md, CAPABILITY.json, DECISION_BOUNDARY.md}` and `vectors/v0.1.json`.
(INVARIANTS.md/THREAT_MODEL.md present but not required to disambiguate semantics; implementations/ dir NOT read.)

## Semantics implemented
- `register_mandate`: binds doc_hash + deterministic hard constraints (max_total_exposure uint-string, asset bound via upstream composition, allowed_classes list). Rejects duplicate ids, empty id/doc_hash/asset, zero/non-numeric exposure.
- `evaluate_opportunity`: deterministic eligibility - CLASS_NOT_PERMITTED / EXPOSURE_EXCEEDED / WITHIN_MANDATE. **Evaluation ids burn on INELIGIBLE attempts too** (duplicate-id rejection applies to all attempts - auditable); ineligible attempts consume no exposure. ELIGIBLE consumes advisory exposure capacity only (no authority).
- `supersede_evaluation`: old record preserved and marked SUPERSEDED; successor record created with `supersedes` lineage link and the old record's exposure contribution moves with it (net-zero). Self-supersede rejected.
- Views return canonical JSON or "" for unknown ids.

## Interpretation choices (ambiguities resolved)
1. Superseding an evaluation creates the successor record at supersede time (vector ma-supersede-008 expects `get_evaluation(RES2)` to exist without a prior evaluate call); exposure transfers rather than double-counts.
2. Empty allowed_classes permitted on a mandate (only empty mandate_id/doc_hash are rejected by vectors); such a mandate simply yields CLASS_NOT_PERMITTED for everything.
3. `committed_exposure` counts recommended_amount of ELIGIBLE, still-EVALUATED records only.

## Verification
```
python3 your_build.py ../../primitives/mandate-allocation/vectors/v0.1.json
# PASS x9 (all vector ids ma-*-001..009)
```
Determinism: pure functions over dict state; canonical JSON output (`sort_keys`, compact separators); no wall-clock or randomness. JUDGMENT_BOUNDARY = NONE.
