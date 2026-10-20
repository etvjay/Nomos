# BUILD_REPORT - ppa (convergence lane)

## Result
- **PASS** — all 15 canonical v0.1 vectors pass in EXACT mode (`15/15 vectors passed for ppa`, exit 0).
- Build: `convergence-lanes/ppa/your_build.py` (independent reimplementation from spec artifacts only; pure Python, no genlayer imports, embedded vector runner).

## Inputs read
- `primitives/ppa/SPEC.md`
- `primitives/ppa/INVARIANTS.md`
- `primitives/ppa/THREAT_MODEL.md`
- `primitives/ppa/DECISION_BOUNDARY.md`
- `primitives/ppa/CAPABILITY.json`
- `primitives/ppa/vectors/v0.1.json`
- Structural templates only (no semantics copied): `convergence-lanes/daa/your_build.py`, `tools/nomos_run_vectors.py`, `convergence-lanes/financial-contract/BUILD_REPORT.md` (report structure).
- NOT read: `primitives/ppa/implementations/**`, `contracts/ppa.py`, any other file under `primitives/ppa/`, sibling lanes `convergence-lanes/pop/your_build.py` and `convergence-lanes/policy-envelope/your_build.py`.

## Semantics implemented
- `initialize(owner)`: single initialization; second call rejects (`ALREADY_INITIALIZED`).
- `create_account(account_id, rules_json)`: rejects duplicate ids and unparseable rules; normalizes `per_tx_limit`/`daily_limit` to canonical decimal strings; ledger starts at `balance=0, committed=0`, empty rolling daily window.
- `deposit`: adds uint-string amount to balance; unknown account rejects.
- `send(account_id, payment_id, to, amount, evidence_hash="", memo="")` gate order: **policy gate** (denylist/allowlist deny → `POLICY_DENYLIST`, per-tx → `POLICY_PER_TX_LIMIT`, daily over rolling 86400s window of settled events → `POLICY_DAILY_LIMIT`) → **attestation gate** (only when `rules.require_attestation` truthy; fail-closed) → **encumbrance gate** (`available = balance - committed`, else `INSUFFICIENT_COMMITMENT`) → **settle** (deduct balance, append window event, record immutable `SETTLED` payment, consume id).
- DENY semantics: stores an auditable `DENIED` payment record with canonical reason, moves no funds, adds no daily-window spend, and does **not** consume the payment id (vector 013: retry with the same id settles once valid evidence appears). Any non-DENIED terminal record consumes its id exactly once; replaying a settled id is a structural rejection (`PAYMENT_ID_CONSUMED`, vector 012).
- Attestation gate: empty registry → `ATTESTATION_MISSING` (v002, v006 — a rejected registration leaves the registry empty and the gate stays fail-closed); non-empty registry with no candidate bound to the recipient subject → `ATTESTATION_SUBJECT_MISMATCH` (v007); bound candidates (subject == recipient, regardless of status) evaluated in **ascending attestation_id order**, first fully admissible candidate admits (v014: an expired A1 does not block a valid A2).
- Per-candidate check order: `REVOKED` → `INVALID_STATUS` (defensive; registration already enforces the vocabulary) → `ISSUER_UNAUTHORIZED` (issuer ∉ `rules.attestation_issuers`) → `POLICY_MISMATCH` (`policy_version != rules.attestation_policy_version`) → time window: `now < issued_at` → `ATTESTATION_INVALID` (not-yet-valid); `now >= expires_at` → `ATTESTATION_EXPIRED`; admit iff `issued_at <= now < expires_at` on ISO-8601 timestamp comparison.
- `register_attestation`: attestation_id ≤ 64 chars, no duplicates; fixed schema **exactly** `{subject, issuer, status, issued_at, expires_at, evidence_hash, policy_version}` — unknown fields (v011 PII carrier), missing fields, non-string values, non-ISO timestamps rejected; status ∈ {VALID, REVOKED} (v006 rejects `PENDING`); evidence_hash ≤ 128, policy_version ≤ 64.
- `revoke_attestation`: flips `status` to `REVOKED` (affects future sends only, never rewrites payment history — vector 005 reason `ATTESTATION_REVOKED`); unknown id rejects; double revoke rejects (`ATTESTATION_ALREADY_REVOKED`).
- `get_attestation` / `get_payment` / `get_account`: canonical JSON output (`sort_keys=True, separators=(",",":")`); unknown ids/accounts reject (v015) — absence is an error, never an empty approval.
- Fixed simulated chain time `NOW = 2025-01-01T00:00:00+00:00` makes the 2020-issued/2099-expiring attestation valid (v003) and the 2020-issued/2021-expiring one expired (v004, v014). Fresh `Ppa()` instance per vector.
- Embedded runner mirrors `tools/nomos_run_vectors.py` dispatch: `expect=="ok"` = no exception, `expect=="reject"` = exception, dict expect = subset field match with string coercion, fresh contract instance per vector.

