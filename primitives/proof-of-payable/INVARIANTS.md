# Proof of Payable - Invariants

- `claimId` is stable across evidence snapshots.
- `claimId != proofHash`.
- Lifecycle transitions are explicit and append-only.
- Evidence mutation cannot silently create a new economic claim.
- A proof cannot allocate, reserve, encumber, or settle capital by itself.
