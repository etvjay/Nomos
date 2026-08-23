# Gaia — GenLayer Implementation

Deterministic Intelligent Contract implementing the Gaia exception plane v0.1.

## Public modules/interfaces

Single contract: `Gaia` in `gaia.py`.

Write methods:
- `open_case(case_id, category, subject_ref, facts_json)` — open an exception case. Categories are declared vocabulary: settlement-mismatch, delivery-mismatch, duplicate-execution, stale-evidence, unauthorized-action, reconciliation-failure, other.
- `classify_case(case_id, classification_id, obligations_json)` — attach 1–8 bounded rectification obligations (refund / retry / provide_evidence / correct_usage_record / reconcile / manual_review). Obligation ids derive deterministically as `<classification_id>-O<index>`. OPEN → CLASSIFIED.
- `discharge_obligation(obligation_id, evidence_hash)` — explicit satisfaction with auditable evidence.
- `waive_obligation(obligation_id, waiver_note)` — explicit waiver with recorded justification.
- `resolve_case(case_id, resolution_evidence_hash)` — CLASSIFIED → RESOLVED (terminal) once **every** obligation is dispositioned.

Views: `get_case`, `get_obligation`.

## Core guarantees

- Failure does not create authority: Gaia prescribes remedies but executes nothing.
- Historical truth append-only: facts, obligations, and dispositions are never rewritten; RESOLVED is terminal.
- No silent resolution: the completeness gate scans all obligations bound to the case.
- Ordinary deterministic rejection never auto-creates a case — cases are explicitly opened.

## State ownership

Cases and obligations only. No capital movement, no authorization bypass, no
mutation of other primitives' history. Remedy execution loops back through
ordinary Workflow Authorization downstream.

## Expected errors

`Gaia:`-prefixed ValueError/UserError for unknown/duplicate ids, unknown
categories or obligation types, malformed/oversized JSON, double classification,
double disposition, discharge without evidence, waive without note, premature
resolution, and mutations of resolved cases.

## How to run tests

```bash
python tools/nomos_run_vectors.py primitives/gaia/implementations/genlayer/gaia.py --vectors primitives/gaia/vectors/v0.1.json
```

9 canonical vectors covering lifecycle, classification gating, disposition
evidence binding, resolution completeness, terminality, and authority absence.

## What remains unsupported

In-contract LLM classification of ambiguous exceptions (v0.1 accepts bounded
caller-supplied classifications; an LLM layer may compose upstream), remedy
execution, deployment receipts, and independent-partner convergence evidence.
