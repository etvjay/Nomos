# PPA Custody Adapter — Specification

## Scope

This primitive is a **testnet-only custody-mechanics slice** for the PPA
composition. It demonstrates that an already-EXECUTED PPA Core consequence can
authorize an external ERC-20 custody settlement without giving custody any
authority over PPA policy, balances, or judgment.

The only asset in scope is `Nomos Test Asset` (`NTEST`), an 18-decimal ERC-20
fixture deployed by the same test operator. `NTEST` is not USDC, is not a
stablecoin, has no external backing, and carries no economic claim.

Out of scope: USDC, CGT, bridges (LayerZero/Hyperlane), a frontend, production
custody, Phase 2 migration, and any change to PPA Core or the Receipt/Proposal
Adapter.

## Components

| Component | Environment | Responsibility |
| --- | --- | --- |
| `NomosTestAsset` | EVM (Bradbury Phase 1) | Minimal owner-minted ERC-20 fixture. |
| `NomosCustodyVault` | EVM (Bradbury Phase 1) | Holds NTEST, stores proposal-bound intents, executes exact-intent settlements, records refusals. |
| `PPACustodyAuthorizer` | GenLayer (Bradbury Phase 1) | Reads the live PPA Core consequence/payment/account, revalidates the EXECUTED binding, and is the vault's only authorization caller. |

The components are independently deployed and independently fingerprinted.
There is no upgrade proxy and no shared storage.

## Authority order

```text
PPA Core consequence (EXECUTED + payment SETTLED)
        |
        v
PPACustodyAuthorizer (deterministic read + revalidation)
        |
        v  EthSend authorize(proposal_id, token, recipient, amount, expires_at)
NomosCustodyVault (immutable intent)
        |
        v  permissionless settle(proposal_id, token, recipient, amount)
NTEST transfer to the exact Core-bound recipient
```

The vault does not read PPA Core. The authorizer does not hold or move tokens.
Core does not know the vault exists. The settlement execution is deliberately
separate from the authorization decision:

- **Authorization** is Core-bound and restricted to the authorizer contract.
- **Execution** is permissionless, but it can only execute an already-stored
  intent and cannot change token, recipient, or amount.

This separation lets an independent operator (or an auditor) execute the exact
authorized transfer without granting that operator any authority to choose a
different one. It also makes the exact-binding refusals observable on-chain.

## GenLayer authorizer interface

### `initialize(owner, core_address, adapter_address, vault_address, token_address, currency, max_ttl_seconds)`

- `owner`: GenLayer address allowed to change the asset registry, max TTL, and
  authorizer pause flag.
- `core_address`: live PPA Core. Immutable after initialization.
- `adapter_address`: the approved PPA Receipt/Proposal Adapter. The consequence
  `adapter_caller` must equal this address. Immutable after initialization.
- `vault_address`: custody vault. Immutable after initialization.
- `token_address`: ERC-20 address for `currency`.
- `currency`: Core account currency string, exactly `NTEST` for this slice.
- `max_ttl_seconds`: upper bound for a custody intent lifetime, 1..604800.

### `preview_authorization(proposal_id) -> object` (view)

Reads `Core.get_consequence(proposal_id)`, then the bound payment and account.
Returns `AUTHORIZED`, `REJECTED`, or `UNDETERMINED` with a reason code and the
exact token/recipient/amount it would authorize. This view never calls EVM and
never creates authority. It is the local/audit surface for the Core-side
decision.

### `authorize_settlement(proposal_id, ttl_seconds) -> object` (write, owner-only)

1. Re-runs the same Core-side validation as `preview_authorization`.
2. Refuses if the authorizer is paused or the intent is already
   authorized/settled in this authorizer. A paused refusal is persisted as
   `REJECTED_AUTHORIZER_PAUSED`; a replay refusal is returned as
   `REJECTED_REPLAY` without overwriting the existing `AUTHORIZED`/`SETTLED`
   record or emitting another message.
3. Calls `vault.authorize(proposal_id, token, recipient, amount, expires_at)`
   through `gl.evm` `EthSend`. The vault atomically enforces its pause flag,
   token allowlist, recipient/amount/expiry checks, and exact-intent rules when
   the message executes.
4. Persists `AUTHORIZED` with `execution = "PENDING_FINALITY"` after the EVM
   message is emitted. It cannot observe the vault's later execution result; a
   local send failure is persisted as `REJECTED_EVM_AUTHORIZE_FAILED`. The vault
   record, not this record, is the authority for whether an intent exists.
5. Does not call `settle`. The vault's exact-intent `settle` is a separate,
   permissionless execution step.
6. Finality delay is material. The message executes at finality, not at
   acceptance, so `ttl_seconds` must be long enough to cover the appeal window
   plus execution. A TTL that expires before the message executes yields a
   vault-side `VAULT_INVALID_EXPIRY` refusal and no intent.

