# Proof of Payable - Canonical Specification

Status: SPECIFIED
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
NONE for the v0.1 canonical slice. Identity, hashing, lineage, amount bounds, and lifecycle legality are deterministic. Whether heterogeneous evidence substantively establishes the stated payable condition is a separate judgment that belongs to Claim Verification (SEMANTIC) consuming these claim/proof snapshots.

### v0.1 classification change (Article XVI record)
v0.1-draft of this spec declared `judgmentBearing: true` (SEMANTIC). The accepted v0.1 narrows the primitive to its deterministic core: stable claim identity, append-only evidence lineage keyed by globally unique `proofId`, explicit lifecycle state machine with immutable terminal states, and no capital effects.

Rationale: the implemented canonical surface contains no judgment; EXACT convergence is the honest mode and makes independent-partner reproduction mechanically checkable. Compatibility: additive - no prior release consumed a judgment-bearing pop surface; downstream judgment consumers bind to Claim Verification, unchanged.

## Composition
Feeds Claim Verification (which judges over pop evidence snapshots), Policy Envelope, Workflow Authorization, and DAA. Settlement/performance may create later proof snapshots.

## Research questions
What minimum evidence representation makes a payable portable across financing systems without turning Nomos into an oracle protocol? v0.1 answer: caller-supplied `proofHash` bindings over append-only lineage; remote fetching stays out of scope.
