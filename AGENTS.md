# AGENTS.md — Nomos Build Contract

This file governs all human and agent contributors.

## Mission

Build portable economic coordination primitives whose semantics survive implementation across environments.

## Before changing code

1. Read `CONSTITUTION.md`.
2. Read the target primitive's `SPEC.md`, `INVARIANTS.md`, `THREAT_MODEL.md`, and `DECISION_BOUNDARY.md`.
3. Read the target environment profile.
4. Check `nomos.manifest.json` for claimed status and capabilities.
5. Inspect existing research/experiment evidence before inventing a new mechanism.

## Non-negotiable rules

- Do not redefine a primitive to fit a VM or library.
- Do not introduce AI/LLM judgment into deterministic safety properties.
- Do not let judgment directly move money.
- Do not conflate claim identity with evidence snapshot identity.
- Do not conflate policy, delegation, allocation, agreement, encumbrance, commitment, replay authority, settlement, or rectification.
- Do not claim support without executable evidence.
- Do not mark a capability live because a schema/interface exists.
- Do not silently fall back to permissive behavior.
- Do not swallow exceptions that affect economic state or authorization.
- Do not mutate historical confirmed truth to model recovery.
- Do not create corrective execution paths that bypass ordinary authorization.
- Do not expose a frontend/API capability until it is present in the implementation registry.

## Required implementation pattern

Every environment implementation must contain adjacent usage documentation describing:

- public modules/interfaces;
- inputs and outputs;
- state ownership;
- dependencies;
- expected errors;
- security assumptions;
- how to run tests;
- what remains unsupported.

If a module is reusable by a frontend, SDK, agent, service, or another primitive, its usage documentation is part of the module's definition of done.

## GenLayer profile rule

Use GenLayer only for the explicitly declared judgment boundary.

A GenLayer implementation must document:

```text
DETERMINISTIC PRECONDITIONS
INTELLIGENT QUESTION
ADMISSIBLE EVIDENCE
EQUIVALENCE / CONSENSUS CONDITION
STRUCTURED DECISION
UNDETERMINED PATH
DETERMINISTIC POSTCONDITIONS
INVARIANTS JUDGMENT CANNOT OVERRIDE
```

Run GenVM linting, direct tests, integration tests and deployment/CLI checks appropriate to the implementation. The GenLayer implementation must still pass canonical Nomos vectors.

## Testing order

1. unit/property tests;
2. canonical conformance vectors;
3. environment-specific integration tests;
4. adversarial tests;
5. Experiment Foundry benchmark when a research claim is involved;
6. release receipt.

## Required adversarial questions

At minimum test:

- Can this be replayed?
- Can stale evidence authorize new state?
- Can the same economic object appear under another snapshot/version?
- What happens after authority revocation?
- What happens under two concurrent valid requests?
- Can capacity be overcommitted?
- Can partial execution leave an impossible state?
- Can an unavailable dependency be mistaken for approval?
- Can exception handling create authority?
- Can one environment pass by weakening a semantic guarantee?

## Result language

Use only evidence-backed outcomes:

- `PASS`
- `FAIL`
- `NOT_IMPLEMENTED`
- `BLOCKED`

Never use "works", "production ready", "secure", or "supported" without identifying the receipt/test evidence that justifies the claim.

## Definition of done

A change is done when:

- semantics remain compliant;
- relevant tests pass;
- new behavior has vectors;
- failure modes are explicit;
- usage docs are updated;
- manifest capability/status is accurate;
- a receipt exists for any release claim.
