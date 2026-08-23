# BUILD_REPORT — gaia (convergence lane)

## Result
- **PASS** — all 9 canonical v0.1 vectors pass in EXACT mode.
- Build: `your_build.py` (independent reimplementation from spec artifacts only).

## Inputs read
Only: `primitives/gaia/CAPABILITY.json` and `vectors/v0.1.json`. Implementations dir NOT read.

## Semantics implemented
- Case state machine OPEN → CLASSIFIED → RESOLVED (RESOLVED terminal: reclassification and re-resolution rejected).
- `open_case`: duplicate ids, unknown category, empty case_id/subject_ref, malformed facts JSON rejected; facts ≤ 4096 bytes.
- `classify_case`: exactly one per case; classification_id unique; obligations list of {type, bound} with 1..8 entries; type ∈ declared set; obligation ids derived `<classification_id>-O<i>`; case annotated to CLASSIFIED.
- Obligation lifecycle PRESCRIBED → DISCHARGED | WAIVED; discharge requires non-empty evidence_hash, waive requires non-empty waiver_note; double disposition rejected.
- `resolve_case`: requires ALL obligations dispositioned (discharged or waived) plus a resolution evidence hash; sets RESOLVED + resolution_evidence_hash.
- History append-only: prior fields never rewritten — only status/evidence/note annotations added. Remedies are prescribed compensating entries ONLY; Gaia holds no execution authority (no capital views exist; unknown lookups return "").

## Verification
```
python3 your_build.py ../../primitives/gaia/vectors/v0.1.json
# PASS x9 (ga-*-001..009)
```
Determinism: pure dict-state transitions, canonical JSON output (sort_keys, compact), obligation ids derived deterministically from classification_id + index. JUDGMENT_BOUNDARY = NONE.
