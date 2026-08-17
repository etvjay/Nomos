# DAA — GenLayer Implementation Contract

Status: NOT_IMPLEMENTED

## Required GenLayer behavior
- Receive canonical claim/evidence, policy, candidate, pool, request, and constraint inputs.
- Enforce deterministic preconditions before judgment.
- Ask a bounded allocation question and return structured fields such as eligibility, max allocation, risk class, conditions hash, and evidence root.
- Preserve `UNDETERMINED`.
- Apply deterministic postconditions so judgment cannot exceed request, capacity, expiry, or authority bounds.
- Store or emit an immutable AllocationAward decision object.

## Must never do
- move funds from the judgment result;
- treat allocation as commitment;
- mutate unrelated pool accounting;
- hide validator disagreement behind approval.

## Required evidence
GenVM lint, direct tests, equivalence/validator-quality tests, canonical vectors, adversarial allocation tests, integration tests, and deployment/CLI evidence.