### Configuration views/writes

- `register_asset(currency, token_address)` — owner-only, adds one
  currency-to-token mapping; refuses a different token for an already-registered
  currency. `initialize` already registers the configured currency.
- `set_max_ttl(ttl_seconds)` — owner-only, 1..604800.
- `set_paused(paused)`, `pause()`, `unpause()` — owner-only authorizer pause.
  Existing vault intents remain settleable; the vault pause is the stronger gate.
- `get_authorization(proposal_id)` — persisted authorization/refusal record, or
  `{"status": "NONE"}`.
- `get_config()` — owner, core, adapter, vault, configured currency/token, max
  TTL, paused, self address, and creation time.
- `get_asset(currency)` — token for a registered currency, or a raise.

## Vault interface

### `authorize(proposal_id, token, recipient, amount, expires_at)` — only authorizer

Checks, in order:

1. caller equals `authorizer` (revert `VAULT_CALLER_NOT_AUTHORIZER` otherwise);
2. vault is not paused (`VAULT_PAUSED`);
3. token is allowlisted (`VAULT_TOKEN_NOT_ALLOWED`);
4. proposal id is non-empty, recipient is non-zero, amount is non-zero;
5. expiry is strictly in the future (`VAULT_INVALID_EXPIRY`);
6. no existing `AUTHORIZED`/`SETTLED`/`EXPIRED` intent for the proposal
   (`VAULT_INTENT_EXISTS`, `VAULT_INTENT_ALREADY_SETTLED`,
   `VAULT_INTENT_EXPIRED`).

A prior `REFUSED` authorization may be replaced by a new `authorize` call. A
successful call stores the exact intent and emits `Authorized`. A refused call
stores `REFUSED` with the reason and emits `AuthorizationRefused`.

The vault does **not** check its token balance at authorization time. Balance is
a settlement-time condition; authorizing an intent that is temporarily
underfunded does not move anything.

### `settle(proposal_id, token, recipient, amount)` — permissionless

Checks, in order:

1. intent exists (`VAULT_INTENT_NOT_FOUND`);
2. intent is not `SETTLED` (`VAULT_INTENT_ALREADY_SETTLED`);
3. intent is not `EXPIRED` (`VAULT_INTENT_EXPIRED`);
4. vault is not paused (`VAULT_PAUSED`);
5. token is allowlisted (`VAULT_TOKEN_NOT_ALLOWED`);
6. supplied token equals the authorized token (`VAULT_TOKEN_MISMATCH`);
7. supplied recipient equals the authorized recipient
   (`VAULT_RECIPIENT_MISMATCH`);
8. supplied amount equals the authorized amount (`VAULT_AMOUNT_MISMATCH`);
9. `block.timestamp < expires_at` (`VAULT_INTENT_EXPIRED`);
10. custody balance covers the amount (`VAULT_INSUFFICIENT_CUSTODY`).

On success, the vault records `SETTLED`, before/after custody and recipient
balances, settler, and timestamp, then transfers exactly `amount` to
`recipient`. On a refusal, it records `lastReasonCode` and increments `attempts`;
the intent remains `AUTHORIZED` unless the refusal is expiry, in which case it
becomes terminal `EXPIRED`. No refusal moves tokens.

### Owner/custody surface

- `deposit(token, amount)` — pulls an allowlisted token from the caller.
- `withdraw(token, to, amount)` — owner-only emergency withdrawal; emits
  `EmergencyWithdraw`. It can make outstanding intents underfunded; that is
  recorded as `VAULT_INSUFFICIENT_CUSTODY` at settlement.
- `setAuthorizer(address)` — owner-only; the rotation is emitted. Intents on the
  old authorizer remain valid; the new authorizer cannot create new intents
  until it is used.
- `allowToken(address, bool)` — owner-only. Disabling a token blocks new
  authorizations and settlements of intents for that token.
- `setPaused(bool)` — owner-only. Pausing blocks new authorizations and
  settlements.
- `getSettlement(proposal_id)` — full record.
- `custodyBalance(token)` — current vault token balance.
- `authorizer()`, `owner()`, `paused()`, `allowedTokens(token)`.

## Canonical refusal vocabulary

Authorizer (persisted):

- `REJECTED_INVALID_PROPOSAL_ID`
- `REJECTED_INVALID_TTL`
- `REJECTED_UNKNOWN_ASSET`
- `REJECTED_CORE_UNAVAILABLE`
- `REJECTED_NO_CONSEQUENCE`
- `REJECTED_CONSEQUENCE_NOT_EXECUTED`
- `REJECTED_WRONG_ADAPTER`
- `REJECTED_PAYMENT_NOT_SETTLED`
- `REJECTED_PAYMENT_BINDING`
- `REJECTED_ACCOUNT_NOT_ACTIVE`
- `REJECTED_CURRENCY_MISMATCH`
- `REJECTED_POLICY_VERSION`
- `REJECTED_AMOUNT`
- `REJECTED_RECIPIENT`
- `REJECTED_REPLAY`
- `REJECTED_AUTHORIZER_PAUSED`
- `REJECTED_EVM_AUTHORIZE_FAILED`
- `UNDETERMINED_DEPENDENCY`

