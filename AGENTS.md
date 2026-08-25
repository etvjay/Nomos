# AGENTS.md - Nomos Build Contract

This file governs all human and agent contributors.

## Mission

Build reusable financial primitives for GenLayer whose semantics survive implementation by different humans, agents, teams, repositories, and machines.

Nomos coordination is repository-mediated. Private conversation, agent memory, local notes, or hidden reasoning are never required to reproduce an accepted result.

Read `CONVERGENCE.md` for the parallel-build and reproduction protocol.

## Before changing code

1. Read `CONSTITUTION.md`.
2. Read `CONVERGENCE.md`.
3. Read the target primitive's `SPEC.md`, `INVARIANTS.md`, `THREAT_MODEL.md`, and `DECISION_BOUNDARY.md`.
4. Read the target primitive's `CAPABILITY.json` when present.
5. Read `environments/genlayer/PROFILE.md`.
6. Check `nomos.manifest.json` for claimed status/capability version.
7. Inspect existing research/experiment evidence before inventing a new mechanism.
8. For material parallel work, operate under a Work Contract derived from `templates/WORK_CONTRACT.json`.

## Non-negotiable rules

- Every primitive MUST have an executable GenLayer implementation before it can become conformant.
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
- Do not expose a frontend/API capability until it is present in `CAPABILITY.json` and the implementation registry.
- Do not depend on another contributor's private context to understand a public module.
- Do not silently widen a Work Contract lane.
- Do not edit shared foundation state from a primitive lane merely to make local tests pass.
- Do not treat two green builds as equivalent if they target different authority fingerprints.

## Repository-mediated convergence

For a declared primitive version:

```text
same canonical authority
+ same capability contract
+ same canonical vectors
+ same acceptance gates
= same admissible build result
```

Convergence modes:

- `EXACT` for deterministic primitives: the same canonical input must produce equivalent observable output/state.
- `SEMANTIC` for judgment-bearing primitives: internal reasoning/prose may differ, but results must fall inside the same bounded decision relation declared by the primitive.

Run:

```bash
python tools/nomos_converge.py check
python tools/nomos_converge.py fingerprint <primitive-id>
```

A material handoff should carry a Convergence Receipt derived from `templates/CONVERGENCE_RECEIPT.json`.

## Required primitive developer surface

Every primitive at `IMPLEMENTING`, `CONFORMANT`, or `RELEASED` MUST contain `CAPABILITY.json`.

`CAPABILITY.json` is the portable build-on-top contract and must describe at least:

- primitive/capability version;
- convergence mode;
- public methods/events;
- canonical input/output/status/error surface;
- state ownership and negative boundary;
- GenLayer implementation path;
- canonical vector paths;
- reproduction commands;
- composition dependencies;
- unsupported behavior.

A developer should be able to consume this contract without reading undocumented implementation internals.

Incompatible public capability changes require an explicit capability-version change and compatibility analysis.

## Required implementation pattern

Every mature primitive MUST contain `implementations/genlayer/`.

Every implementation must contain adjacent usage documentation describing:

- public modules/interfaces;
- inputs and outputs;
- state ownership;
- dependencies;
- expected errors;
- security assumptions;
- how to run tests;
- what remains unsupported.

If a module is reusable by a frontend, SDK, agent, service, or another primitive, its usage documentation is part of the module's definition of done.

## GenLayer implementation rule

For a judgment-bearing primitive, document and implement:

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

For a deterministic primitive, explicitly declare `JUDGMENT_BOUNDARY = NONE` and implement the canonical deterministic semantics on GenLayer without adding artificial LLM/validator judgment.

Run GenVM linting, direct tests, integration tests and deployment/CLI checks appropriate to the implementation. The implementation must also pass canonical Nomos vectors.

## Testing order

1. repository/convergence checks;
2. unit/property tests;
3. canonical conformance vectors;
4. GenLayer direct/integration tests;
5. adversarial tests;
6. Experiment Foundry benchmark when a research claim is involved;
7. convergence/release receipt.

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
- Can an independent implementation pass by weakening the semantic guarantee?
- Can a downstream builder reconstruct the public behavior from the repository contract alone?

## Result language

Use only evidence-backed outcomes:

- `PASS`
- `FAIL`
- `NOT_IMPLEMENTED`
- `BLOCKED`

Never use "works", "production ready", "secure", or "supported" without identifying the receipt/test evidence that justifies the claim.

## Required handoff

Every material contribution must make available, in repository artifacts or PR description:

- Work Contract/work ID when applicable;
- base/result commit;
- primitive and capability version;
- authority fingerprint;
- inputs/outputs and public interface changes;
- invariants touched;
- external facts/evidence relied upon;
- exact commands run;
- tests/vectors added;
- gate results;
- known NOT_IMPLEMENTED/BLOCKED dependencies;
- security/secrets considerations;
- compatibility impact.

"Tests pass" is not a sufficient handoff.

## Definition of done

A change is done when:

- semantics remain compliant;
- the GenLayer implementation is present and updated where relevant;
- `CAPABILITY.json` accurately represents the public surface where required;
- relevant tests pass;
- new behavior has vectors;
- failure modes are explicit;
- usage docs are updated;
- manifest capability/status is accurate;
- repository convergence checks pass;
- a convergence/release receipt exists for any corresponding proof claim.
