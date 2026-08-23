# BUILD_REPORT — policy-envelope (independent build)

Builder: independent convergence-lane agent (no access to
`implementations/genlayer/`; built solely from SPEC.md, INVARIANTS.md,
THREAT_MODEL.md, DECISION_BOUNDARY.md, CAPABILITY.json, vectors/v0.1.json).

## Result

`PASS` — all 12 canonical vectors (v0.1.json) pass.

```
python3 your_build.py /home/ubuntu/nomos/primitives/policy-envelope/vectors/v0.1.json
# 12/12 PASS, exit 0
```

## Deterministic gate surface

- `create_envelope`: rejects empty id/hash, non-positive or non-numeric
  amount, inverted window (`valid_after >= valid_until`), duplicate ids.
  Registered ACTIVE.
- `evaluate_request`, fixed fail-closed order:
  ENVELOPE_INACTIVE → OUTSIDE_VALIDITY_WINDOW → ASSET_MISMATCH →
  AMOUNT_EXCEEDS_LIMIT → CAPACITY_EXHAUSTED → ADMIT(WITHIN_HARD_LIMITS).
- Denials are recorded in an append-only audit log; they mutate no
  accounting state, consume no capacity, and do NOT consume the request
  id (vector pe-duplicate-request-id-rejected-010 confirms a denied R2
  can later be admitted). Admitted request ids are consumed and become
  replay-guarded (`admittedRequestIdReuse: rejected`).
- Cumulative usage tracked per envelope; `used_amount` view exposed.
- actor/target bound to decision records but not enforced against
  registries — per CAPABILITY `unsupported` list for v0.1.
- Views return `""` for unknown keys (json-or-empty convention).

## Judgment component interpretation (SEMANTIC notes)

CAPABILITY.json declares `judgmentBearing: false` / convergence EXACT;
SPEC.md records the v0.1 Article XVI narrowing from the v0.1-draft
SEMANTIC classification. My interpretation:

- The declared mandate-clause surface (`attach_mandate_clause`,
  `interpret_clause`, `get_clause_interpretation`) is implemented as a
  strictly subordinate structured surface returning
  ADMIT/DENY/UNDETERMINED with duplicate-id and ≤4096-byte limits.
- In this reference build the interpretation resolves to UNDETERMINED
  unless facts explicitly carry `{"decision": "ADMIT"|"DENY"}`; the
  `analysis` field is treated as explicitly non-canonical prose.
- Interpretations never relax hard limits, never mutate accounting
  state, never create execution authority, and do not veto otherwise-
  admissible deterministic requests (dominanceRule honored).
- Equivalence binds only `{decision, reason_code}` of
  `evaluate_request`; interpretation internals are non-canonical, so
  this build is convergent under the declared EXACT mode regardless of
  how another builder realizes the bounded interpretation prose.

The canonical vectors exercise none of the interpretation surface
beyond the empty-lookup check (pe-no-authority-effects-012), which is
consistent with judgment being subordinate/non-canonical in v0.1.

## Ambiguities resolved

- Empty-view return value: vectors compare against `""`, so unknown
  lookups return the empty string rather than an empty object.
- Denial reason ordering is not pinned by vectors for combined
  violations; I chose status → window → asset → per-tx cap → capacity
  as the most conservative reading of "hard limits evaluated in fixed
  order".
