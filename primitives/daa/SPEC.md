# Dynamic Authority Allocation (DAA) — Canonical Specification

Status: RESEARCHING
Version: 0.1.0

## Problem
Determine which actor receives bounded authority over which scarce capital, for which claim or financing purpose, under which terms and constraints.

## Primitive meaning
DAA produces an `AllocationAward`: a bounded authority decision. It does not reserve capital or move funds.

## Core invariants
- Award binds exact `claimId`, evaluated evidence/proof hash, policy hash, beneficiary, pool, amount bounds, and validity window.
- Award amount cannot exceed requested or available allocatable capacity.
- Finalized decision is immutable; changes require a new version/identifier.
- `REJECTED` or `UNDETERMINED` reserves nothing.
- DAA does not imply exclusivity, encumbrance, commitment, or settlement.

## Judgment boundary
GenLayer is the reference allocator where eligibility, comparative ranking, risk classification, qualitative mandates, contradictory evidence, or conditional requirements require validator-mediated judgment.

## Composition
Consumes verified claims, policy and workflow authority. Feeds Pact binding, Claim Encumbrance, Capital Commitment and later execution authorization.
