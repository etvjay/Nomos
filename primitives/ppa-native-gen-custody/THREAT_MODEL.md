# PPA Native GEN Custody — Threat Model

## Trust boundaries

| Boundary | Trusted for | Not trusted for |
| --- | --- | --- |
| PPA Core | policy, internal ledger, consequence/payment/account records | native GEN custody |
| PPA Receipt/Proposal Adapter | being the approved consequence caller | custody, correctness of the vault |
| `PPANativeGenCustody` | holding native GEN and enforcing exact intents | PPA policy, adjudication, asset legitimacy |
| Vault owner | authorization, pause, max-TTL configuration | choosing recipient/amount, settling, withdrawing |
| GenLayer protocol | native value transfer accounting and finality | off-chain recipient readback |

A compromised owner can create intents only for real, executed Core
consequences; it cannot invent a recipient or amount. It can pause or delay
settlement, and it can authorize a consequence with a short TTL that expires
before anyone settles. Those are availability effects, not value-redirection
effects. Owner compromise is still an explicit trusted-operator boundary.

## Threats and handling

### Unauthorized authorization

A non-owner calls `authorize`, `pause`, `unpause`, or `set_max_ttl`. The
owner-only guard raises before any state change. Evidence: a reverted
transaction and an unchanged intent/config record.

### Forged or caller-supplied Core records

`authorize` accepts only `consequence_id` and `ttl_seconds`. It reads
`get_consequence`, `get_payment`, and `get_account` from the configured Core.
A caller cannot inject an `EXECUTED` JSON blob. `settle` accepts recipient and
amount only as exact-match confirmations of the stored intent and the live Core
binding; a mismatch is refused.

### Wrong adapter / wrong Core

The consequence `adapter_caller` must equal the configured approved adapter.
The Core address is immutable after initialization. A vault bound to a different
Core cannot read the canonical consequence and fails closed.

### Stale consequence

Core records one consequence per proposal id. The vault assigns a fresh bounded
TTL at authorization. A stale consequence cannot be turned into a new intent
under the same id; a new proposal id would have its own Core consequence. An
expired intent cannot be re-authorized or settled.

### Replay

An intent is keyed by `consequence_id`. A `PENDING_FINALITY` intent refuses a
second `settle` with `REJECTED_ALREADY_EMITTED`. Re-authorizing an
`AUTHORIZED`, `PENDING_FINALITY`, or `EXPIRED` intent is refused. A refusal
record does not create value authority.

### Wrong recipient / amount

The vault stores the exact Core-derived values and compares both at settlement.
A mismatch is refused, the intent remains executable with the correct values,
and native balances are unchanged. `settle` cannot redirect funds.

### Paused custody

Pause blocks `authorize` and `settle`. A paused vault refuses without moving
value. Deposits remain open. Existing intents are not deleted.

### Insufficient custody

Authorization does not require a balance; settlement does. An underfunded intent
is refused with `REJECTED_INSUFFICIENT_CUSTODY`, no partial transfer, and
remains `AUTHORIZED`. A later deposit can make it settleable. Core has already
debited its internal ledger; the non-atomic gap is recorded.

### Native transfer failure / refund

If the emitted child transfer fails, GenLayer returns the value through
`__on_errored_message__`. v0.1 records the actual refunded value and increments
`total_refunded`, but does not rewrite the intent because the hook does not
carry the consequence id. The intent stays `PENDING_FINALITY`; retry is
unsupported. Accounting remains exact. This is a deliberate fail-closed
limitation, not a claim of automatic recovery.

### Gas/value confusion

Protocol fees are a separate budget. The vault never adds fees to the intent
amount and never treats a fee payment as custody value. Evidence must separate
the deposit/settlement value from gas.

### Child-finality confusion

The vault cannot observe child success. `PENDING_FINALITY` is not settlement
proof. Evidence must identify the child/emitted transaction and read recipient
and vault balances independently. An EVM-style status or the vault's own emit
record alone is insufficient.

### Contract recipient

v0.1 emits to externally-owned accounts only. A contract recipient may not
accept the native transfer or may execute unexpected code. Unsupported; do not
claim it.

### Owner compromise

A compromised owner can pause, set a hostile max TTL, and authorize real Core
consequences. It cannot choose a different recipient or amount, settle on its
own authority, or withdraw. Production use would require a multisig/timelock;
this testnet slice does not claim that.

### Key management

The live deployment uses a testnet deployer key read at runtime. It is never
printed or copied into an artifact. The key is testnet-only but must be treated
as sensitive; rotate it if exposed.

### Native GEN misrepresentation

Native GEN is the network's gas token. This primitive does not claim it is
USDC, a stablecoin, externally backed, or production collateral. It also does
not claim NTEST or any ERC-20 is native GEN.

## Out-of-scope attacks

- LayerZero/Hyperlane message forgery (no bridge is implemented).
- USDC blacklist/freeze semantics (no USDC is used).
- ERC-20 transfer semantics (no token contract is used).
- Phase 2 chain migration (not implemented).
- Frontend/API authorization (no frontend exists).
- Adjudication manipulation (custody consumes an already-EXECUTED consequence).
- Automatic retry or refund-to-intent attribution (unsupported in v0.1).
