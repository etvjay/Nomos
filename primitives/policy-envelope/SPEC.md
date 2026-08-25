# Policy Envelope - Canonical Specification

Status: SPECIFIED
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
NONE for the v0.1 canonical decision. Hard-limit evaluation (amount, asset, window, capacity) is deterministic and dominant. Declared mandate clauses MAY be interpreted via a bounded non-deterministic surface (interpret_clause) whose structured result - ADMIT/DENY/UNDETERMINED - is subordinate to hard constraints and can never mutate accounting state or create authority. Convergence is therefore EXACT: equivalence binds the deterministic decision fields; interpretation prose is non-canonical.

### v0.1 classification change (Article XVI record)
v0.1-draft declared judgmentBearing=true (SEMANTIC). Accepted v0.1 narrows the canonical decision to deterministic hard limits with a subordinate, non-authoritative interpretation surface. Compatibility: additive; no prior release consumed a SEMANTIC policy surface.

## Composition
Consumed by Workflow Authorization, DAA, Financial Contract, and corrective workflows.
