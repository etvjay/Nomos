# Mandate Allocation — GenLayer Implementation

Deterministic Intelligent Contract implementing Mandate Allocation v0.1.

## Public modules/interfaces

Single contract: `MandateAllocation` in `mandate_allocation.py`.

Write methods:
- `register_mandate(mandate_id, doc_hash, max_total_exposure, asset, allowed_classes_json)` — bind mandate constraints. The qualitative mandate document is referenced by hash; its interpretation happens upstream (Policy Envelope).
- `evaluate_opportunity(evaluation_id, mandate_id, opportunity_ref, opportunity_class, requested_amount, at_timestamp)` — deterministic advisory gate: class membership → exposure capacity → ELIGIBLE/INELIGIBLE with reason code. ELIGIBLE consumes advisory exposure; INELIGIBLE attempts are recorded and consume nothing.
- `supersede_evaluation(old, new, note)` — lineage-preserving replacement.

Views: `get_mandate`, `get_evaluation`, `committed_exposure`.

## Advisory-only guarantee

A result is NOT authority, commitment, or encumbrance and cannot move value
(Article V). `committed_exposure` is bookkeeping *inside this primitive* — it
reserves nothing in any pool. DAA must independently create any downstream
authority grant.

## Judgment boundary

NONE in-contract for v0.1. Comparative/qualitative ranking composes upstream:
Claim Verification judges the evidence, Policy Envelope's interpret_clause
judges the qualitative mandate, and their bounded results feed evaluation as
deterministic inputs. This keeps convergence EXACT while preserving the LLM
judgment path through composition — GenLayer's core used meaningfully without
letting judgment move money.

## Expected errors

`MandateAllocation:`-prefixed ValueError/UserError for unknown/duplicate ids,
empty fields, malformed/oversized JSON, zero or malformed amounts, self-supersede,
successor-already-exists, superseding non-EVALUATED records.

## How to run tests

```bash
python tools/nomos_run_vectors.py primitives/mandate-allocation/implementations/genlayer/mandate_allocation.py --vectors primitives/mandate-allocation/vectors/v0.1.json
```

9 canonical vectors: registration, eligibility gates, exposure accounting,
id uniqueness (including auditable ineligible attempts), supersession lineage.

## What remains unsupported

In-contract comparative ranking, per-opportunity asset binding (upstream
composed), deployment receipts, and independent-partner convergence evidence.
