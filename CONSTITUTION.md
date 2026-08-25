# Nomos Constitution

This document is the highest-authority engineering document in the Nomos repository.

## Article I - Product Purpose

Nomos exists to provide **reusable financial primitives for developers building applications on GenLayer**.

A Nomos primitive is not merely a research abstraction. Its released form must be consumable as a GenLayer building block with explicit semantics, executable Intelligent Contract implementation, tests, developer documentation, and composition examples.

Cross-environment implementations may exist for research, interoperability, reference modeling, or conformance comparison. They are secondary to the GenLayer product target.

## Article II - Semantic Sovereignty

A Nomos primitive is defined by its economic meaning, state model, invariants, authority boundaries, failure semantics, and observable guarantees.

GenLayer, GenVM, Intelligent Contracts, Optimistic Democracy, SDKs, standards, account models, wallets, bridges, AI models, or product interfaces may implement or validate a primitive; they may not silently redefine its economic semantics.

This semantic separation exists to make GenLayer implementations correct and composable, not to make GenLayer optional.

## Article III - Mandatory GenLayer Implementation

Every Nomos primitive MUST have an executable GenLayer implementation before it may be `CONFORMANT` or `RELEASED`.

The primary implementation model is:

```text
Nomos financial primitive
        ↓
Intelligent Contract
        ↓
GenVM execution
        ↓
Optimistic Democracy
        ↓
finalized GenLayer state
```

Intelligent Contracts are the programmable implementation surface. Optimistic Democracy is the network consensus mechanism used to validate GenLayer execution, including non-deterministic operations.

Neither is itself a Nomos financial primitive.

## Article IV - Intelligence and Equivalence Boundary

Non-deterministic intelligence is allowed only where the primitive intrinsically requires judgment that cannot be reduced to deterministic computation without changing the problem.

Every judgment-bearing primitive MUST specify:

1. the exact question requiring judgment;
2. admissible evidence;
3. deterministic preconditions;
4. structured decision schema;
5. the Equivalence Principle / validator acceptance criterion;
6. deterministic postconditions;
7. invariants judgment can never override;
8. `UNDETERMINED` or disagreement behavior.

Canonical pattern:

```text
DETERMINISTIC PRECONDITIONS
          ↓
NON-DETERMINISTIC OPERATION
          ↓
EQUIVALENCE / VALIDATOR ACCEPTANCE
          ↓
CANONICAL DECISION
          ↓
DETERMINISTIC STATE TRANSITION
```

A deterministic primitive still implements as an Intelligent Contract, but MUST NOT invent unnecessary LLM judgment.

`free-form model output → unrestricted money movement` is forbidden.

## Article V - Authority Separation

Nomos MUST preserve the distinction:

```text
Evidence ≠ Verification ≠ Policy ≠ Recommendation
         ≠ Standing Authority ≠ Authority Allocation
         ≠ Agreement ≠ Encumbrance ≠ Commitment
         ≠ Replay Authority ≠ Settlement ≠ Rectification
```

A primitive may compose with another; it may not inherit another primitive's authority implicitly.

Examples:

- Mandate Allocation produces recommendation/evaluation, not authority.
- DAA creates bounded authority but does not reserve capital.
- Path does not allocate capital.
- Pact does not guarantee backing capital.
- Claim Encumbrance does not reserve pool capital.
- Capital Commitment does not grant replay authority.
- DAL does not prove economic independence of authorizations.
- Gaia does not gain execution authority from exception state.

## Article VI - Evidence Before Assertion

Claims about implementation, security, compatibility, performance, GenLayer behavior, consensus behavior, or production status require evidence.

Acceptable evidence includes:

- executable direct tests;
- GenVM linting;
- canonical conformance vectors;
- equivalence/validator experiments;
- integration tests;
- adversarial experiment receipts;
- official GenLayer documentation;
- standards specifications;
- reproducible deployment receipts;
- source-linked research records.

A demo is not evidence of a guarantee unless the guarantee is directly measured by the demo.

