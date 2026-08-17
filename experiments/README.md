# Experiment Foundry — Nomos

Experiments exist to discriminate between competing architectural claims, not to decorate implementation work.

## Required experiment record

Each experiment must contain:

- ID and title;
- hypothesis;
- competing model/baseline;
- exact invariant or research question;
- environment(s);
- setup and fixtures;
- steps/commands;
- expected discriminating observation;
- actual observation;
- result: `PASS`, `FAIL`, `NOT_IMPLEMENTED`, or `BLOCKED`;
- artifacts/logs/commit/runtime identifiers;
- limitations;
- next smallest research action.

## Rules

- Prefer the smallest experiment capable of falsifying the claim.
- Record failures as evidence; never rewrite expected output after seeing the result.
- Benchmarks must state what is measured and what is not.
- Cross-environment experiments must hold canonical semantics constant.
- For GenLayer, isolate whether the result depends on Intelligent Contract judgment, validator/equivalence behavior, or deterministic code.
- A successful happy-path demo is not an adversarial experiment.

## Initial benchmark family

The first shared economic benchmark should model one stable receivable/claim identity moving through evidence, workflow authorization, allocation, encumbrance, commitment, independent authorization, settlement and Gaia rectification.

Adversarial branches should include double financing, stale proof, lifecycle-version confusion, conflicting allocations, revoked authority, exhausted capacity, duplicate replay, contradictory evidence, failed settlement, and unauthorized rectification.
