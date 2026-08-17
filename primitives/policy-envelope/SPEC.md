# Policy Envelope — Canonical Specification

Status: RESEARCHING
Version: 0.1.0

## Problem
Express bounded admissibility and spend/financing constraints without conflating policy with authority or allocation.

## Primitive meaning
A Policy Envelope is a deterministic-first constraint object that defines what actions are admissible and, where necessary, a bounded natural-language mandate requiring judgment.

## Core invariants
- Hard limits always dominate judgment.
- Policy approval does not imply delegation, allocation, agreement, commitment, or settlement.
- Time, asset, amount, actor, target, and capacity constraints are deterministic where expressible.
- `UNDETERMINED` never becomes implicit approval.

## Judgment boundary
GenLayer MAY interpret declared mandate clauses that cannot be faithfully reduced to deterministic predicates. The structured result is subordinate to hard constraints.

## Composition
Consumed by Workflow Authorization, DAA, Financial Contract, and corrective workflows.
