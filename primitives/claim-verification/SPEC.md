# Claim Verification - Canonical Specification

Status: RESEARCHING
Version: 0.1.0

## Problem
Determine whether evidence substantively supports a claimed economic fact when structural validity alone is insufficient.

## Primitive meaning
Claim Verification produces a bounded, evidence-linked verification result for a stable claim or proof snapshot.

## Core invariants
- Verification binds the exact `claimId` and evaluated `proofHash`.
- Verification does not mutate the claim.
- `UNDETERMINED` is not approval.
- Contradictory evidence must remain observable.
- Verification does not allocate or move capital.

## Judgment boundary
GenLayer evaluates admissible external/heterogeneous evidence and returns structured results such as `VERIFIED`, `CONFLICTED`, `INSUFFICIENT`, plus evidence commitments and bounded findings.

## Composition
Consumes Proof of Payable and feeds Policy Envelope, Workflow Authorization, DAA, Financial Contract, and Gaia.
