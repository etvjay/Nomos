# Policy Envelope — GenLayer Implementation Contract

Status: NOT_IMPLEMENTED

## Required GenLayer behavior
- Enforce hard constraints deterministically.
- Invoke Intelligent Contract judgment only for explicitly declared mandate clauses.
- Return structured admissibility findings plus evidence/decision commitments.
- Preserve `UNDETERMINED` and reject any result that exceeds hard bounds.

## Must never do
- let interpretation override amount/capacity/expiry/identity constraints;
- treat policy approval as execution authority;
- convert unavailable evidence into approval.

## Required evidence
GenVM lint, deterministic-boundary tests, mandate interpretation tests, canonical vectors, integration tests, and deployment/CLI evidence.
