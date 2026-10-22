# PPA Native GEN Custody — Specification

## Scope

This primitive is a **testnet-only native-GEN custody slice** for the PPA
composition. It demonstrates that an already-EXECUTED PPA Core consequence can
authorize a finalized native GEN transfer from a separately deployed custody
contract to the exact Core-bound recipient, without giving custody authority
over PPA policy, balances, or judgment.

The asset is **native GEN** on GenLayer Bradbury Phase 1: 18 decimals, `u256`
base units (wei), no token contract, and no external backing beyond the testnet
network. The custody contract holds GEN on its own ghost contract.

Out of scope: USDC, CGT, NTEST, any ERC-20, bridges (LayerZero/Hyperlane), a
frontend, production custody, Phase 2 migration, contract recipients, owner
emergency withdrawal, partial settlement, and any change to PPA Core or the
Receipt/Proposal Adapter.

This primitive does not extend or reinterpret `ppa-custody` v0.1 (the NTEST
ERC-20 mechanics slice). It is a separate deployment, a separate authority
fingerprint, and a separate capability version.

## Components

| Component | Environment | Responsibility |
| --- | --- | --- |
| PPA Core (dependency) | GenLayer Bradbury Phase 1 | Owns the internal ledger, account, payment, and consequence state. Unchanged. |
| PPA Receipt/Proposal Adapter (dependency) | GenLayer Bradbury Phase 1 | Approved consequence caller. Unchanged. |
| `PPANativeGenCustody` | GenLayer Bradbury Phase 1 | Holds native GEN, derives and persists a Core-bound intent, and emits the exact finalized native transfer. |

There is no EVM vault, no proxy, no upgrade path, and no shared storage with
`ppa-custody`.

## Authority order

```text
PPA Core consequence (EXECUTED + payment SETTLED + account GEN/ACTIVE)
        |
        v
PPANativeGenCustody.authorize(consequence_id, ttl_seconds)   [owner-gated]
        |  reads Core itself; derives recipient/amount; stores exact intent
        v
PPANativeGenCustody.settle(consequence_id, recipient, amount) [permissionless]
        |  revalidates Core; exact match; expiry/pause/replay/balance checks
        v
native GEN emit_transfer(on='finalized') to the Core-bound recipient
        |
        v
independent child-transaction and balance readback
```

`authorize` is owner-gated to prevent a third party from burning a consequence
with a hostile TTL. The owner cannot choose the recipient or amount: both are
read from the bound Core consequence and cross-checked against the settled
payment. `settle` is permissionless so an independent operator can execute the
already-authorized transfer without gaining authority to change it.

The vault does not read PPA policy and does not decide whether a payment should
exist. It consumes a consequence that Core has already recorded as `EXECUTED`.

## Native asset and value semantics

- Symbol: `GEN`; decimals: `18`; base unit: `wei`.
- The PPA amount string is interpreted as a positive wei integer in v0.1. There
  is no decimals-aware human-unit conversion.
- `deposit()` is payable. `gl.message.value` is the deposited amount; it must be
  positive. The contract records the deposit and increments `total_deposited`.
- `settle()` emits an external value transfer. GenLayer deducts the emitted
  value from the custody contract balance at emit time and credits the recipient
  when the child transaction activates.
- Protocol gas/fees are a separate budget. They are never counted as custody
  value and never reduce the transferred amount.
- `self.balance` is the custody balance of record. Accounting is reconciled as
  `total_deposited - total_emitted + total_refunded`, with no withdrawal path in
  v0.1.
- v0.1 recipients are externally-owned accounts only. Contract recipients are
  unsupported.

## Interface

### `initialize(owner, core_address, adapter_address, max_ttl_seconds)`

- `owner`: GenLayer address allowed to authorize intents, pause the vault, and
  change the max TTL. The owner cannot settle, withdraw, or choose a recipient
  or amount.
- `core_address`: live PPA Core. Immutable after initialization.
- `adapter_address`: approved PPA Receipt/Proposal Adapter. Immutable.
- `max_ttl_seconds`: upper bound for an intent lifetime, 1..604800.
- Stores `currency = "GEN"` and the initial pause/accounting state.
- One-time; a second call raises `Custody: already initialized`.

### `deposit()` — payable, permissionless

- Requires a positive `gl.message.value`.
- Stores a deposit record keyed by a monotonic sequence: sender, amount, time.
- Increments `total_deposited`.
- Does not create settlement authority.
- A paused vault still accepts deposits; pause blocks authorization and
  settlement, not funding.

### `authorize(consequence_id, ttl_seconds)` — owner-only

1. Reject an uninitialized vault, a paused vault, an invalid id, or an invalid
   TTL.
2. Read the bound Core consequence, payment, and account.
3. Require:
   - consequence `status == EXECUTED` and `reason_code == EXECUTED`;
   - consequence `payment_status == SETTLED`;
   - consequence `adapter_caller ==` the configured approved adapter;
   - payment `status == SETTLED`, bound to the same proposal, payment, decision,
     recipient, and amount;
   - payment `actor == "adapter:<adapter>"` and
     `memo == "proposal:<consequence_id>"`;
   - account `status == ACTIVE` and `rules.currency == "GEN"`;
   - any account `policy_version` matches the consequence;
   - recipient is a valid address, amount is a positive integer.
4. Refuse if the intent is already `AUTHORIZED`, `PENDING_FINALITY`, or
   `EXPIRED`; a `FAILED` intent may be re-authorized if the Core binding still
   passes.
