# PPA Native GEN Custody — Decision Boundary

## Classification

```text
JUDGMENT_BOUNDARY = NONE
CONVERGENCE_MODE = EXACT
```

The vault is a deterministic custody executor. It contains no LLM call, no web
retrieval, no `gl.nondet` operation, and no validator-judgment surface. Every
validator must reach the same decision from the same Core, vault, and native
balance state.

## Deterministic preconditions

- The vault is initialized, and the caller is the owner for owner-only methods.
- The configured Core exposes the consequence, payment, and account.
- The consequence is `EXECUTED` with `reason_code` `EXECUTED`.
- The consequence `payment_status` is `SETTLED`.
- The consequence `adapter_caller` is the configured approved adapter.
- The payment is `SETTLED` and binds to the same proposal, payment, decision,
  recipient, amount, actor, and memo.
- The account is `ACTIVE` and its currency is `GEN`.
- Any account policy version matches the consequence.
- The recipient is a valid address and the amount is a positive wei integer.
- The requested TTL is within the configured maximum.
- The consequence has no prior `AUTHORIZED`, `PENDING_FINALITY`, or `EXPIRED`
  intent.
- The vault is not paused at authorization or settlement.
- The settlement recipient and amount exactly match the stored intent.
- The settlement occurs before `expires_at`.
- `self.balance` covers the amount at settlement.

## Intelligent question

None. There is no evidence interpretation, ambiguity resolution, or semantic
equivalence condition. The only "decision" is a deterministic comparison of
persisted Core and vault fields.

## Admissible evidence

- PPA Core state read through `gl.get_contract_at(core).view()`.
- Persisted vault state (`meta`, `intents`, deposits, refunds).
- The native balance `self.balance`.
- The payable `gl.message.value` on `deposit` and the refund hook.
- No caller-supplied consequence or payment JSON is admissible on the write
  path.
- Off-chain child-transaction and recipient-balance readback is evidence for the
  final transfer, not an input to the deterministic decision.

## Equivalence / consensus condition

EXACT. Validators independently read the same deterministic contract state and
must produce the same `AUTHORIZED`, `SETTLEABLE`, `PENDING_FINALITY`, or
`REJECTED_*` result. A cross-contract read failure is
`UNDETERMINED_DEPENDENCY` or `REJECTED_CORE_UNAVAILABLE`, never a permissive
fallback.

## Structured decision

| Outcome | Meaning |
| --- | --- |
| `AUTHORIZED` | Core binding passed; an exact intent was persisted. No native value moved. |
| `SETTLEABLE` | Preview only: an `AUTHORIZED` intent would pass the settlement checks now. |
| `PENDING_FINALITY` | The exact value transfer was emitted; the vault cannot observe child success. |
| `REJECTED_*` | A deterministic precondition failed; no native value moved. |
| `UNDETERMINED_DEPENDENCY` | A required Core/dependency could not be read; no intent and no emit. |

Every write attempt persists an authorization, an intent state, a refusal, or a
deposit/refund record, except a rejected caller, which raises before the state
write.

## Undetermined path

- Core read failure -> `UNDETERMINED_DEPENDENCY` / `REJECTED_CORE_UNAVAILABLE`.
- These outcomes never persist an `AUTHORIZED` intent and never emit value.
- A missing Core, payment, or account is never treated as approval.
- A child-transaction failure is not observable as a success; it is a refund
  ledger entry, and the intent remains `PENDING_FINALITY` in v0.1.

## Deterministic postconditions

- On `AUTHORIZED`, exactly one intent exists for the consequence with the exact
  Core-derived recipient, amount, currency, and expiry. No native value moved.
- On a settlement emit, the intent is `PENDING_FINALITY`, the exact amount was
  deducted from the vault balance at emit, and `total_emitted` increased by the
  amount.
- On `REJECTED`, no native value moved and the intent is unchanged, except that
  an expiry refusal makes the intent terminal `EXPIRED`.
- On a deposit, `total_deposited` increases by the actual value received.
- On a refund, `total_refunded` increases by the actual value returned.
- PPA Core is unchanged by the vault.

## Invariants judgment cannot override

- Only the owner can authorize, pause, or change the max TTL.
- The owner cannot choose recipient or amount.
- The recipient and amount are immutable after authorization.
- A `PENDING_FINALITY` intent cannot emit again.
- An expired intent cannot settle or be re-authorized.
- A paused vault cannot authorize or settle.
- A refusal moves no native value.
- Core `SETTLED` is not native transfer evidence.
- Gas/fees are not custody value.
- NTEST, USDC, and ERC-20 custody cannot be inferred from this primitive.

Because judgment is absent, there is no judgment-specific override path. Core
read failure is fail-closed. Child success is external and is never fabricated
by the vault.