## Article VII - Research Before Reinvention

Before introducing or materially changing a primitive, Research Foundry MUST establish:

- exact financial/coordination problem;
- existing standards and prior art;
- closest semantic equivalents;
- what is GenLayer machinery versus actual Nomos primitive meaning;
- novelty claims that must NOT be made;
- surviving research question;
- falsifiers;
- smallest discriminating experiment.

## Article VIII - Identity and Lineage

Economic identity MUST remain distinct from evidence snapshots.

For claim-bearing instruments:

```text
claimId != proofHash
```

A lifecycle update may create a new immutable proof without creating a new economic claim.

Any primitive with mutable evidence MUST define stable identity, versioning, lineage, amendment semantics, and supersession rules.

## Article IX - Deterministic Economic Safety

Capacity, conservation, replay, uniqueness, accounting, expiry, reservation, encumbrance, and authority checks MUST remain deterministic unless the canonical specification proves why deterministic treatment is impossible.

Subjective judgment may determine a bounded decision. It may not mutate unrelated accounting or bypass the safety core.

## Article X - Exception Does Not Suspend Authorization

Failure, dispute, mismatch, or rectification does not create authority.

Gaia may prescribe a resolution obligation. Corrective execution MUST pass the same authorization requirements appropriate to that action.

Historical truth is append-only. Rectification creates new evidence and state transitions; it does not rewrite confirmed prior events.

## Article XI - GenLayer Conformance

A released primitive MUST demonstrate that its GenLayer implementation preserves the canonical observable guarantees.

Conformance must include, as applicable:

- canonical state-transition vectors;
- deterministic invariant tests;
- direct GenVM tests;
- non-deterministic operation tests;
- Equivalence Principle / validator-quality tests;
- integration tests;
- adversarial tests;
- deployment/runtime evidence.

Additional environment conformance is additive and does not replace GenLayer conformance.

## Article XII - Explicit Unsupported State

An implementation MUST say `UNSUPPORTED`, `NOT_IMPLEMENTED`, `BLOCKED`, or `FAIL` when appropriate.

It is forbidden to simulate support by weakening a requirement, omitting the hard case, returning optimistic defaults, substituting documentation for execution evidence, or treating validator disagreement as approval.

## Article XIII - Adversarial Completion

A primitive is not implementation-grade until tested against its own invariants and adversarial model.

Minimum adversarial categories include:

- replay;
- stale evidence;
- identity/version confusion;
- authority revocation;
- concurrent/conflicting operations;
- capacity exhaustion;
- partial execution;
- external dependency failure;
- contradictory evidence;
- validator disagreement/equivalence instability where applicable;
- unauthorized recovery;
- semantic drift between primitive specification and Intelligent Contract.

## Article XIV - Developer Consumption Is Part of Completion

A released primitive MUST be usable by another GenLayer application developer without reverse-engineering its implementation.

Where appropriate, releases must include:

- canonical types/schemas;
- public Intelligent Contract methods;
- SDK/client helpers;
- deployment instructions;
- composition examples;
- expected errors/failure states;
- security assumptions;
- conformance and deployment receipts.

Every reusable module must include adjacent usage documentation.

## Article XV - Receipts

Every claimed release MUST produce a receipt containing:

- primitive and version;
- canonical spec version/hash;
- GenLayer implementation source commit;
- Intelligent Contract/runtime identifier where applicable;
- tests executed;
- equivalence/consensus evidence where applicable;
- conformance result;
- adversarial experiment result;
- known limitations;
- timestamp.

## Article XVI - Change Control

A change to implementation code is ordinary engineering.

A change to canonical semantics, invariants, authority boundaries, identity rules, failure semantics, GenLayer implementation requirements, or developer-facing guarantees is a specification/governance change and MUST include:

- rationale;
- compatibility analysis;
- migration impact;
- new/updated conformance vectors;
- adversarial review;
- research record where substantive.

Implementation convenience is never sufficient reason to silently change a primitive.
