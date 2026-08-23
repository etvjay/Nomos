# BUILD_REPORT — dal (independent build)

Builder: independent convergence-lane agent (no access to
`implementations/genlayer/`; built solely from SPEC.md, INVARIANTS.md,
THREAT_MODEL.md, DECISION_BOUNDARY.md, CAPABILITY.json, vectors/v0.1.json).

## Result

`PASS` — all 10 canonical vectors (v0.1.json) pass.

```
python3 your_build.py /home/ubuntu/nomos/primitives/dal/vectors/v0.1.json
# 10/10 PASS, exit 0
```

## Implementation

State: one replay domain per `(issuer, domain_id)`; lane carries
`expiry_window`, expected `nonce` (starts at "1"), status
ACTIVE/REVOKED/EXPIRED(implicit).

- `open_lane`: rejects duplicates — including revoked lanes, which can
  never be reopened (dal-reopen-after-revoke-rejected-010).
- `exercise`, ordered fail-closed validation:
  1. LANE_REVOKED (explicit revocation dominates expiry),
  2. LANE_EXPIRED (`at_timestamp > expiry_window`),
  3. nonce == 0 or > expected → NONCE_INVALID,
  4. nonce < expected → NONCE_REUSED,
  5. else AUTHORIZE/NONCE_VALID with exactly one atomic advance of the
     expected nonce.
- All denials mutate nothing (nonce unchanged), verified by
  dal-stale-nonce-rejected-004 and dal-future-or-zero-nonce-rejected-005.
- Domain independence: exercising DOMAIN-A does not disturb DOMAIN-B
  under the same issuer (dal-domain-independence-006). No balances,
  capacity, or shared economic state are exposed (dal-shared-dependency-
  not-implied-007); DAL owns only per-(issuer,domain) replay state.
- Unknown lane views return `""` (json-or-empty); exercising an unknown
  lane rejects at op level.

## Judgment boundary

NONE (per DECISION_BOUNDARY.md). Nonce validity, sequence advancement,
replay detection, and lane identity are fully deterministic; no
validator/LLM surface exists anywhere in the build.

## Ambiguities resolved

- `expiry_window` semantics: no open-time parameter exists on
  `open_lane`, so I read it as an absolute deadline compared directly
  to `at_timestamp` (window "50", exercise at 51 → LANE_EXPIRED, per
  dal-expired-lane-denies-009).
- NONCE_INVALID vs NONCE_REUSED precedence: CAPABILITY lists zero/ahead
  as INVALID and below-expected as REUSED; nonce 0 satisfies both, so I
  check INVALID first (matches dal-future-or-zero-nonce-rejected-005).
