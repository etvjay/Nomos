# GenLayer Product Profile

Role: **primary execution and consensus environment for Nomos financial primitives**.

Nomos exists to give GenLayer application developers reusable financial building blocks. Every released Nomos primitive therefore ships as an executable GenLayer implementation.

## Implementation stack

```text
Nomos primitive semantics
        ↓
Intelligent Contract
        ↓
GenVM
        ↓
Optimistic Democracy
        ↓
finalized GenLayer state
```

### Intelligent Contracts

Intelligent Contracts are the programmable implementation surface for Nomos primitives. They own the primitive's GenLayer state machine, public methods, deterministic checks, and any declared non-deterministic operations.

### Optimistic Democracy

Optimistic Democracy is the GenLayer consensus/validation mechanism underneath Intelligent Contract execution. Nomos does not reimplement it and does not treat it as a financial primitive.

Where a Nomos primitive uses non-deterministic operations, the implementation must define the Equivalence Principle or validator acceptance condition narrowly enough that the network can validate outputs without allowing unconstrained semantic drift.

## Two implementation classes

### Deterministic financial primitive

Examples include Claim Encumbrance, Capital Commitment, and DAL.

```text
input
  ↓
deterministic validation
  ↓
deterministic state transition
  ↓
GenLayer consensus/finality
```

These MUST NOT introduce LLM judgment merely because they run as Intelligent Contracts.

### Judgment-bearing financial primitive

Examples include Claim Verification, Mandate Allocation, DAA where allocation itself requires qualitative judgment, Workflow Authorization where purpose interpretation is required, Financial Contract clauses requiring external interpretation, and Gaia.

```text
deterministic preconditions
        ↓
non-deterministic operation
        ↓
Equivalence Principle / validator acceptance
        ↓
structured bounded result
        ↓
deterministic postconditions
        ↓
state transition
```

## Required primitive mapping

Each GenLayer implementation MUST document:

- public Intelligent Contract methods;
- canonical state mapped to GenLayer storage;
- deterministic invariants;
- non-deterministic operations, if any;
- evidence sources and admissibility rules;
- Equivalence Principle / validator acceptance criterion, if any;
- `UNDETERMINED` / disagreement behavior;
- events/observable outputs;
- composition points with other Nomos primitives;
- security assumptions;
- unsupported behavior;
- SDK/client usage.

## Required verification stack

Use current official GenLayer tooling and documentation for:

- Intelligent Contract authoring;
- GenVM linting;
- direct tests;
- non-deterministic/equivalence tests where applicable;
- integration tests;
- GenLayer SDK/client integration;
- CLI/deployment checks.

All implementations must additionally pass Nomos canonical conformance vectors and adversarial experiments.

## Developer-consumption requirement

A released primitive is expected to be consumed by another financial application. Its GenLayer package must therefore expose enough documentation and helpers to support a pattern such as:

```text
app
  ↓
Nomos SDK/helper
  ↓
Nomos Intelligent Contract
  ↓
other composed Nomos primitives
```

The developer should not need to reconstruct core protocol semantics manually.

## Reject

- treating Optimistic Democracy as a Nomos primitive;
- calling generic LLM inference a financial primitive;
- free-form model output directly moving unrestricted value;
- deterministic accounting delegated to subjective judgment without necessity;
- validator disagreement treated as approval;
- primitive semantics rewritten to make implementation easier;
- GenLayer contract code without a usable developer-facing integration path.
