# BUILD_REPORT - adjudicated-receipt (convergence lane)

## Result
- **PASS** - all 5 canonical v0.2 vectors pass (deterministic-envelope slice), exit code 0.
- Build: `convergence-lanes/adjudicated-receipt/your_build.py` (independent reimplementation from authority artifacts only; no reference implementation read).
- Convergence mode: SEMANTIC (judgment-bearing primitive; this lane covers only the deterministic envelope, which is itself deterministic).

## Inputs read
Exactly these files, nothing else:
1. `primitives/adjudicated-receipt/SPEC.md` (full file; middle section re-read at lines 54-100 after a truncated first read)
2. `primitives/adjudicated-receipt/INVARIANTS.md`
3. `primitives/adjudicated-receipt/THREAT_MODEL.md`
4. `primitives/adjudicated-receipt/DECISION_BOUNDARY.md`
5. `primitives/adjudicated-receipt/CAPABILITY.json`
6. `primitives/adjudicated-receipt/vectors/v0.2.json`
7. `convergence-lanes/daa/your_build.py` (permitted structural reference: lane file + embedded vector runner)
8. `convergence-lanes/financial-contract/your_build.py` lines 1-120 (permitted structural reference)
9. `convergence-lanes/financial-contract/BUILD_REPORT.md` (report structure reference)
10. `tools/nomos_run_vectors.py` (permitted: canonical runner dispatch semantics)

NOT read (independence preserved): `primitives/adjudicated-receipt/implementations/**`, `contracts/adjudicated_receipt.py`, and any other file under `primitives/adjudicated-receipt/`.

## Semantics implemented
- `initialize(owner)`: one-shot init; re-initialization rejects (`ALREADY_INITIALIZED`); empty owner rejects.
- `register_release(invoice_id, object_ref, surrender_value, surrender_asset, evidence_pointer, adjudication_clause, valid_for_seconds, challenge_window, policy_version, expected_source_id)`: rejects duplicate object ids; invoice/receipt ids must be 1..64 chars; `object_ref`, `surrender_asset`, `adjudication_clause`, `policy_version`, `expected_source_id` must be non-empty; `surrender_value`/`valid_for_seconds`/`challenge_window` must be positive uint-strings (`"0"` rejects); `evidence_pointer` is https-only (`http://` rejects). Binds all ten registered terms immutably and derives an `obligation_hash` at registration. Returns `release_registered`; object starts `OPEN`.
- `cancel_release(invoice_id)`: only an `OPEN` object can be cancelled; `CANCELLED` (and `SETTLED`) are terminal - re-cancellation rejects (`OBJECT_NOT_OPEN`); unknown id rejects.
- `adjudicate_object(invoice_id, receipt_id)`: deterministic preconditions enforced (initialized, object exists, status `OPEN`, fresh 1..64 receipt id, not already recorded); a `CANCELLED` object deterministically rejects (`OBJECT_NOT_OPEN`, vector ar-cancel-001). If preconditions pass, fails closed with `JudgmentSurfaceNotInLaneScope` - quorum verdict production is judgment surface, never in this lane.
- `challenge_release` / `finalize_release` / `settle_release`: unknown receipt ids fail closed (`UNKNOWN_RECEIPT_ID`, vector ar-lifecycle-guards-rejected-004); for known receipts, deterministic preconditions (bond validity, provisional-only finalization, FINAL_ACCEPTED-only settlement, one-way `consumed` bit, obligation-hash binding to current object terms, object still `OPEN`, owner-held authority) are evaluated, then the operation fails closed with `JudgmentSurfaceNotInLaneScope` because the receipt can only originate from the quorum path.
- Views `get_object` / `get_receipt` / `get_release` / `get_challenge`: unknown ids reject; known ids return canonical JSON (sorted keys, compact separators).
- Canonical JSON everywhere: `sort_keys=True, separators=(",", ":")`. Fresh contract instance per vector. Embedded runner mirrors `tools/nomos_run_vectors.py` dispatch: `"ok"` = no exception, `"reject"` = any exception, dict = subset key match with string coercion.
- Fail-closed everywhere: every rejection path raises before any state mutation; no exception path mutates economic state.

