# Gaia — GenLayer Implementation Contract

Status: NOT_IMPLEMENTED

## Required GenLayer behavior
- Open explicit cases for operationally meaningful dispute, exception, rectification, or reconciliation conditions.
- Evaluate only declared case questions using admissible evidence.
- Return structured case classification and bounded RectificationObligations.
- Support `UNDETERMINED` and contradictory-evidence states.
- Require normal Workflow Authorization for any corrective execution.
- Preserve original confirmed economic history and append rectification evidence.
- Prevent premature case closure while required obligations remain unresolved.

## Must never do
- make a refund/transfer merely because judgment says it is appropriate;
- grant authority from exception state;
- rewrite an original confirmed settlement into a failure;
- create Gaia cases for every ordinary deterministic rejection.

## Required evidence
GenVM lint, direct tests, contradictory-evidence tests, unauthorized-recovery tests, append-only-history tests, canonical vectors, integration tests, and deployment/CLI evidence.
