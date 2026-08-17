# Proof of Payable — Canonical Specification

Status: RESEARCHING
Version: 0.1.0

## Problem
Represent an economic obligation as a stable claim with lifecycle-specific evidence without confusing evidence snapshots with the identity of the underlying payable.

## Primitive meaning
Proof of Payable is an evidence-bearing representation that a particular economic claim exists in a stated lifecycle condition.

## Core invariants
- `claimId != proofHash`.
- Lifecycle updates preserve stable claim identity.
- Evidence history is append-only.
- Disputed, rejected, or terminal claims cannot silently become financeable.
- Creating a proof does not allocate, reserve, encumber, or settle capital.

## Judgment boundary
GenLayer MAY judge whether heterogeneous evidence substantively establishes the stated payable condition. Identity, hashing, lineage, amount bounds, and lifecycle legality remain deterministic.

## Composition
Feeds Claim Verification, Policy Envelope, Workflow Authorization, and DAA. Settlement/performance may create later proof snapshots.

## Research questions
What minimum evidence representation makes a payable portable across financing systems without turning Nomos into an oracle protocol?
