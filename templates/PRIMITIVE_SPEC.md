# <Primitive Name> — Canonical Specification

Status: DISCOVERY | RESEARCHING | SPECIFIED | IMPLEMENTING | CONFORMANT | RELEASED | BLOCKED
Version: 0.x

## 1. Problem

State the economic/coordination problem without reference to a chain, VM, library, standard, or product UI.

## 2. Primitive Meaning

Define exactly what this primitive represents.

## 3. Non-Goals

List adjacent concerns this primitive explicitly does not own.

## 4. Economic Object / State Model

Define stable identity, versioning, lifecycle and ownership.

## 5. Inputs

Canonical environment-neutral inputs.

## 6. Outputs

Canonical environment-neutral outputs.

## 7. State Transitions

List valid transitions and invalid transitions.

## 8. Invariants

Enumerate invariants as testable statements.

## 9. Authority Boundary

Answer:
- who may create this object/state?
- who may mutate it?
- what prior authority must exist?
- what this primitive can never authorize by itself?

## 10. Judgment Boundary

If no intrinsic judgment exists, write `NONE` and explain why.

If judgment exists, specify:
- exact judgment question;
- admissible evidence;
- deterministic preconditions;
- structured decision schema;
- equivalence/consensus requirement;
- UNDETERMINED behavior;
- deterministic postconditions;
- invariants judgment can never override.

## 11. Failure Semantics

Define ordinary rejection, retryable failure, exceptional state, dispute, reconciliation, rectification and terminal failure where relevant.

## 12. Composition

Declare required/optional dependencies on other Nomos primitives. Never inherit their authority implicitly.

## 13. Environment-Neutral Conformance Vectors

Link canonical vectors that every claimed implementation must pass.

## 14. Prior Art / Standards

Separate:
- semantic prior art;
- transport/encoding standards;
- execution/account standards;
- settlement/custody standards;
- related but non-equivalent mechanisms.

## 15. Security / Threat Model

Link `THREAT_MODEL.md`.

## 16. Falsifiers

What findings would show that the primitive is unnecessary, incorrectly scoped, or better represented by another abstraction?

## 17. Open Research Questions

State unresolved questions explicitly.
