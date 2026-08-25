# Gaia - Exception, Reconciliation & Rectification

Status: SPECIFIED
Version: 0.1.0

## Problem
Turn economically meaningful exceptions, disputes, mismatches, and reconciliation failures into explicit resolution workflows without granting hidden administrative authority or rewriting history.

## Primitive meaning
Gaia is a cross-cutting exception plane. A GaiaCase classifies exceptional state and may produce one or more RectificationObligations such as refund, retry, provide evidence, correct a usage record, reconcile, or manual review.

## Core invariants
- Failure does not create authority.
- Gaia may prescribe a remedy but may not bypass Workflow Authorization required to perform it.
- Historical confirmed truth is append-only; rectification creates compensating/new state rather than rewriting prior events.
- Ordinary deterministic rejection does not automatically create a Gaia case.
- A case cannot resolve while required obligations remain undispositioned.
- Resolution evidence is explicit and auditable.

## Judgment boundary
GenLayer MAY classify ambiguous exceptions, compare contradictory evidence, determine appropriate bounded rectification obligations, and judge whether evidence satisfies resolution conditions. Execution of any remedy remains separately authorized and deterministic where economic state changes.

## Composition
Reachable from evidence, Workflow Authorization, DAA, encumbrance, commitment, settlement, and Financial Contract state. Rectification loops back through normal authorization before execution.
