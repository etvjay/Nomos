# BUILD_REPORT — workflow-authorization (fresh-context convergence lane)

Build: `your_build.py` — independent reimplementation of Nomos primitive
`workflow-authorization` v0.1.0, EXACT mode, JUDGMENT_BOUNDARY = NONE.

## Independence confirmation

Read ONLY: `SPEC.md`, `INVARIANTS.md`, `THREAT_MODEL.md`, `DECISION_BOUNDARY.md`,
`CAPABILITY.json`, `vectors/v0.1.json`. The directory listing surfaced
`implementations/genlayer/*` filenames; none of those files (including the
implementation README and tests) were opened. No reference implementation
code influenced this build.

## Vector results

`python3 your_build.py ../../primitives/workflow-authorization/vectors/v0.1.json`
→ 10/10 PASS: wa-grant-path-001, wa-path-duplicate-rejected-002,
wa-path-invalid-inputs-003, wa-propose-pact-004,
wa-pact-unknown-path-rejected-005, wa-pact-duplicate-and-invalid-006,
wa-blocked-cannot-execute-007, wa-revoked-path-authorizes-nothing-008,
wa-expired-path-010, wa-no-capital-effects-013.

## State layout

Two flat maps owned by the contract; nothing else:

- `paths[path_id] = {path_id, principal, agent, purpose_scope, max_per_action,
  asset, valid_after, valid_until, status}` — status ACTIVE/REVOKED explicit;
  EXPIRED is implicit by window (`_path_status(path, now)`), never stored.
- `pacts[pact_id] = {pact_id, path_id, workflow_ref, terms (parsed object),
  proposed_at, status, [accepted_at], [executed_at], [executed_amount]}` —
  PROPOSED → ACCEPTED → EXECUTED; PROPOSED/ACCEPTED → VOID; terminal states
  immutable.

Not owned (per CAPABILITY.json): capital allocation/reservation, replay
nonces, settlement, policy interpretation, claim encumbrance.

## Decision gate ordering (execute_pact)

Fail-closed structured DENY, no exceptions for expected denials:

1. unknown pact or status != ACCEPTED → DENY / PACT_NOT_ACCEPTED
2. path revoked (or missing) → DENY / PATH_NOT_ACTIVE
3. at_timestamp outside validity window → DENY / PATH_EXPIRED
4. amount > max_per_action → DENY / EXCEEDS_PATH_BOUND
5. else AUTHORIZE / WITHIN_DELEGATED_AUTHORITY (mutates pact → EXECUTED)

Ordering note: acceptance is checked before path state because vector 008
executes a never-accepted pact on a revoked path and expects
PACT_NOT_ACCEPTED.

## Rejections vs denials

- Expected DENY decisions are structured `{decision, reason_code}` results.
- Invalid operations (duplicates, self-delegation, empty fields, zero bound,
  inverted window, malformed/oversized terms, non-principal accept, void of
  terminal pact, executed-pact reuse) raise a typed `Rejected` exception,
  which the runner maps to "reject". Only unexpected failures surface as raw
  exceptions.

## Sender neutrality

All write methods take an explicit `sender`; all timestamps come from caller
arguments (no wall clock). The only sender-sensitive operation is Pact
acceptance (principal-only, compared case/`0x`-prefix insensitively), which
the vector file explicitly excludes from vector coverage (single fixed
runner sender); implemented per CAPABILITY.json rules but not
vector-exercised.

## Ambiguities encountered

1. **Window inclusivity**: spec gives no explicit closed/open semantics.
   Chose inclusive `[valid_after, valid_until]`; consistent with all vectors
   (proposal at t=60 against valid_until=50 rejected).
2. **Unknown pact in execute_pact**: reason-code list has no NOT_FOUND code.
   Mapped to PACT_NOT_ACCEPTED (fail-closed, same observable class).
3. **Void authority**: CAPABILITY.json declares no authority restriction for
   void_pact; left unrestricted for any party, restricted only by terminal
   immutability.
4. **Revoke idempotency**: revoking an already-revoked path is unspecified;
   made idempotent (returns REVOKED canonical form rather than rejecting).
5. **Canonical output fields**: CAPABILITY.json says "canonical-*-json-string"
   without exact field lists. Emitted full objects including timestamps as
   strings (uint/int-string convention); vector expects are subset-matched,
   so extra deterministic fields are compatible.
6. **grant_path timestamp args**: validity bounds accepted as int-strings and
   normalized to ints internally, re-emitted as strings.

## Gaps / not implemented

- GenVM deployment artifacts, direct tests for principal-only acceptance
  (vector file notes these live in the reference lane's direct tests),
  pytest suite, and multi-sig/quorum acceptance (explicitly unsupported in
  v0.1) are out of scope for this lane build.
- Policy-envelope `interpret_clause` composition is externalized per spec;
  not stubbed here.
