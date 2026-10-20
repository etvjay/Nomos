# PPA Core - GenLayer Implementation

The final deterministic consequence boundary of the PPA composition product.

## Public modules/interfaces

`PPACore` (GenLayer Intelligent Contract). Public surface is declared in
`primitives/ppa-core/CAPABILITY.json`: `initialize`, `register_adapter`,
`revoke_adapter`, `get_adapter`, `create_account`, `update_rules`, `get_account`,
`deposit`, `withdraw`, `send`, `get_payment`, `register_attestation`,
`revoke_attestation`, `get_attestation`, `execute_proposal`, `get_consequence`.

## Caller model

At Core, `gl.message.sender_address` is the **calling contract** — for this
contract that is the Receipt / Proposal Adapter. The original EOA is consumed at
the previous hop. Evidence: `convergence/reports/CALLER-IDENTITY-SPIKE.json`.

`execute_proposal` therefore authenticates the **Adapter**, never a JSON field.

## Asynchronous boundary

The Adapter emits; Core executes in a **later transaction**. Core re-reads and
revalidates policy, recipient, amount, attestation, capital, replay, expiry and
account status from its own state. It does not trust Adapter-supplied assertions.

## Refusal semantics

Core **returns** a consequence record rather than raising. A rejecting raise
reverts the emitted transaction and leaves no observable artifact, making a
refusal indistinguishable from an emit that never happened.

## State ownership

Owns the ledger, payments, attestations, the adapter registry, and consequence
audit records (identifiers and hashes only — no receipt or evidence payloads).
Does **not** own adjudication, receipts, or any balance authority elsewhere.

## Expected errors

`REJECTED_CALLER_NOT_REGISTERED_ADAPTER`, `REJECTED_ADAPTER_REVOKED`,
`REJECTED_PROPOSAL_REPLAY`, `REJECTED_POLICY`, `REJECTED_AMOUNT`,
`REJECTED_RECIPIENT`, `REJECTED_CAPITAL`, `REJECTED_ATTESTATION`,
`REJECTED_EXPIRED`. Every attempt yields exactly one auditable outcome.

## Security assumptions

Registered adapters are trusted for *identity* only, never for *correctness*.
Core independently revalidates every economic gate. An Adapter cannot widen
amount, recipient, or policy.

## How to run tests

    source ~/nomos-venv312/bin/activate
    python -m pytest primitives/ppa-core/implementations/genlayer/tests/ -q
    python -m pytest tests/split/ -q      # cross-contract

Requires glsim on :4000. Contract discovery uses `contracts/ppa_core.py`.

## What remains unsupported

Adjudication, external token settlement, invoice/dispute/delegation extensions,
bridges, frontend.
