# PPA Native GEN Custody — Invariants

These invariants hold for every successful transaction and every recorded
refusal. They are deterministic; no LLM or validator judgment participates.

## Authority

1. `PPANativeGenCustody.authorize` is callable only by the configured owner. An
   EOA or contract that is not the owner raises before state changes.
2. The owner cannot choose or override the intent recipient or amount. Both are
   read from the bound PPA Core consequence and cross-checked against the
   settled payment.
3. `settle` is permissionless. Any caller can execute an existing intent only
   with the exact stored recipient and amount.
4. The vault never writes to PPA Core and never adjudicates policy. It consumes
   a consequence Core has already recorded as `EXECUTED`.
5. The vault never accepts a caller-supplied consequence JSON. Only the
   `consequence_id` is supplied; all fields come from Core.

## Binding

6. An intent is uniquely keyed by the canonical `consequence_id`, which is the
   PPA Core `proposal_id`.
7. An intent stores exactly one recipient, amount, currency (`GEN`),
   authorization time, expiry, and Core snapshot hash.
8. The consequence must be `EXECUTED` with `reason_code` `EXECUTED`, its
   `payment_status` must be `SETTLED`, and its `adapter_caller` must equal the
   configured approved adapter.
9. The settled payment must bind to the same proposal, payment id, decision id,
   recipient, amount, actor (`adapter:<adapter>`), and memo
   (`proposal:<consequence_id>`).
10. The account must be `ACTIVE`, its currency must be `GEN`, and any account
    policy version must match the consequence.
11. The intent recipient equals both the consequence `requested_recipient` and
    the payment `to`.
12. The intent amount equals both the consequence `requested_amount` and the
    payment `amount`, interpreted as a positive wei integer.

## Settlement

13. A `consequence_id` reaches at most one emitted native transfer.
14. A successful settlement emits exactly the stored amount of native GEN to
    the stored recipient.
15. A settlement attempt with a wrong recipient or amount is refused, leaves
    native balances unchanged, and does not consume the intent.
16. A settlement attempt while the vault is paused is refused, leaves native
    balances unchanged, and does not consume the intent.
17. A settlement attempt with insufficient custody is refused, leaves native
    balances unchanged, and does not consume the intent; a later deposit may
    make the same intent settleable.
18. A settlement attempt at or after `expires_at` is refused, leaves native
    balances unchanged, and makes the intent terminal `EXPIRED`.
19. A repeated settlement after a successful emit is refused with
    `REJECTED_ALREADY_EMITTED` and leaves native balances unchanged.
20. The stored recipient and amount cannot be changed after authorization.
21. The contract revalidates the full Core binding at settlement time; it does
    not rely on the authorization-time snapshot alone.

## Expiry

22. An intent expiry is `authorize_now + ttl_seconds`, with
    `1 <= ttl_seconds <= max_ttl_seconds <= 604800`.
23. No settlement emit occurs at or after the stored expiry.
24. An expired intent is terminal and cannot be re-authorized under the same
    `consequence_id`.
25. Expiry gates the emit, not the later child finality. Value emitted before
    expiry may finalize after it.

## Pause and configuration

26. Pausing blocks `authorize` and `settle`; deposits remain open.
27. Existing `AUTHORIZED` intents remain stored through a pause and become
    settleable again after unpause, unless they expire.
28. Only the owner can pause/unpause and change the max TTL.
29. The Core address, approved adapter, currency, and owner are immutable after
    initialization.
30. v0.1 has no owner withdrawal, ownership transfer, or upgrade path.

## Native value and accounting

31. `deposit` requires a positive `gl.message.value` and credits only the
    actual value received.
32. Native GEN is held by the custody ghost contract; `self.balance` is the
    balance of record.
33. `total_deposited - total_emitted + total_refunded == self.balance` at every
    confirmed state, absent protocol fees charged outside custody value.
34. Gas/protocol fees are never counted as custody value and never reduce the
    transferred amount.
35. v0.1 recipients are externally-owned accounts only.
36. The refund hook records the actual refunded value and never guesses which
    intent failed.

## Evidence and non-claims

37. A vault `PENDING_FINALITY` status is not proof that the recipient was
    credited. Final success requires the emitted/child transaction and
    independent recipient/vault balance readback.
38. A reverted settlement leaves no native value movement and no consumed
    intent, except that an expiry refusal may make the intent terminal
    `EXPIRED`.
39. Core `SETTLED` is never treated as proof of a native GEN transfer.
40. NTEST, USDC, ERC-20 balances, bridges, and production custody are outside
    this primitive and cannot be inferred from its evidence.
