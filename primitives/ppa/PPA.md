# The Programmable Payment Account

## Why we built it

Ask a developer to build a payment app. They don't start by reasoning about
claims, encumbrances, and policy envelopes - they start with an account that
holds money and a `send()` function that moves it under rules they control.
Everything else - invoicing, recurring billing, disputes, delegated access -
hangs off those two ideas.

The Nomos primitive stack was built the opposite way: bottom-up, one verified
mechanism at a time. Proof-of-payable knows how a payment becomes a settled
claim with evidence attached. Claim-encumbrance knows how capacity is locked
so it can never be double-spent. Policy-envelope knows how a spending rule
admits or denies a request deterministically. Gaia knows how a payment that
went wrong gets disputed and rectified without rewriting history.

Each piece was correct. None of them, alone, was something a builder could use.

The Programmable Payment Account (PPA) is the layer where those two worlds
meet. It is one contract you deploy once and configure however you want - an
account with money in it, rules around it, and every internal movement routed
through the verified primitives underneath.

## What it does

A PPA is opened by an owner and configured with a **rules envelope**:

```json
{
  "daily_limit": "1000",
  "per_tx_limit": "500",
  "currency": "USDC",
  "allowlist": ["0x…"],
  "require_attestation": true
}
```

From there, the account exposes the verbs people actually expect:

**`send`** - the core flow. Every payment passes through four gates in order,
and no gate can be skipped:

1. **Policy gate.** Is the recipient allowed? Is the amount within per-transaction
   and daily limits? Denied requests are recorded for audit but move nothing
   and consume nothing - fix the rule, retry the same payment id.
2. **Encumbrance gate.** Is there uncommitted balance to cover this? The
   account tracks committed vs available funds separately, so overcommitment
   is structurally impossible rather than merely forbidden.
3. **Payable claim.** The payment exists as a claim with an evidence hash and
   memo - not just a ledger line, but a settlement record that downstream
   verification (claim-verification) can later attest.
4. **Settle.** Funds move. History is written once and never rewritten.

**Invoices** are structured receivables. Issuing one creates an open claim
against a payer; settling it runs the payer's own policy and encumbrance
gates - an invoice cannot force a payment that rules would deny.

**Disputes** follow the gaia lifecycle: open a case against a settled payment
in a declared economic category (settlement-mismatch, unauthorized-payment,
duplicate, …), then resolve with a remedy. A refund is a compensating entry:
the original payment stays in history marked REFUNDED, the balance is restored.
The past is annotated, never edited.

**Delegation** grants scoped spending authority to another principal, with its
own per-transaction and daily limits plus expiry. The critical property:
delegation narrows, never widens. A delegate's payments still run through the
full account policy - the effective limit is always the *minimum* of the
account's rule and the delegation's rule. Revoke takes effect immediately;
expiry takes effect silently at the block boundary.

## What it deliberately doesn't do

**No judgment moves money.** Every decision inside the send path - allowlist
checks, limits, encumbrance arithmetic - is deterministic code evaluated by
every validator identically. LLM judgment has a place in the broader system
(monitoring external data, classifying dispute categories), but it enters only
through upstream composition, never through the value-moving path itself. This
is Nomos's constitution rule inherited by construction: there is no code path
where an AI output changes a balance.

**No swap in v0.1.** Exchange requires liquidity sources that don't yet exist
on the testnet; shipping a wrapper around nothing would be theater. The rules
engine is designed so a swap action slots into the same gate pipeline when a
real venue exists.

**Single-contract composition in v0.1.** The primitive semantics are embedded
in-account rather than called cross-contract. The state machines mirror the
canonical primitives exactly - the extraction into separate contracts with
cross-calls is mechanical once Bradbury's cross-contract story stabilizes.

## Evidence

All flows pass live transaction tests on GLSim localnet through full GenLayer
consensus (`6/6 PASS`):

- happy-path send: settle + balance/daily-window updates
- per-tx limit: denied, zero funds moved, same id retryable after rule change
- allowlist: non-allowlisted recipient denied
- insufficient commitment: denied without touching balances
- invoice: issue → settle through gates → both records updated
- dispute: refund restores balance, original payment marked REFUNDED, case closed

Deployed to Testnet Bradbury alongside the eleven underlying primitives.

## For builders

Consume the PPA, not the primitives. Configure accounts with rules; call
`send`; build your app. If you need deeper guarantees, each gate maps to a
canonical primitive with published vectors and specs in the repository:

| PPA concept | Underlying primitive |
|---|---|
| Rules envelope | policy-envelope |
| Balance / committed split | capital-commitment, claim-encumbrance |
| Payment record | proof-of-payable |
| Invoice | proof-of-payable (structured claims) |
| Dispute / refund | gaia |
| Delegation | dynamic-authority-allocation, authorization lanes |

The account is the product. The primitives are the proof that the product does
what it says.
