# DAL - GenLayer Implementation

Deterministic Intelligent Contract implementing Dynamic Authorization Lanes v0.1.

## Public modules/interfaces

Single contract: `Dal` in `dal.py`.

Write methods:
- `open_lane(issuer, domain_id, expiry_window)` - open a fresh replay domain; one lane per (issuer, domain_id); revoked lanes cannot be reopened.
- `exercise(issuer, domain_id, nonce, at_timestamp)` - authorize one execution inside the lane's domain. AUTHORIZE (nonce consumed atomically) or DENY with reason code (`NONCE_REUSED`, `NONCE_INVALID`, `LANE_REVOKED`, `LANE_EXPIRED`). Denials mutate nothing.
- `revoke_lane(issuer, domain_id)` - explicit revocation.

View: `get_lane`.

## Replay model

Expected nonce starts at 1 and advances exactly once per AUTHORIZE.
Supplied < expected → NONCE_REUSED (replay). Supplied > expected or 0 →
NONCE_INVALID (gap). Fail-closed order: status → expiry → nonce.

## State ownership

Replay domains only. DAL deliberately exposes NO balances/capacity/policy -
replay independence must never be mistaken for independence of shared
economic state (Article V).

## Expected errors

`DAL:`-prefixed ValueError/UserError for unknown lanes, duplicate opens,
reopen-after-revoke, empty ids, malformed timestamps.

## How to run tests

```bash
python tools/nomos_run_vectors.py primitives/dal/implementations/genlayer/dal.py --vectors primitives/dal/vectors/v0.1.json
```

10 canonical vectors: nonce advancement, stale/future/zero rejection,
same-issuer domain independence, scoped revocation, expiry fail-closed.

## What remains unsupported

Any shared economic state, authority creation, capital effects, deployment
receipts, and independent-partner convergence evidence do not exist yet.
