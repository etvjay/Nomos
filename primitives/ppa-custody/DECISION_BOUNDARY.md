# PPA Custody Adapter — Decision Boundary

## Classification

```text
JUDGMENT_BOUNDARY = NONE
CONVERGENCE_MODE = EXACT
```

The custody adapter is a deterministic bridge. It contains no LLM call, no web
retrieval, no `gl.nondet` operation, and no validator-judgment surface. Every
validator must reach the same decision from the same Core and vault state.

## Deterministic preconditions

- The configured Core exposes the proposal's consequence, payment, and account.
- The consequence is `EXECUTED` with `reason_code` `EXECUTED`.
- The consequence `payment_status` is `SETTLED`.
- The consequence `adapter_caller` is the configured approved Adapter.
- The payment is `SETTLED` and binds to the same proposal, payment, decision,
  recipient, and amount.
- The payment actor is `adapter:<approved adapter>` and the memo is
  `proposal:<proposal_id>`.
- The account is `ACTIVE`, its currency maps to an allowlisted token, and any
  account policy version matches the consequence.
- The amount is a positive decimal integer and the recipient is a valid address.
- The requested TTL is within the configured maximum.
- The proposal has no prior `AUTHORIZED` or `SETTLED` record in this
  authorizer.
- The vault's pause, token allowlist, duplicate, expiry, and settlement checks
  are enforced atomically when the authorization message executes; they are
  not preflighted by the authorizer.

## Intelligent question

None. There is no evidence interpretation, no ambiguity resolution, and no
semantic equivalence condition. The only "decision" is a deterministic
comparison of persisted fields.

## Admissible evidence

- PPA Core state read through `gl.get_contract_at(core).view()`.
- Persisted authorizer state (`authorizations`, `assets`, `meta`).
- The vault's own state after message execution (authoritative, not readable by
  the authorizer in v0.1).
- No caller-supplied consequence or payment JSON is admissible on the write
  path.

## Equivalence / consensus condition

EXACT. Validators independently read the same deterministic contract state and
must produce the same `AUTHORIZED` or `REJECTED_*` result. A cross-contract read
failure is `UNDETERMINED_*`, never a permissive fallback.

## Structured decision

| Outcome | Meaning |
| --- | --- |
| `AUTHORIZED` | Core binding passed; the exact authorization message was emitted with `execution = PENDING_FINALITY`. The vault creates the intent only at finality. |
| `REJECTED_*` | A deterministic precondition failed; no message was emitted, or the local EVM send failed. |
| `UNDETERMINED_*` | A required Core/dependency could not be read; no EVM send. |

Every write attempt persists either the authorization or the refusal. The only
exception is a rejected caller, which raises before the state write.

## Undetermined path

- Core read failure -> `UNDETERMINED_DEPENDENCY` / `REJECTED_CORE_UNAVAILABLE`.
- These outcomes never emit `authorize` and never claim a settlement.
- A vault-side refusal after finality is recorded on the vault; the authorizer
  cannot observe it and does not claim the intent exists.

## Deterministic postconditions

- On `AUTHORIZED`, exactly one authorization message was emitted for the
  proposal with the exact token, recipient, amount, and expiry. The vault may
  still refuse at execution; only the vault record proves an intent exists.
- On `REJECTED`, no authorization message was emitted.
- PPA Core is unchanged by the authorizer.
- NTEST balances are unchanged by authorization; they change only on a
  successful `settle`.

## Invariants judgment cannot override

- Only the authorizer may create a custody intent.
- The vault's stored token/recipient/amount are exact and immutable.
- A settled proposal cannot settle again.
- An expired intent cannot settle.
- A paused vault cannot authorize or settle.
- A refusal moves no tokens.
- Core `SETTLED` is not external settlement evidence.
- The NTEST fixture is not USDC and has no economic claim.

Because judgment is absent, there is no judgment-specific override path. Core
read failure is fail-closed (`UNDETERMINED_*`). EVM message execution is
asynchronous and outside the authorizer's view; the vault is authoritative and
a vault refusal creates no settlement authority.
