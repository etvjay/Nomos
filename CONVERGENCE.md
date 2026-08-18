# Nomos Convergence Protocol

Nomos must support multiple humans, coding agents, research agents, and partner teams working at the same time without requiring shared conversational context.

The repository is the coordination surface.

## Independent-build invariant

For a declared primitive version:

```text
same canonical authority
+ same capability contract
+ same canonical vectors
+ same acceptance gates
= same admissible build result
```

A partner working in another repository, machine, agent runtime, or organization should be able to reproduce the accepted behavior and build on top without knowing who implemented the original or what private conversation produced it.

This does **not** require byte-identical implementation code.

- Deterministic primitives use `EXACT` convergence: canonical inputs must produce exactly equivalent observable state/output.
- Judgment-bearing primitives use `SEMANTIC` convergence: validators/builds may differ internally, but canonical inputs must resolve inside the same bounded output relation declared by the primitive's `DECISION_BOUNDARY.md` and `CAPABILITY.json`.
- Free-form model reasoning, local notes, hidden prompts, and agent memory are never convergence authority.

## Authority order

All workers use this order:

1. `CONSTITUTION.md`
2. target primitive `SPEC.md`, `INVARIANTS.md`, `THREAT_MODEL.md`, `DECISION_BOUNDARY.md`
3. target primitive `CAPABILITY.json` when present
4. accepted research/experiment evidence
5. active Work Contract
6. current official GenLayer implementation truth
7. implementation code and tests
8. Convergence Receipt
9. SDK/interface/demo surfaces

A lower layer may not silently reinterpret a higher layer.

## Parallel work model

Nomos work is divided into non-overlapping lanes.

### Foundation lane

The following are shared constitutional/foundation state and MUST have a single integration owner for a given change window:

```text
CONSTITUTION.md
GOVERNANCE.md
AGENTS.md
CONVERGENCE.md
nomos.manifest.json
convergence/**
templates/**
tools/**
.github/workflows/**
shared SDK/package roots
```

Primitive workers must not opportunistically edit foundation state just to make their branch pass.

### Primitive lane

Each `primitives/<primitive-id>/` directory is independently buildable unless its Work Contract explicitly declares a cross-primitive dependency.

Two workers may build different primitives concurrently.

Two workers may also independently implement the same primitive as competing/reproducibility builds, provided they share the same authority fingerprint and capability version. Convergence is decided by the canonical gates, not by which implementation was written first.

### Integration lane

Cross-primitive compositions, shared SDK changes, manifest changes, or public interface changes enter an integration lane after primitive-local gates pass.

## Work Contract

Every material parallel work item SHOULD begin from a machine-readable Work Contract copied from `templates/WORK_CONTRACT.json`.

A Work Contract freezes:

- `workId`
- `baseCommit`
- target primitive(s)
- lane type
- allowed paths
- change class
- authority fingerprint
- capability version
- dependencies
- acceptance gates
- whether public-interface mutation is allowed

The Work Contract is an execution boundary, not a planning document.

A worker may discover that the contract is wrong. In that case it must stop the affected claim, record the contradiction, and propose a new Work Contract or higher-authority change. It must not silently widen its lane.

## Capability contract

`CAPABILITY.json` is the portable build-on-top contract for a mature primitive.

It tells another builder, without reading implementation internals:

- what the primitive is called and versioned as;
- whether convergence is EXACT or SEMANTIC;
- canonical input/output types;
- public methods/events;
- stable status/error vocabulary;
- state ownership;
- composition dependencies;
- security/authority assumptions;
- implementation path;
- canonical vectors;
- commands that reproduce the local proof surface;
- unsupported behavior.

`CAPABILITY.json` becomes mandatory at `IMPLEMENTING` and later.

Public consumers should bind to this contract plus the primitive specification, not to undocumented implementation details.

Changing a public capability incompatibly is not a patch. It requires an explicit version change and compatibility analysis.

## Authority fingerprint

Nomos computes a deterministic authority fingerprint from the canonical files that define a primitive:

```text
SPEC.md
INVARIANTS.md
THREAT_MODEL.md
DECISION_BOUNDARY.md
CAPABILITY.json (when present)
vectors/**
```

The fingerprint identifies the semantic build target.

Two agents claiming to implement the same work but using different authority fingerprints are not working on the same target and MUST NOT be treated as convergent merely because both test suites are green.

Use:

```bash
python tools/nomos_converge.py fingerprint <primitive-id>
```

## Convergence Receipt

Every material handoff that claims reproducible implementation evidence SHOULD produce a receipt based on `templates/CONVERGENCE_RECEIPT.json`.

A receipt records:

- work ID;
- primitive ID;
- base and result commit;
- authority fingerprint;
- capability version;
- convergence mode;
- exact commands executed;
- gate results;
- evidence paths;
- tool/runtime versions where material;
- known `NOT_IMPLEMENTED` / `BLOCKED` dependencies.

A receipt is evidence of what was run, not permission to overstate what was not run.

## Reproduction protocol

A new partner should be able to:

```text
1. clone/fetch the declared result commit
2. read CONSTITUTION + primitive canonical files
3. inspect CAPABILITY.json
4. recompute the authority fingerprint
5. run the declared commands
6. run canonical vectors
7. compare results under EXACT or SEMANTIC convergence
8. consume the public capability surface
9. extend in a new Work Contract without depending on private context
```

Repository checks:

```bash
python tools/nomos_lint.py
python tools/nomos_converge.py check
python tools/nomos_converge.py fingerprint <primitive-id>
python tools/nomos_converge.py verify-receipt <receipt.json>
```

## Merge/acceptance rule

A contribution converges only when:

1. it targets the declared authority fingerprint;
2. it stays within its Work Contract lane;
3. primitive-local gates pass;
4. previous PASS gates remain PASS;
5. public capability drift is explicit/versioned;
6. canonical vectors satisfy the declared convergence relation;
7. the handoff records exact evidence and known gaps;
8. integration gates pass for any shared/cross-primitive change.

Green local tests alone are insufficient.

## Why this exists

Nomos is meant to be financial infrastructure for GenLayer builders. Its semantics must survive team boundaries, agent boundaries, repository forks, independent reimplementations, and future SDK/application layers.

The goal is not to make every contributor write identical code.

The goal is to make independently produced code converge on the same financial guarantees and expose a stable surface another builder can safely compose on top of.
