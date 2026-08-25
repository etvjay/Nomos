# Claim Encumbrance - Canonical Specification

Status: SPECIFIED
Version: 0.1.0

## Problem
Prevent the same underlying economic claim from supporting more active financing than its financeable amount.

## Primitive meaning
Claim Encumbrance is deterministic claim-level capacity accounting keyed by stable `claimId`.

## Core invariants
- `sum(activeEncumbrances(claimId)) <= financeableAmount(claimId)`.
- Encumbrance is keyed by stable claim identity, not proof snapshot hash.
- Reserve/commit/release/settle transitions are atomic and auditable.
- Duplicate or conflicting reservations cannot over-encumber a claim.
- Evidence changes do not reset encumbrance.

## Judgment boundary
NONE. GenLayer implementation is mandatory, but the accounting and conflict checks remain deterministic. Any upstream judgment about whether two records represent the same claim belongs to Claim Verification or another explicitly declared adjudication step.

## Composition
Consumes stable claims and DAA awards; feeds Capital Commitment and settlement/financial-contract execution.
