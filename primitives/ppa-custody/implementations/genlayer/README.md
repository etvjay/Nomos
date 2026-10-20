# PPA Custody Authorizer — GenLayer Implementation

Deterministic bridge from an EXECUTED PPA Core consequence to an EVM custody
intent. `JUDGMENT_BOUNDARY = NONE`; there is no LLM, web fetch, or nondet call.

## Public modules/interfaces

`PPACustodyAuthorizer` in `ppa_custody_authorizer.py`.

Writes:

- `initialize(owner, core_address, adapter_address, vault_address, token_address, currency, max_ttl_seconds)`
- `register_asset(currency, token_address)`
- `set_max_ttl(ttl_seconds)`
- `set_paused(paused)`
- `pause()`
- `unpause()`
- `authorize_settlement(proposal_id, ttl_seconds)` — owner-only

Views:

- `preview_authorization(proposal_id)`
- `get_authorization(proposal_id)`
- `get_asset(currency)`
- `get_config()`

The EVM side lives in `../evm/src/NomosTestAsset.sol` and
`../evm/src/NomosCustodyVault.sol`. The authorizer is the vault's only
`authorize` caller; settlement execution is permissionless but exact-intent.

## Inputs and outputs

`preview_authorization` returns the exact token, recipient, amount, currency,
payment/decision ids, adapter caller, Core snapshot hash, and an expiry computed
from the configured max TTL. It never calls EVM and never writes state.

`authorize_settlement` returns `AUTHORIZED` only after the vault's
`authorize` EthSend succeeds. Core-side or vault-side refusals are persisted in
`get_authorization` with a stable `reason_code`. A missing Core or vault is
`UNDETERMINED_*`, never an authorization.

## State ownership

Owns:

- the asset registry (currency -> token address);
- the persisted authorization/refusal records;
- the owner/configuration metadata (Core, adapter, vault, max TTL, pause).

Does not own:

- PPA balances, policy, payments, or consequences;
- NTEST custody or balances (the vault owns those);
- adjudication or receipt truth (the Adapter/Producer own those);
- the vault's authorizer setting (the vault owner owns that).

## Dependencies

- Live PPA Core and the approved PPA Receipt/Proposal Adapter on Bradbury
  Phase 1.
- The deployed `NomosCustodyVault` EVM address, configured immutably at
  initialization.
- GenVM runner `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`.
- `gl.evm` `EthCall` for vault `paused`/`allowedTokens`, and `EthSend` for
  `authorize`.

## Expected errors

Caller/owner: `Custody: caller is not owner` (raises, no persisted record).

Core binding: `REJECTED_NO_CONSEQUENCE`, `REJECTED_CORE_UNAVAILABLE`,
`REJECTED_CONSEQUENCE_NOT_EXECUTED`, `REJECTED_PAYMENT_NOT_SETTLED`,
`REJECTED_WRONG_ADAPTER`, `REJECTED_PAYMENT_BINDING`,
`REJECTED_ACCOUNT_NOT_ACTIVE`, `REJECTED_CURRENCY_MISMATCH`,
`REJECTED_POLICY_VERSION`, `REJECTED_UNKNOWN_ASSET`, `REJECTED_AMOUNT`,
`REJECTED_RECIPIENT`, `REJECTED_INVALID_PROPOSAL_ID`.

Configuration/state: `REJECTED_INVALID_TTL`, `REJECTED_AUTHORIZER_PAUSED`,
`REJECTED_REPLAY`, `REJECTED_EVM_AUTHORIZE_FAILED`.

`REJECTED_CUSTODY_PAUSED`, `REJECTED_TOKEN_NOT_ALLOWED`, and
`UNDETERMINED_VAULT_UNAVAILABLE` are reserved and not emitted in v0.1. The
authorizer does not preflight the vault with EVM view calls; the vault enforces
pause, token allowlist, recipient, amount, and expiry when the authorization
message executes. A successful authorizer record has
`execution = "PENDING_FINALITY"`; the vault record is authoritative. Because
the message executes at finality, choose a TTL longer than the appeal window or
the vault will refuse with `VAULT_INVALID_EXPIRY`.

## Security assumptions

- The Core and Adapter addresses are configured by the owner at initialization
  and are immutable afterwards.
- The authorizer reads Core itself; callers supply only a proposal id and TTL.
- The EVM vault is trusted to enforce the exact intent and only the authorizer
  is trusted to create one.
- A compromised authorizer or vault owner is a custody-authority compromise; the
  vault owner can pause, rotate the authorizer, or emergency-withdraw.
- Core and external custody are non-atomic. A vault refusal does not roll back
  Core; evidence records both sides.

## How to run tests

```bash
source ~/nomos-venv312/bin/activate
python -m pytest primitives/ppa-custody/implementations/genlayer/tests/ -q
python tools/nomos_run_vectors.py \
  primitives/ppa-custody/implementations/genlayer/ppa_custody_authorizer.py \
  --vectors primitives/ppa-custody/vectors/v0.1.json
genvm-lint check \
  primitives/ppa-custody/implementations/genlayer/ppa_custody_authorizer.py
forge test --root primitives/ppa-custody/implementations/evm -vv
```

The glsim suite covers the Core-side decision and the authorizer's
`AUTHORIZED`/`PENDING_FINALITY` emission record. glsim does not execute EVM
messages, so it cannot produce a vault intent; Foundry covers the vault
mechanics and the live Phase 1 run covers the GenLayer-to-EVM join.

## What remains unsupported

USDC, CGT, bridges, Phase 2, a frontend, API authorization, production custody,
real economic value, partial settlement, fee-on-transfer/rebasing tokens, and
migration of existing PPA composition claims.
