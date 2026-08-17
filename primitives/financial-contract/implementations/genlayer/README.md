# Financial Contract — GenLayer Implementation Contract

Status: NOT_IMPLEMENTED

## Required GenLayer behavior
- Preserve deterministic principal, balance, payment, maturity, and lifecycle accounting.
- Accept explicitly declared contractual predicates/evidence for Intelligent Contract evaluation.
- Return structured clause-resolution outcomes with evidence commitments and `UNDETERMINED` behavior.
- Apply economic consequences only through deterministic state transitions authorized by the canonical contract/workflow.
- Preserve amendment and historical-event lineage.

## Must never do
- let a model directly rewrite balances;
- reinterpret confirmed historical cash flows;
- execute corrective value movement without authorization;
- treat unavailable external evidence as satisfied conditions.

## Required evidence
GenVM lint, direct accounting tests, clause-resolution tests, canonical vectors, lifecycle/adversarial tests, integration tests, and deployment/CLI evidence.
