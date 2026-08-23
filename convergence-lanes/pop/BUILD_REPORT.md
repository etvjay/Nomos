# BUILD_REPORT — proof-of-payable (convergence lane, independent build)

Primitive: `proof-of-payable` v0.1.0 · Mode: EXACT · JUDGMENT_BOUNDARY = NONE

## Result

- `python3 your_build.py <vectors.json>` runs all 17 canonical vectors in
  `primitives/proof-of-payable/vectors/v0.1.json`: **17/17 PASS** (ALL PASS).
- Built solely from SPEC.md, INVARIANTS.md, THREAT_MODEL.md,
  DECISION_BOUNDARY.md, CAPABILITY.json, vectors/v0.1.json.
- **Independence confirmation:** no file under
  `primitives/proof-of-payable/implementations/` was opened, listed, or read;
  no other implementation, runner, or tool source was consulted.

## State layout

Four TreeMap-keyed stores:
- `claims`: claim_id → full internal record (identity fields immutable after open).
- `proofs`: globally unique proof_id → proof record (`ATTACHED` status, hash, metadata).
- `lineage`: claim_id → ordered list of proof_id (append-only; never mutated retroactively).
- `counts`: claim_id → evidence count string (mirrored into the claim record).

Public projections are canonical JSON (sorted keys, compact separators) over
exactly the `equivalenceFields` for claims and
`{proof_id, claim_id, proof_hash, status}` for proofs. Non-canonical fields
(`created_at`, `created_by`) exist internally but are empty and never emitted —
the canonical surface stays deterministic.

## Lifecycle / rules implemented

DRAFT →(first attach)→ EVIDENCED → ATTESTED → SETTLED (terminal);
live → DISPUTED → REJECTED (terminal); any live → VOID (terminal).
Attest requires EVIDENCED status + evidence ≥ 1; settle requires ATTESTED +
evidence ≥ 1; terminal states reject every mutation including re-dispute,
re-attach, re-void, re-settle. Duplicate claim_id and duplicate proof_id are
rejected. Amount must be a positive decimal digit-string (rejects "", "0",
"00", "-5", "abc"). Metadata > 4096 UTF-8 bytes rejected. No capital effects
anywhere on the surface.

## Ambiguities & spec gaps found

1. **Metadata JSON validity unspecified.** CAPABILITY.json types it as
   "string (<=4096 bytes)" but nothing says whether malformed JSON must be
   rejected. Vectors don't cover it; I chose lenient (size check only) to keep
   the deterministic surface minimal. Worth a vector either way.
2. **Reject preconditions.** CAPABILITY.json says only `DISPUTED->REJECTED`;
   I reject reject_claim from anything but DISPUTED. Not vector-covered.
3. **Void scope.** "live->VOID" is stated; I interpret live as exactly
   {DRAFT, EVIDENCED, ATTESTED} (DISPUTED excluded), matching vector 011's
   terminal-dispute rejection but not directly tested from DISPUTED.
4. **Amount normalization.** Leading zeros ("007") accepted as-is since
   equivalence compares strings; spec doesn't say whether to normalize.
5. **`get_evidence` projection shape** (no metadata/status history beyond
   ATTACHED) is inferred from vectors 005/016 only; CAPABILITY.json just says
   "canonical-proof-json-string".
6. **Error channel.** Vector harness distinguishes ok/reject/""; I use a typed
   `Reject` exception locally. On GenVM this maps to revert semantics; the
   exact error-payload convention is not specified by the artifacts.

## Files created (lane dir only)

- `/home/ubuntu/nomos/convergence-lanes/pop/your_build.py`
- `/home/ubuntu/nomos/convergence-lanes/pop/BUILD_REPORT.md`

Nothing outside the lane directory was touched.