`REJECTED_CUSTODY_PAUSED`, `REJECTED_TOKEN_NOT_ALLOWED`, and
`UNDETERMINED_VAULT_UNAVAILABLE` are reserved v0.1 vocabulary and are not
emitted: the authorizer does not preflight the vault with EVM view calls. The
vault enforces pause/token/expiry atomically when the authorization message
executes; its refusal is recorded on the vault, not in the authorizer record.

Owner-only calls raise `Custody: caller is not owner` and do not persist a
refusal record. `REJECTED_EXPIRED` is reserved for a later capability version;
v0.1 derives expiry from the Core `created_at` plus the requested TTL and does
not emit it.

Vault:

- `VAULT_CALLER_NOT_AUTHORIZER` (revert)
- `VAULT_PAUSED`
- `VAULT_TOKEN_NOT_ALLOWED`
- `VAULT_INVALID_PROPOSAL_ID`
- `VAULT_INVALID_RECIPIENT`
- `VAULT_INVALID_AMOUNT`
- `VAULT_INVALID_EXPIRY`
- `VAULT_INTENT_EXISTS`
- `VAULT_INTENT_NOT_FOUND`
- `VAULT_INTENT_ALREADY_SETTLED`
- `VAULT_INTENT_EXPIRED`
- `VAULT_TOKEN_MISMATCH`
- `VAULT_RECIPIENT_MISMATCH`
- `VAULT_AMOUNT_MISMATCH`
- `VAULT_INSUFFICIENT_CUSTODY`
- `VAULT_TRANSFER_FAILED`

## Core binding

The authorizer accepts a consequence only when all of the following hold:

- consequence `status == "EXECUTED"` and `reason_code == "EXECUTED"`;
- consequence `payment_status == "SETTLED"`;
- consequence `adapter_caller` equals the configured approved Adapter;
- consequence `proposal_id` equals the requested id;
- payment `status == "SETTLED"`;
- payment `payment_id`, `proposal_id`, and `decision_id` match the consequence;
- payment `actor == "adapter:" + adapter_address`;
- payment `memo == "proposal:" + proposal_id`;
- payment `to` and `amount` equal consequence `requested_recipient` and
  `requested_amount`;
- payment `account_id` equals the referenced account;
- account `status == "ACTIVE"`;
- account `rules.currency` equals the configured currency;
- the currency maps to the configured token address;
- the consequence amount is a positive decimal integer and the recipient is a
  valid 20-byte address;
- any account `rules.policy_version`, if present, equals the consequence
  `policy_version`.

The Core-side read is the only source of truth for these fields. A caller cannot
supply them; `preview_authorization` takes only the proposal id.

**Amount convention (v0.1):** the PPA `requested_amount` string is interpreted
as the custody token's base-unit amount. `NTEST` has 18 decimals, so a live
phase-1 PPA amount of `100000000000000000000` authorizes a transfer of 100
NTEST. An asset whose PPA amount is expressed in human decimal units requires a
decimals-aware adapter in a later capability version; v0.1 does not scale.

## Expiry

The Core consequence has no custody expiry. The authorizer therefore assigns a
fresh, bounded custody expiry at authorization time:

```text
expires_at = authorizer_now + ttl_seconds
```

`ttl_seconds` is owner-supplied and must be `1..max_ttl_seconds` (max 604800).
The vault stores and enforces the exact expiry. A stale intent can never settle
after expiry. Expiry is terminal for that intent; a new consequence/proposal id
is required for a new settlement.

## Non-atomicity with Core

Core has already moved its internal ledger when it records `EXECUTED`. The
external vault settlement happens later and can refuse (paused, insufficient
custody, expiry, transfer failure). Core is **not** rolled back. A custody
refusal therefore leaves Core's internal payment `SETTLED` while the external
balance is unchanged. This gap is a declared limitation, not a hidden success:

- Core remains the policy/ledger authority.
- The vault remains the external-custody authority.
- The evidence records both sides and never treats the Core `SETTLED` status as
  proof of an external transfer.
- Reconciliation is a separate operation; this primitive does not mutate
  historical confirmed Core truth to simulate recovery.

## Evidence classification

- `NTEST` custody mechanics on Bradbury Phase 1: `TESTNET_OBSERVED` only after
  independent JSON-RPC readback.
- External USDC custody: `NOT_ESTABLISHED`.
- Bridge settlement: `NOT_IMPLEMENTED`.
- Production custody or real economic value: `NOT_CLAIMED`.