5. Store the exact intent with `authorized_at`, `expires_at` (now + TTL),
   `status = AUTHORIZED`, `execution = NONE`, and a `core_snapshot_hash`.
6. Emit `IntentAuthorized`.

No native value moves at authorization.

### `settle(consequence_id, recipient, amount)` — permissionless

Checks, in order:

1. vault initialized and not paused;
2. intent exists (`REJECTED_INTENT_NOT_FOUND`);
3. status is `AUTHORIZED`; `PENDING_FINALITY` is a replay
   (`REJECTED_ALREADY_EMITTED`), and `EXPIRED` is
   `REJECTED_INTENT_EXPIRED`;
4. supplied recipient equals the stored recipient
   (`REJECTED_RECIPIENT_MISMATCH`);
5. supplied amount equals the stored amount (`REJECTED_AMOUNT_MISMATCH`);
6. `now < expires_at`, otherwise mark `EXPIRED` and refuse;
7. re-run the full Core binding from `authorize` step 3; a failure is
   `REJECTED_CORE_BINDING` and no transfer;
8. `self.balance >= amount` (`REJECTED_INSUFFICIENT_CUSTODY`);
9. persist `PENDING_FINALITY`, settler, attempt count, and vault balance
   before/after emit; increment `total_emitted`;
10. emit `emit_transfer(value=amount, on='finalized')` to the exact recipient.

The vault cannot observe child-transaction success. It never writes `SETTLED`.
Final success is established by the emitted/child transaction and independent
recipient/vault balance readback.

### `set_paused(paused)` / `pause()` / `unpause()` — owner-only

Pause blocks `authorize` and `settle`. Deposits remain open. Existing
`AUTHORIZED` intents remain stored and become settleable again after unpause,
unless they expire first.

### `set_max_ttl(ttl_seconds)` — owner-only

`1..604800`. Does not change the expiry of an existing intent.

### `get_intent(consequence_id)` — view

Returns the persisted intent record, or `{"status": "NONE"}`.

### `get_config()` — view

Returns owner, core, adapter, currency, max TTL, paused, in-flight consequence,
self address, creation time, and accounting totals.

### `get_balance()` — view

Returns `self.balance` and the accounting totals.

### `preview_authorization(consequence_id, ttl_seconds)` — view

Runs the Core-side decision without writing an intent or emitting value.
Returns `AUTHORIZED`, `REJECTED_*`, or `UNDETERMINED_*` plus the derived fields
and a Core snapshot hash.

### `preview_settlement(consequence_id, recipient, amount)` — view

Runs every `settle` check without mutating state. Returns `SETTLEABLE` or
`REJECTED_*`. It reads the live Core and `self.balance`.

### `__on_errored_message__()` — payable refund hook

Invoked by GenLayer when an emitted value transfer fails. v0.1 records the
actual refunded `gl.message.value` in a refund ledger, increments
`total_refunded`, and does not rewrite any intent. The hook does not carry the
consequence id, so attributing a refund to a specific intent would be a guess;
the intent remains `PENDING_FINALITY` and retry is unsupported.

The refunded value is already credited to `self.balance` by the protocol. The
hook never assumes the refund equals any intent amount; it records the actual
value.

## Canonical refusal vocabulary

Owner-only caller failures raise `Custody: caller is not owner` and do not
persist a record.

Vault state and binding refusals (persisted on the intent or returned by the
preview):

- `REJECTED_NOT_INITIALIZED`
- `REJECTED_VAULT_PAUSED`
- `REJECTED_INVALID_CONSEQUENCE_ID`
- `REJECTED_INVALID_TTL`
- `REJECTED_INVALID_RECIPIENT`
- `REJECTED_INVALID_AMOUNT`
- `REJECTED_INTENT_NOT_FOUND`
- `REJECTED_ALREADY_EMITTED`
- `REJECTED_INTENT_EXPIRED`
- `REJECTED_RECIPIENT_MISMATCH`
- `REJECTED_AMOUNT_MISMATCH`
- `REJECTED_INSUFFICIENT_CUSTODY`
- `REJECTED_CORE_UNAVAILABLE`
- `REJECTED_NO_CONSEQUENCE`
- `REJECTED_CONSEQUENCE_NOT_EXECUTED`
- `REJECTED_PAYMENT_NOT_SETTLED`
- `REJECTED_WRONG_ADAPTER`
- `REJECTED_PAYMENT_BINDING`
- `REJECTED_ACCOUNT_NOT_ACTIVE`
- `REJECTED_CURRENCY_MISMATCH`
- `REJECTED_POLICY_VERSION`
- `REJECTED_CORE_BINDING`
- `UNDETERMINED_DEPENDENCY`

`REJECTED_ALREADY_SETTLED` is reserved for a future observed-success version.
v0.1 uses `PENDING_FINALITY` and refuses a replay with
`REJECTED_ALREADY_EMITTED`. The replay evidence must name the exact code
actually returned.

## Accounting

- `total_deposited`: sum of accepted payable deposits.
- `total_emitted`: sum of values emitted by `settle`.
- `total_refunded`: sum of values returned through
  `__on_errored_message__`.
- No `total_withdrawn`: v0.1 has no withdrawal path.
- Expected invariant: `self.balance == total_deposited - total_emitted +
  total_refunded` at every confirmed state.

## Evidence

Local gates cover the deterministic surface. Native value emission and child
finality are live-only: the direct VM has no real native transfer. Live evidence
must include the deployment, deposit, Core consequence, intent, permissionless
settle, child transaction, and independent balance readback.
