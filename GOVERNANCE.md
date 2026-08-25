# Nomos Governance

Nomos governance is repository-mediated. Multiple partners and agents may build concurrently, but accepted work converges through shared canonical authority, machine-readable capability contracts, canonical vectors, executable gates, and commit-bound receipts rather than through shared conversational context.

Read `CONVERGENCE.md` for the full parallel-build and independent-reproduction protocol.

## Governing pipeline

Every Nomos primitive moves through these gates:

1. **Problem / Product Truth** - state the economic problem and intended guarantee without implementation language.
2. **Research Foundry** - prior art, standards, competing models, falsifiers, smallest discriminating experiment.
3. **Canonical Specification** - state, transitions, authority boundaries, invariants, failures, composition interfaces.
4. **Judgment Boundary** - identify deterministic versus judgment-bearing semantics.
5. **Capability Contract** - publish the portable consumer surface and convergence mode in `CAPABILITY.json`.
6. **Work Contract** - freeze the base commit, semantic target, lane, allowed paths, dependencies, and acceptance gates for material parallel work.
7. **GenLayer Implementation** - implement the primitive as an Intelligent Contract/state machine without semantic drift.
8. **Conformance** - run canonical vectors and implementation-specific tests.
9. **Adversarial Experiment** - red-team invariants, concurrency, revocation, stale state, failure, disagreement, and recovery.
10. **Convergence Receipt** - record the exact target fingerprint, commands, gates, commit and known gaps.
11. **Release Receipt** - record exactly what was proven for release/deployment claims.
12. **Interface / Demo** - expose only registered capabilities.

A stage may feed evidence backward. No stage may skip a higher-authority semantic requirement.

## Required primitive capsule

Before a primitive can reach `IMPLEMENTING`, it must contain:

- `SPEC.md`
- `INVARIANTS.md`
- `THREAT_MODEL.md`
- `DECISION_BOUNDARY.md`
- `CAPABILITY.json`
- at least one canonical vector
- a registry entry in `nomos.manifest.json`
- an executable GenLayer implementation directory with adjacent usage documentation

Before `CONFORMANT`, it additionally requires:

- automated canonical conformance tests;
- adversarial experiment record;
- convergence evidence/receipt;
- release/conformance receipt.

## Repository-mediated convergence

The canonical acceptance relation is:

```text
same canonical authority
+ same capability contract
+ same canonical vectors
+ same acceptance gates
= same admissible build result
```

This allows independent teams to implement elsewhere and still establish that they built the same primitive.

### Deterministic primitives

Use `EXACT` convergence. Independent implementations must produce equivalent observable state/output for the same canonical inputs.

### Judgment-bearing primitives

Use `SEMANTIC` convergence. Internal model reasoning, prose, or execution path may vary, but the result must lie inside the bounded output/equivalence relation declared by the primitive.

A green test suite against a different authority fingerprint is not convergence.

## Parallel work lanes

### Foundation lane

Repository-wide authority and shared developer surfaces have a single integration owner per change window. This includes constitution/governance, manifests, templates, convergence tooling, shared packages and CI.

### Primitive lane

A primitive directory is independently buildable. Multiple partners can work on different primitives simultaneously. Competing implementations of the same primitive are valid when they share the same authority fingerprint and capability version.

### Integration lane

Cross-primitive compositions, shared SDK changes, manifest/public-surface changes and release integrations enter the integration lane after primitive-local gates pass.

Workers must not silently widen their lane.

## Review gates

### Gate A - Semantic Integrity

Reject when:
- the implementation changes the meaning of the primitive;
- a standard is mistaken for the primitive itself;
- an environment-specific limitation is hidden;
- two distinct authority/economic states are collapsed.

### Gate B - Intelligence Necessity

For any judgment-bearing implementation, ask:

> If judgment is removed, does the problem materially change?

If no, prefer deterministic implementation.

Require exact evaluator question, evidence, equivalence rule, structured output, deterministic bounds, and `UNDETERMINED` behavior.

### Gate C - Economic Safety

Require tests for conservation/capacity, replay, identity/versioning, expiry, revocation, atomicity where claimed, and competing/concurrent actions.

### Gate D - Convergence

Require:
- current authority fingerprint;
- matching capability version;
- canonical vectors;
- correct `EXACT` or `SEMANTIC` convergence mode;
- no undocumented public surface;
- no hidden dependency on partner/agent memory.

### Gate E - Evidence

No claim is upgraded from `NOT_IMPLEMENTED` or `BLOCKED` without executable evidence. A URL or file presence is not runtime proof.

## Foundry stack

Nomos uses the existing foundry discipline as follows:

- **Research Foundry** - prior art, standards, research questions, falsifiers.
- **Experiment Foundry** - smallest discriminating benchmarks, repeatability, receipts.
- **Product Foundry / red-team** - adversarial product and system assumptions.
- **Interface Foundry** - interaction design only after capability truth is established.
- **Demo Foundry** - deterministic evidence-driven demonstrations, never capability theater.

Environment-specific skills supplement these gates. For GenLayer, use current official contract-writing, GenVM linting, direct-test, integration-test, documentation and CLI/deployment guidance.

## Status transitions

Allowed primitive lifecycle:

`DISCOVERY → RESEARCHING → SPECIFIED → IMPLEMENTING → CONFORMANT → RELEASED`

Any state may move to `BLOCKED`. A failed invariant returns the primitive to the earliest stage whose assumption was invalidated.

## Change classes

- **PATCH** - implementation change preserving canonical semantics and public capability compatibility.
- **PROFILE** - implementation/environment mapping change preserving canonical semantics.
- **CAPABILITY** - public developer surface change; incompatible changes require capability versioning and compatibility analysis.
- **SPEC** - canonical semantic/invariant change.
- **CONSTITUTIONAL** - repository-wide law/convergence change.

`CAPABILITY`, `SPEC`, and `CONSTITUTIONAL` changes require explicit compatibility analysis. `SPEC` and `CONSTITUTIONAL` changes also require updated research rationale, vectors, and adversarial evidence.
