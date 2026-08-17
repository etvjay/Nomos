# Nomos Governance

## Governing pipeline

Every Nomos primitive moves through these gates:

1. **Problem / Product Truth** — state the economic problem and intended guarantee without implementation language.
2. **Research Foundry** — prior art, standards, competing models, falsifiers, smallest discriminating experiment.
3. **Canonical Specification** — state, transitions, authority boundaries, invariants, failures, composition interfaces.
4. **Judgment Boundary** — identify deterministic versus judgment-bearing semantics.
5. **Environment Profile** — map the canonical spec to GenLayer, EVM, offchain, or another environment without semantic drift.
6. **Implementation** — code against the profile.
7. **Conformance** — run environment-neutral vectors and environment-specific tests.
8. **Adversarial Experiment** — red-team invariants, concurrency, revocation, stale state, failure and recovery.
9. **Release Receipt** — record exactly what was proven.
10. **Interface / Demo** — expose only registered capabilities.

A stage may feed evidence backward. No stage may skip a higher-authority semantic requirement.

## Required primitive capsule

Before a primitive can reach `IMPLEMENTING`, it must contain:

- `SPEC.md`
- `INVARIANTS.md`
- `THREAT_MODEL.md`
- `DECISION_BOUNDARY.md`
- at least one canonical vector
- a registry entry in `nomos.manifest.json`

Before `CONFORMANT`, it additionally requires:

- implementation README for each claimed environment;
- automated canonical conformance tests;
- adversarial experiment record;
- release receipt.

## Review gates

### Gate A — Semantic Integrity

Reject when:
- the implementation changes the meaning of the primitive;
- a standard is mistaken for the primitive itself;
- an environment-specific limitation is hidden;
- two distinct authority/economic states are collapsed.

### Gate B — Intelligence Necessity

For GenLayer or any AI/judgment-bearing implementation, ask:

> If judgment is removed, does the problem materially change?

If no, prefer deterministic implementation.

Require exact evaluator question, evidence, equivalence rule, structured output, deterministic bounds, and `UNDETERMINED` behavior.

### Gate C — Economic Safety

Require tests for conservation/capacity, replay, identity/versioning, expiry, revocation, atomicity where claimed, and competing/concurrent actions.

### Gate D — Cross-Environment Conformance

The same canonical input should lead to observably equivalent outcomes where the primitive declares deterministic semantics. For judgment-bearing semantics, equivalence is evaluated against the canonical output schema and acceptable decision relation, not byte-identical internal execution.

### Gate E — Evidence

No claim is upgraded from `NOT_IMPLEMENTED` or `BLOCKED` without executable evidence.

## Foundry stack

Nomos uses the existing foundry discipline as follows:

- **Research Foundry** — prior art, standards, research questions, falsifiers.
- **Experiment Foundry** — smallest discriminating benchmarks, repeatability, receipts.
- **Product Foundry / red-team** — adversarial product and system assumptions.
- **Interface Foundry** — interaction design only after capability truth is established.
- **Demo Foundry** — deterministic evidence-driven demonstrations, never capability theater.
- **Sound Foundry** — optional presentation layer; never part of protocol truth.

Environment-specific skills supplement these gates. For GenLayer, use the official contract-writing, GenVM linting, direct-test, integration-test, documentation and CLI/deployment skills where available.

## Status transitions

Allowed primitive lifecycle:

`DISCOVERY → RESEARCHING → SPECIFIED → IMPLEMENTING → CONFORMANT → RELEASED`

Any state may move to `BLOCKED`. A failed invariant returns the primitive to the earliest stage whose assumption was invalidated.

## Change classes

- **PATCH** — implementation change preserving all canonical semantics.
- **PROFILE** — environment mapping change preserving canonical semantics.
- **SPEC** — canonical semantic/invariant change.
- **CONSTITUTIONAL** — changes repository-wide law.

`SPEC` and `CONSTITUTIONAL` changes require updated research rationale, compatibility analysis, vectors, and adversarial evidence.
