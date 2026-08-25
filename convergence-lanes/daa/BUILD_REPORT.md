# DAA Build Report - Independent Reimplementation (fresh-context lane)

Build: `your_build.py` - canonical vector runner result: **11/11 PASS** against
`primitives/daa/vectors/v0.1.json`.

## Independence confirmation

Only the following artifacts were read: `primitives/daa/SPEC.md`, `INVARIANTS.md`,
`THREAT_MODEL.md`, `DECISION_BOUNDARY.md`, `CAPABILITY.json`, `vectors/v0.1.json`.
`implementations/genlayer/` was **not** opened, listed, or referenced. The build was
written from spec + capability contract alone; the only iteration after the first run
was a mechanical fix in the embedded runner's dispatch (views must not receive the
simulated sender), not a semantic change.

## State layout

- `_requests`: request_id → record (`request_id, resource, asset, beneficiary,
  purpose, requested_bound, policy_hash, valid_after, valid_until,
  authority_source, status`). Status ∈ REQUESTED / EVALUATING / AWARDED /
  REJECTED / UNDETERMINED.
- `_awards`: allocation_id → immutable award record once finalized
  (`status` ∈ AWARDED / REVOKED; EXPIRED is *implicit by window*, computed in
  `effective_status`, never written).
- `_request_award`: request_id → allocation_id (enforces one award per request).
- `_evaluations`: append-only ledger of burned evaluation ids
  (`EVAL-<seq>`, request_id, eligibility ELIGIBLE|INELIGIBLE, burned=True) with a
  monotonic counter - INELIGIBLE attempts consume an id exactly like eligible ones.

## Key semantics implemented

- Authority source = requester at `request_allocation`; only it may award /
  reject / undetermine / revoke / evaluate.
- Award ≠ usage: `award` creates capacity only; downstream execution proves
  containment via `verify_authority`, a fail-closed view mutating nothing.
- Bound escalation structurally impossible: `max_authority > requested_bound`
  raises before any state change.
- Validity windows are frozen at request time and copied into the award;
  no transition touches them, so expiry never resets on activity.
- EXPIRED is derived from the window (`at < valid_after` or `at >= valid_until`),
  matching vector 008 where the award itself is granted exactly at `valid_until`.
- REJECTED / UNDETERMINED finalize requests into zero-authority states; awarding
  them raises.

## Ambiguities resolved

1. **Can `award` follow directly from REQUESTED?** The CAPABILITY state machine
   shows `REQUESTED -> AWARDED` while SPEC §5 routes through EVALUATING; the
   canonical vectors award straight from REQUESTED. Resolved: EVALUATING is
   optional; both REQUESTED and EVALUATING are awardable.
2. **Where does expiry check sit relative to revocation?** Vector 009 checks a
   revoked award inside its window; ordering revoked-before-expired is safe either
   way here since windows were still open, but I check REVOKED first so a revoked
   award never reports EXPIRED.
3. **Award timestamp vs window**: I reject awards placed outside
   `[valid_after, valid_until]` (vector 008 awards exactly at `valid_until`, which
   passes as inclusive).
4. **Vector expectations are partial**: `get_request`/`get_award` expects omit
   fields (e.g. `valid_after`) present in my richer records. Runner does subset
   matching for dict expectations; canonical output is sorted-key compact JSON.
5. **INELIGIBLE evaluation burn** is described in the lane brief and implied by the
   audit trail requirement but not exercised by v0.1 vectors; implemented as
   `begin_evaluation` + `record_evaluation` with mandatory id burn, unexercised by
   the canonical runner (covered only by direct use).

## Gaps / NOT_IMPLEMENTED in this slice

- No GenVM deployment artifacts/tests directory (lane scope is single-file build +
  vector runner); sender gating beyond the simulated `sender` argument is not
  cryptographically enforced here.
- Evaluation ledger surface (`list_evaluations`) is extra to the public method list;
  it exists to make evaluation-id burning auditable.
- `conditionsHash`/`claimId`/`evidenceHash` bindings from SPEC §4 are not carried
  because CAPABILITY 0.1.0 inputs do not include them.

## Reproduce

```bash
python3 convergence-lanes/daa/your_build.py primitives/daa/vectors/v0.1.json
```
