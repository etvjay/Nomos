# DAA - GenLayer Implementation

Deterministic Intelligent Contract implementing Dynamic Authority Allocation v0.1.

## Public modules/interfaces

Single contract: `Daa` in `daa.py`.

Write methods:
- `request_allocation(request_id, resource, asset, beneficiary, purpose, requested_bound, policy_hash, valid_after, valid_until)` - register REQUESTED. The caller becomes the recorded **authority source**.
- `award(request_id, allocation_id, max_authority, awarded_at)` - authority source only; bound ≤ requested_bound enforced (escalation structurally impossible); award time inside window.
- `reject_request(request_id)` / `undetermine_request(request_id)` - authority source only; neither creates authority.
- `revoke_award(allocation_id)` - authority source only.

View method (the sole downstream surface):
- `verify_authority(allocation_id, actor, resource, purpose, action_amount, at_timestamp)` - deterministic AUTHORIZE/DENY with reason code. Fail-closed order: revoked → expired → beneficiary → resource → purpose → bound.

Views: `get_request`, `get_award`.

## State machine

```
REQUESTED -> AWARDED -> REVOKED | EXPIRED(implicit)
REQUESTED -> REJECTED | UNDETERMINED   # create no authority
```

## State ownership

Awards and requests only. An award does NOT reserve capital, encumber claims,
assign replay lanes, or move value (Article V). Downstream primitives consume
`verify_authority` decisions.

## Expected errors

`DAA:`-prefixed ValueError/UserError: unknown ids, duplicates, empty fields,
zero/malformed bounds, inverted windows, non-authority-source operations,
bound escalation, awards outside validity windows, terminal-state mutations,
malformed amounts/timestamps in verify_authority.

## Security assumptions

- The authority source is whoever calls `request_allocation`; composition
  layers must ensure that caller actually holds authority over the resource.
- Beneficiary/actor addresses compare case/prefix-insensitively.
- Qualitative mandate interpretation belongs upstream (Policy Envelope);
  v0.1 expresses allocation purely through deterministic predicates.

## How to run tests

```bash
python tools/nomos_run_vectors.py primitives/daa/implementations/genlayer/daa.py --vectors primitives/daa/vectors/v0.1.json
python -m pytest primitives/daa/implementations/genlayer/tests/ -v
```

11 canonical vectors + 4 direct tests (authority-source gating).

## What remains unsupported

Qualitative mandate interpretation inside the primitive, underwriting/ranking,
any capital effects, deployment receipts, and independent-partner convergence
evidence do not exist yet.
