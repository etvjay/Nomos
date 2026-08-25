# Proof of Payable - GenLayer Implementation

Deterministic Intelligent Contract implementing Proof of Payable v0.1.

## Public modules/interfaces

Single contract: `ProofOfPayable` in `proof_of_payable.py`.

Write methods:

- `open_claim(claim_id, amount, external_ref, obligor)` - register a payable claim. `amount` must be a positive decimal uint-string; identity fields immutable after creation.
- `attach_evidence(claim_id, proof_id, proof_id_hash, metadata_json)` - append one immutable proof snapshot (`proof_id` globally unique, `metadata_json` ≤ 4096 bytes). First attachment moves `DRAFT → EVIDENCED` and sets `latest_proof_hash`.
- `attest_claim(claim_id)` - requires ≥1 attached proof.
- `dispute_claim(claim_id)` - any live status → `DISPUTED`.
- `reject_claim(claim_id)` - `DISPUTED → REJECTED` (terminal).
- `settle_claim(claim_id)` - `ATTESTED → SETTLED` (terminal); does not move capital.
- `void_claim(claim_id)` - live → `VOID` (terminal).

View methods:

- `get_claim(claim_id)` - canonical claim JSON or empty string if unknown.
- `get_evidence(proof_id)` - canonical proof JSON or empty string if unknown.

## Inputs and outputs

All state is returned as canonical JSON strings (sorted keys, no whitespace). See
`../CAPABILITY.json` for the exact field surface.

## State ownership

The contract owns: stable claim identity (immutable amount/external_ref/obligor),
append-only evidence lineage keyed by globally unique `proof_id`, and lifecycle state.
It owns nothing economic downstream: it cannot reserve, encumber, commit, or move capital.

## Dependencies

None beyond the pinned GenLayer Python SDK.

## Expected errors

All rejections raise `ValueError` with a `ProofOfPayable:` prefix:
unknown claim/proof ids, duplicate `claim_id`/`proof_id`, non-positive or malformed
amounts, missing required fields, oversized metadata, attest/settle without evidence,
and any mutation of a terminal (`REJECTED`/`SETTLED`/`VOID`) or non-live claim.

## Security assumptions

- Callers supply `proof_hash`; this primitive does not fetch or hash remote evidence.
- No access control on lifecycle transitions in v0.1 - authorization belongs to
  upstream Workflow Authorization / DAA composition. Do not expose an uncomposed
  deployment to untrusted writers expecting permissioned behavior.
- Deterministic accounting only: `JUDGMENT_BOUNDARY = NONE`.

## How to run tests

```bash
python tools/nomos_run_vectors.py \
  primitives/proof-of-payable/implementations/genlayer/proof_of_payable.py \
  --vectors primitives/proof-of-payable/vectors/v0.1.json
```

17 canonical vectors cover identity stability, append-only lineage, lifecycle legality,
terminal immutability, replay/duplicate rejection, and absence of capital effects.

## What remains unsupported

Substantive judgment over whether evidence supports the claimed condition is
explicitly out of scope - that is Claim Verification's SEMANTIC boundary consuming
the snapshots produced here. Deployment receipts and independent-partner convergence
evidence do not yet exist for this primitive.
