# PPA Receipt / Proposal Adapter - GenLayer Implementation

The adjudication/proposal boundary of the PPA composition product.

## Public modules/interfaces

`PPAReceiptAdapter`. Public surface in `primitives/ppa-receipt-adapter/CAPABILITY.json`:
`initialize`, `register_adjudicator`, `revoke_adjudicator`, `get_adjudicator`,
`submit_decision_receipt`, `get_receipt`, `admit_proposal`, `get_proposal`,
`dispatch_proposal`.

## Caller model

At the Adapter, `gl.message.sender_address` is the **calling adjudicator**. The
Adapter authenticates that address against its own registry plus a pinned
authority fingerprint. A JSON `source_contract` field is never provenance —
proven by the spoof case in `convergence/reports/CALLER-IDENTITY-SPIKE.json`.

## No balance authority

The Adapter holds no ledger state, cannot move funds, and cannot widen account
policy, amount, or recipient. `dispatch_proposal` emits to PPA Core, which
revalidates everything independently.

## Asynchronous boundary

`dispatch_proposal` uses `gl.get_contract_at(...).emit(on='accepted')`. Core
executes in a later transaction, so the Adapter may never observe the outcome.
The consequence audit record therefore lives in Core.

## State ownership

Owns the adjudicator registry, receipts with origin provenance, and admitted
proposals. Nothing else.

## Expected errors

`REJECTED_SOURCE_NOT_REGISTERED`, `REJECTED_SOURCE_FINGERPRINT_MISMATCH`,
`REJECTED_UNDETERMINED`, `REJECTED_EXPIRED`, `REJECTED_PROPOSAL_REPLAY`,
`REJECTED_POLICY`, `REJECTED_AMOUNT`, `REJECTED_RECIPIENT`.

## Security assumptions

Origin binding establishes **attribution, not correctness**. A registered but
compromised adjudicator can still emit `ACCEPTED` for a false conclusion. See
`primitives/ppa/DECISION_BOUNDARY.md`.

## How to run tests

    source ~/nomos-venv312/bin/activate
    python -m pytest primitives/ppa-receipt-adapter/implementations/genlayer/tests/ -q
    python -m pytest tests/split/ -q      # cross-contract

Requires glsim on :4000. Discovery uses `contracts/ppa_receipt_adapter.py`.

## What remains unsupported

The real web/LLM adjudication producer, external token custody, bridges, frontend.
