# Nomos Conformance

Conformance answers one question:

> Does this implementation preserve the canonical observable guarantees of the primitive in this environment?

## Canonical vectors

Canonical vectors belong with the primitive and are environment-neutral where possible. Each vector must define:

- pre-state;
- input/action;
- expected output;
- expected state transition;
- expected error/failure class if rejected;
- invariants being exercised.

## Environment adapters

An environment test harness translates a canonical vector into executable calls without changing its expected semantics.

If the environment cannot express a required guarantee, report `UNSUPPORTED`; do not alter the vector.

## Minimum conformance categories

- valid transition;
- invalid transition;
- identity and lineage;
- authority and revocation;
- replay/uniqueness;
- expiry/freshness;
- concurrency/conflict;
- capacity/conservation;
- partial execution/atomicity;
- external dependency failure;
- exceptional/rectification path;
- judgment `UNDETERMINED` where applicable.

## Cross-environment comparison

Deterministic semantics should produce observably equivalent outcomes across implementations. Judgment-bearing semantics need not produce byte-identical internal traces, but must remain within the canonical decision schema, equivalence relation, deterministic bounds and postconditions.

## Evidence states

Every test/receipt reports one of:

- `PASS`
- `FAIL`
- `NOT_IMPLEMENTED`
- `BLOCKED`

No ambiguous green state is allowed.
