# Nomos Constitution

This document is the highest-authority engineering document in the Nomos repository.

## Article I — Semantic Sovereignty

A Nomos primitive is defined by its economic meaning, state model, invariants, authority boundaries, failure semantics, and observable guarantees.

No VM, chain, account model, SDK, standard, AI model, oracle, bridge, wallet, database, or product interface may redefine those semantics.

Environment adapters may implement, approximate, or declare a semantic requirement unsupported. They may not silently weaken it.

## Article II — Portable Primitive, Mandatory GenLayer Implementation

Canonical specifications are environment-neutral.

Every Nomos primitive MUST have an executable GenLayer implementation. GenLayer is therefore the mandatory reference implementation environment for the primitive stack.

Additional EVM, offchain, Move, Solana, or other implementations are valid where they preserve the same canonical semantics.

Each implementation MUST identify its execution profile and explain:

- which canonical guarantees it implements directly;
- which guarantees depend on another system;
- which guarantees are unsupported;
- which environment-specific assumptions are introduced.

A primitive may not reach `CONFORMANT` or `RELEASED` without executable GenLayer implementation evidence.

GenLayer is also the reference judgment substrate for judgment-bearing Nomos primitives.

Mandatory GenLayer implementation does NOT imply mandatory non-deterministic judgment. A deterministic primitive MUST remain deterministic where its safety properties require determinism and MUST NOT introduce artificial LLM/validator judgment solely to satisfy the GenLayer requirement.

## Article III — Judgment Boundary

Intelligence is allowed only where the primitive requires judgment that cannot be reduced to deterministic computation without changing the problem.

Every judgment-bearing primitive MUST specify:

1. the exact question requiring judgment;
2. admissible evidence;
3. deterministic preconditions;
4. validator/evaluator output schema;
5. equivalence/consensus criterion;
6. deterministic postconditions;
7. invariants that judgment can never override;
8. `UNDETERMINED` behavior.

Canonical pattern:

```text
DETERMINISTIC PRECONDITIONS
          ↓
INTELLIGENT JUDGMENT
          ↓
EQUIVALENCE / CONSENSUS
          ↓
CANONICAL DECISION
          ↓
DETERMINISTIC STATE TRANSITION
```

`LLM output → money movement` is not a valid Nomos architecture.

## Article IV — Authority Separation

Nomos MUST preserve the distinction:

```text
Evidence ≠ Policy ≠ Standing Authority ≠ Allocation
         ≠ Agreement ≠ Encumbrance ≠ Commitment
         ≠ Replay Authority ≠ Settlement ≠ Rectification
```

A primitive may compose with another; it may not inherit another primitive's authority implicitly.

Examples:

- Path does not allocate capital.
- DAA does not establish standing delegation.
- Pact does not guarantee backing capital.
- Capital Commitment does not grant replay authority.
- Gaia does not gain execution authority from exception state.

## Article V — Evidence Before Assertion

Claims about implementation, security, compatibility, novelty, performance, or production status require evidence.

Acceptable evidence includes:

- executable tests;
- canonical test vectors;
- experiment receipts;
- official protocol documentation;
- standards specifications;
- reproducible deployment receipts;
- source-linked research records.

A demo is not evidence of a guarantee unless the guarantee is directly measured by the demo.

## Article VI — Research Before Reinvention

Before introducing a primitive or mechanism, Research Foundry MUST establish:

- exact problem statement;
- existing standards and prior art;
- closest semantic equivalents;
- what is transport/mechanism versus actual primitive meaning;
- novelty claims that must NOT be made;
- surviving research question;
- falsifiers;
- smallest discriminating experiment.

Standards provide machinery. Nomos primitives provide economic semantics.

## Article VII — Identity and Lineage

Economic identity MUST remain distinct from evidence snapshots.

For claim-bearing instruments:

```text
claimId != proofHash
```

A lifecycle update may create a new immutable proof without creating a new economic claim.

Any primitive with mutable evidence MUST define stable identity, versioning, lineage, amendment semantics, and supersession rules.

## Article VIII — Deterministic Economic Safety

Capacity, conservation, replay, uniqueness, accounting, expiry, reservation, encumbrance, and authority checks MUST remain deterministic unless the canonical specification proves why deterministic treatment is impossible.

Subjective judgment may determine a bounded decision. It may not mutate unrelated accounting or bypass the safety core.

## Article IX — Exception Does Not Suspend Authorization

Failure, dispute, mismatch, or rectification does not create authority.

Gaia may prescribe a resolution obligation. Corrective execution MUST pass the same authorization requirements appropriate to that action.

Historical truth is append-only. Rectification creates new evidence and state transitions; it does not rewrite confirmed prior events.

## Article X — Conformance Over Implementation Similarity

Two implementations are equivalent Nomos implementations if they preserve the same canonical observable guarantees, even if their mechanisms differ.

Every primitive MUST expose environment-independent conformance vectors wherever possible.

Environment-specific tests supplement canonical vectors; they do not replace them.

GenLayer conformance is mandatory. Other environment conformance is additive.

## Article XI — Explicit Unsupported State

An implementation MUST say `UNSUPPORTED`, `NOT_IMPLEMENTED`, `BLOCKED`, or `FAIL` when appropriate.

It is forbidden to simulate support by weakening a requirement, omitting the hard case, returning optimistic defaults, or substituting documentation for execution evidence.

## Article XII — Adversarial Completion

A primitive is not implementation-grade until it has been tested against its own invariants and adversarial model.

Minimum adversarial categories:

- replay;
- stale evidence;
- identity/version confusion;
- authority revocation;
- concurrent/conflicting operations;
- capacity exhaustion;
- partial execution;
- external dependency failure;
- contradictory evidence;
- unauthorized recovery;
- cross-environment semantic drift.

## Article XIII — Receipts

Every claimed release MUST produce a receipt containing:

- primitive and version;
- canonical spec version/hash;
- environment profile and version;
- source commit;
- tests executed;
- conformance result;
- adversarial experiment result;
- known limitations;
- deployment/runtime identifiers where applicable;
- timestamp.

Every release receipt MUST include a GenLayer implementation receipt.

## Article XIV — Interface Follows Capability

Frontends, SDKs, APIs, MCP surfaces, demos, docs, and agent skills may expose only capabilities that exist in the implementation registry.

Every reusable implementation module MUST include adjacent usage documentation sufficient for another engineer or agent to consume it without guessing.

## Article XV — Change Control

A change to implementation code is ordinary engineering.

A change to canonical semantics, invariants, authority boundaries, identity rules, failure semantics, or the mandatory GenLayer implementation requirement is a constitutional/specification change and MUST include:

- rationale;
- compatibility analysis;
- migration impact;
- new/updated conformance vectors;
- adversarial review;
- research record where the change is substantive.

No implementation convenience is sufficient reason to silently change a primitive.
