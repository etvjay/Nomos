# Workflow Authorization - GenLayer Implementation

Deterministic Intelligent Contract implementing Workflow Authorization v0.1
(Path + Pact).

## Public modules/interfaces

Single contract: `WorkflowAuthorization` in `workflow_authorization.py`.

Write methods:
- `grant_path(path_id, principal, agent, purpose_scope, max_per_action, asset, valid_after, valid_until)` - create standing bounded delegated authority. Self-delegation rejected.
- `revoke_path(path_id)` - ACTIVE → REVOKED (permanent).
- `propose_pact(pact_id, path_id, workflow_ref, terms_json, proposed_at)` - propose a specific economic relation bound to the exact workflow reference. Path must be ACTIVE and `proposed_at` inside its window.
- `accept_pact(pact_id)` - **only the Path principal** may accept; Path must be ACTIVE.
- `void_pact(pact_id)` - terminal void for non-executed pacts.
- `execute_pact(pact_id, action_amount, at_timestamp)` - deterministic authorization gate. Returns AUTHORIZE (pact becomes EXECUTED, terminal) or a DENY decision with reason code that mutates nothing.

View methods: `get_path`, `get_pact`.

## Decision semantics

`execute_pact` gate order (fail-closed): pact ACCEPTED? → path ACTIVE? →
in-window? → amount ≤ max_per_action? Any failure returns
`{decision: DENY, reason_code: ...}` without mutating state. AUTHORIZE marks
the pact EXECUTED (one-time use). This primitive never moves capital.

## State ownership

Path standing-authority objects and Pact lifecycle state. No capital,
no replay lanes, no settlement authority (Article V separation).

## Expected errors

`WorkflowAuthorization:`-prefixed ValueError/UserError for unknown ids,
duplicates, empty/malformed fields, oversized terms (>4096 bytes),
self-delegation, acceptance by non-principal, proposals on dead/expired paths,
and reuse of executed pacts.

## Security assumptions

- Principal identity is an address string; comparisons normalize case and an
  optional `0x` prefix (EIP-55 safe).
- v0.1 has no on-chain verification that `principal`/`agent` are real account
  addresses - composition layers must bind them to wallet identities.
- Substantive purpose-fit ("is this payment really treasury-scope?") is out of
  scope: compose Policy Envelope's `interpret_clause` before proposing Pacts.

## How to run tests

```bash
python tools/nomos_run_vectors.py primitives/workflow-authorization/implementations/genlayer/workflow_authorization.py --vectors primitives/workflow-authorization/vectors/v0.1.json
python -m pytest primitives/workflow-authorization/implementations/genlayer/tests/ -v
```

10 canonical vectors (sender-neutral flows) + 5 direct tests covering the
principal-only acceptance gate, expiry-at-proposal, revocation blocking, and
double-execution rejection.

## What remains unsupported

Purpose-fit judgment, multisig/quorum acceptance, capital effects, deployment
receipts, and independent-partner convergence evidence do not exist yet.
