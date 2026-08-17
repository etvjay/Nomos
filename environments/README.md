# Environment Profiles

Canonical Nomos semantics live above any chain or VM. An environment profile states how those semantics are preserved in a concrete execution environment.

## Required profile sections

Each profile MUST define:

- execution model;
- state/finality model;
- account/authority model;
- signature model;
- replay model;
- external-data model;
- judgment/consensus model if applicable;
- failure semantics;
- cross-contract/service composition assumptions;
- unsupported canonical guarantees;
- environment-specific threats;
- required toolchain and test gates.

## GenLayer

GenLayer is Nomos' reference judgment substrate for primitives that intrinsically require subjective/external evaluation.

A GenLayer profile MUST preserve the canonical judgment boundary:

```text
Deterministic preconditions
  → non-deterministic evaluation
  → validator/equivalence resolution
  → structured bounded decision
  → deterministic state transition
```

GenLayer does not own deterministic accounting merely because a primitive also contains judgment.

## EVM

EVM profiles are preferred for deterministic safety cores such as capacity accounting, commitments, encumbrance, replay protection, settlement and signature/account adapters.

Standards may be used as mechanisms only when they preserve canonical semantics. An ERC/EIP is not automatically the Nomos primitive itself.

## Offchain

Offchain implementations may serve as reference models, simulators, indexers, APIs, evaluators, or execution runtimes. They MUST explicitly state trust assumptions and which guarantees require persistence, signatures, authenticated data, consensus, or an external settlement system.

## Adding another environment

Create `environments/<name>/PROFILE.md` and map every canonical guarantee to one of:

- `NATIVE` — directly enforced by the environment;
- `ADAPTER` — enforced through a named dependency/adapter;
- `EXTERNAL` — depends on an explicitly named external system;
- `UNSUPPORTED` — cannot currently preserve the guarantee.

`UNSUPPORTED` is valid. Silent semantic substitution is not.