## Key interpretation choices / ambiguities resolved
1. **Attestation denial-reason priority order (inferred).** Vectors 004–009 pin each reason only for *single-candidate* failures, so the intra-candidate order was chosen as: `REVOKED → INVALID_STATUS → ISSUER_UNAUTHORIZED → POLICY_MISMATCH → not-yet-valid (INVALID) → EXPIRED`. Any order would pass the vectors since each failing vector fails exactly one check; this order is documented inline in `_evaluate_candidate`.
2. **Multi-candidate all-fail resolution (not pinned by vectors).** When several candidates all fail, the lane reports the reason of the **last** evaluated failing candidate in ascending-id order (plain loop accumulation). Vector 014 only pins that a later valid candidate admits past an earlier failing one. Direct check confirms A1-expired + A2-revoked → `ATTESTATION_REVOKED`.
3. **Candidacy filter is subject-only.** A revoked/expired attestation still "binds" to the recipient for candidacy purposes (vector 005 expects `ATTESTATION_REVOKED`, which requires the revoked record to remain a candidate rather than degrading to `SUBJECT_MISMATCH`).
4. **Allowlist misses map to `POLICY_DENYLIST`.** The canonical reason vocabulary has no `POLICY_ALLOWLIST` code; rules carrying an `allowlist` deny non-members with the only policy-deny code available. No v0.1 vector exercises allowlist/denylist, so this is best-effort from SPEC wording ("policy gate (allowlist deny, ...)").
5. **DENIED retry model.** A denied record is overwritten by the next attempt with the same id (vector 013 shows only the final SETTLED record via `get_payment`). The denial record is auditable history in-protocol but the v0.1 slice exposes only the latest record per id.
6. **Daily window.** Rolling 86400s window over settled send events (`daily_spent = Σ events with now − ts < 86400`); pruned on settle. With the fixed NOW no window ever rolls inside the vectors; boundary inclusion (`< 86400`) is unpinned.
7. **Rejection vs. denial.** Structural failures (unknown account/payment/attestation, duplicate consumed payment id, schema violations, invalid amounts) raise exceptions (`reject`); gate outcomes return a decision object (`ok` + `status: DENIED`) — pinned by vectors 002/004–009/013–014 where denied sends expect `ok`.
8. **`INSUFFICIENT_COMMITMENT` placement.** Encumbrance runs after attestation; `committed` stays 0 in the v0.1 slice (no claim lifecycle exercised), so the check degenerates to `amount > balance` but preserves the `available = balance − committed` arithmetic.

## Gaps / NOT_IMPLEMENTED
- Delegate/invoice/dispute/delegation paths (`issue_invoice`, `settle_invoice`, `get_invoice`, `dispute_payment`, `resolve_dispute`, `get_dispute`, `delegate`, `revoke_delegation`, `get_delegation`, `withdraw`, `update_rules`) are **not implemented** — not exercised by any v0.1 vector. The lane implements only the vector-exercised attestation + gate slice.
- No GenVM/gensol deployment, no glsim integration tests, no sender cryptography/signature checks (lane runs as plain Python; `initialize` owner and `evidence_hash` are carried but not cryptographically verified).
- `DELEGATE_PER_TX_LIMIT` / `DELEGATE_DAILY_LIMIT` reason codes exist in CAPABILITY but have no implementation in this lane.
- `ATTESTATION_INVALID_STATUS` at gate time is a defensive unreachable branch (registration enforces the status vocabulary first).
- No conformance receipt claimed; capability status remains as declared in the manifest.

## Verification
```
$ cd /home/ubuntu/nomos && python3 convergence-lanes/ppa/your_build.py primitives/ppa/vectors/v0.1.json
PASS ppa/ppa-gate-off-backcompat-001
PASS ppa/ppa-att-missing-fail-closed-002
PASS ppa/ppa-att-valid-admits-003
PASS ppa/ppa-att-expired-004
PASS ppa/ppa-att-revoked-005
PASS ppa/ppa-att-invalid-status-register-rejected-006
PASS ppa/ppa-att-subject-mismatch-007
PASS ppa/ppa-att-issuer-unauthorized-008
PASS ppa/ppa-att-policy-mismatch-009
PASS ppa/ppa-att-duplicate-id-rejected-010
PASS ppa/ppa-att-schema-pii-rejected-011
PASS ppa/ppa-payment-id-replay-rejected-012
PASS ppa/ppa-denied-id-retryable-013
PASS ppa/ppa-multi-candidate-conservation-014
PASS ppa/ppa-att-get-unknown-015

15/15 vectors passed for ppa
exit=0
```
Direct adversarial checks (inline python3, not vector-driven): per-tx deny conserves balance and id PASS; daily-window deny after 500+500 against 1000 cap PASS; `INSUFFICIENT_COMMITMENT` on balance 200 vs 300 PASS; denylist → `POLICY_DENYLIST` PASS; not-yet-valid (issued 2030) → `ATTESTATION_INVALID` PASS; multi-candidate all-fail → last-fail reason PASS; double revoke rejects PASS.
Determinism: integer-only arithmetic, canonical JSON output, fixed NOW, no randomness; JUDGMENT_BOUNDARY = NONE, convergence mode EXACT.