## Ambiguities resolved
- **Obligation-hash formula is lane-internal** (vectors assert a hash IS derived and bound, not its value). SPEC.md section 14 offers "ordered concatenation of registered terms (upgrade path: content hash of canonical JSON)"; this lane takes the upgrade path: sha256 hex over canonical JSON of the ten terms in registration order.
- **No clock in the lane**: `registered_at` is recorded as a logical registration sequence number; TTL-freshness enforcement (time-bound, deterministic) is covered by direct/GLSim tests, not vectors, so it is out of lane scope.
- **msg.sender not expressible** in the lane arg surface (vectors pass only documented args): owner-gating in the settlement gate uses a caller attribute that defaults to the owner; non-owner settlement attempts are direct-test/GLSim scope.
- **Vector expect semantics** taken from `tools/nomos_run_vectors.py`: dict expects are subset matches (extra record fields such as `registered_at`, `obligation_hash` are permitted), and `"ok"` means the call must not raise.
- **Status vocabulary** taken from CAPABILITY 0.2.0 (`OPEN|CANCELLED|SETTLED` objects; receipt statuses incl. `PROVISIONAL_ACCEPTED`/`FINAL_ACCEPTED`); SPEC.md is stamped 0.1.0 and lacks `CANCELLED`/`challenge_window`/`policy_version`/`expected_source_id`, so CAPABILITY 0.2.0 + v0.2 vectors were treated as authoritative where they diverge.
- **Cancellation terminality**: SPEC 0.1 models only `OPEN -> SETTLED`; v0.2 adds `CANCELLED` as terminal (vector ar-cancel-001 pins re-cancel and post-cancel adjudication as rejects). Implemented as an explicit terminal rule.

## Gaps / NOT_IMPLEMENTED
- **Quorum verdict paths are out of lane scope** (per task scope note and SPEC section 13): `adjudicate_object` on an OPEN object, and `challenge_release`/`finalize_release`/`settle_release` on known receipts, deterministically reject with a labelled `JudgmentSurfaceNotInLaneScope` error instead of producing ACCEPTED/REJECTED/UNDETERMINED/CHALLENGED/FINAL_ACCEPTED/EXPIRED records. These are judgment-surface behavior tested by mocked-web direct tests and GLSim integration, not by the v0.2 vectors.
- This lane **cannot mint receipts**, so the known-receipt branches of the settlement gate (exactly-once consumption, binding mismatch, non-owner rejection) are implemented but unreachable in-lane; they are exercised only where quorum receipts exist.
- **No GenVM/GenLayer execution**: pure Python; no genvm-lint, direct, or integration tests run here. SEMANTIC convergence: this lane matches the bounded decision relation on the deterministic envelope; model prose/reason strings (non-canonical per CAPABILITY) may differ across implementations.
- Per CAPABILITY `unsupported`: token transfer/custody, cross-contract consumption, per-object settler bindings, partial-release tiers, content-hash evidence binding, bond escrow/slashing, arbitration escalation - none implemented (settlement records a release obligation only).

## Verification
```
$ cd /home/ubuntu/nomos && python3 convergence-lanes/adjudicated-receipt/your_build.py primitives/adjudicated-receipt/vectors/v0.2.json
PASS - ar-register-001: PASS
PASS - ar-register-duplicate-rejected-002: PASS
PASS - ar-register-invalid-rejected-003: PASS
PASS - ar-cancel-001: PASS
PASS - ar-lifecycle-guards-rejected-004: PASS

5/5 vectors PASS
exit=0
```
Adversarial spot-checks (beyond vectors, all fail closed): uninitialized calls reject `NOT_INITIALIZED`; double init rejects `ALREADY_INITIALIZED`; ids >64 chars reject; values `"0"`, `"-1"`, `"abc"`, `""`, `"1.5"` reject; empty asset/expected_source_id reject; adjudicate on OPEN object raises the labelled `JudgmentSurfaceNotInLaneScope`; unknown ids reject on `cancel_release`/`get_challenge`/`get_release`.
Determinism: no clock, randomness, or network inside methods; integer-only arithmetic; canonical JSON output; fresh instance per vector.
