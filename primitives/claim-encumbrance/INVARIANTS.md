# Claim Encumbrance - Invariants

- `sum(activeEncumbrances(claimId)) <= financeableAmount(claimId)`.
- Stable claim identity, not proof hash, keys capacity.
- Reserve/commit/release/settle transitions are atomic.
- Evidence-version changes cannot reset encumbrance.
- Release/settle cannot restore capacity more than once.
