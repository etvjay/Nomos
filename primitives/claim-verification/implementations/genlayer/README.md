# Claim Verification — GenLayer Implementation Contract

Status: NOT_IMPLEMENTED

## Required GenLayer behavior
- Receive exact claim/proof identity and admissible evidence references.
- Evaluate only the declared verification question.
- Return a canonical structured decision with evidence root and reasons/conditions encoded into bounded fields.
- Preserve `UNDETERMINED`/conflict states.
- Never mutate claim identity, financing capacity, or settlement state.

## Required evidence
GenVM lint, direct tests, canonical vectors, contradictory-evidence tests, integration tests, and deployment/CLI evidence before conformance.
