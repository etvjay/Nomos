# Capital Commitment - Canonical Specification

Status: SPECIFIED
Version: 0.1.0

## Problem
Distinguish permission to receive capital from capital that has actually been reserved and made unavailable to competing uses.

## Primitive meaning
Capital Commitment is deterministic reservation of economically backed capacity against an allocation.

## Core invariants
- Commitment amount is backed by reserved pool/vault capacity.
- Active commitment capacity cannot be simultaneously withdrawn or reallocated.
- Commitment binds exact allocation, beneficiary, asset, amount, pool, and validity.
- Expiry/release restores capacity exactly once.
- Commitment does not itself grant replay/execution authority.

## Judgment boundary
NONE for reservation/accounting. Upstream conditions-precedent judgment may be supplied by Policy Envelope, Claim Verification, DAA, or Financial Contract, but commitment state changes remain deterministic.

## Composition
Consumes DAA award, Workflow Authorization/Pact, and Claim Encumbrance state; feeds DAL and settlement.
