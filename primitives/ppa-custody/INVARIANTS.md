# PPA Custody Adapter — Invariants

These invariants hold for every successful transaction and for every recorded
refusal. They are deterministic; no LLM or validator judgment participates.

## Authority

1. `NomosCustodyVault.authorize` is callable only by the configured authorizer
   contract. An EOA or any other contract reverts before state changes.
2. The authorizer contract is the only component that can create a custody
   intent. It reads PPA Core itself; it never accepts caller-supplied
   consequence, payment, account, token, recipient, or amount fields.
3. The authorizer never writes to PPA Core and never holds PPA balance authority.
4. The vault never reads or writes PPA Core and never adjudicates policy.
5. The vault's `settle` is an execution path, not an authorization path. It
   cannot change any field of an authorized intent.

## Identity and binding

6. A custody intent is uniquely keyed by `keccak256(proposal_id)`.
7. An intent stores exactly one token, recipient, amount, authorization time,
   and expiry.
8. The intent token is the authorizer's registered asset for the Core account
   `rules.currency`, and the Core consequence's `adapter_caller` is the
   configured approved PPA Adapter.
9. The intent recipient equals both the consequence `requested_recipient` and
   the settled payment `to`.
10. The intent amount equals both the consequence `requested_amount` and the
    settled payment `amount`.
11. The settled payment's `proposal_id`, `payment_id`, `decision_id`, `actor`,
    and `memo` bind back to the same consequence and adapter.

## Settlement

12. A proposal id reaches at most one successful external settlement.
13. A successful settlement transfers exactly the authorized amount of the
    authorized token to the authorized recipient.
14. A settlement attempt with a wrong token, recipient, or amount is refused,
    leaves token balances unchanged, and does not consume the intent.
15. A settlement attempt while the vault is paused is refused, leaves token
    balances unchanged, and does not consume the intent.
16. A settlement attempt with insufficient custody balance is refused, leaves
    token balances unchanged, and does not consume the intent; a later deposit
    may make the same intent settleable.
17. A settlement attempt at or after `expires_at` is refused, leaves token
    balances unchanged, and makes the intent terminal `EXPIRED`.
18. A repeated settlement after success is refused and leaves token balances
    unchanged.
19. A token transfer failure is recorded as a refusal and does not consume the
    intent; it leaves balances unchanged (the failed transfer reverts inside the
    token call and is caught by the vault).
20. Every settlement records before/after custody balance and before/after
    recipient balance, including refusals where those reads are available.

## Pause and configuration

21. Pausing the vault blocks new authorizations and new settlements.
22. Pausing the authorizer blocks new authorizations but does not block
    settlement of existing vault intents; the vault pause is the stronger gate.
23. Disabling a token blocks new authorizations and settlements for that token.
24. Only the vault owner can set the authorizer, pause/unpause, allow/disallow
    tokens, or emergency-withdraw.
25. Emergency withdrawal cannot create an authorization and cannot settle an
    intent; it can only make an outstanding intent underfunded, which surfaces
    as `VAULT_INSUFFICIENT_CUSTODY`.

## Expiry

26. A custody intent's expiry is `authorizer_now + ttl_seconds`, with
    `1 <= ttl_seconds <= max_ttl_seconds <= 604800`.
27. No custody settlement occurs at or after the stored expiry.
28. An expired intent cannot be re-authorized under the same proposal id.

## Evidence

29. The authorizer persists `AUTHORIZED` with `execution = PENDING_FINALITY`
    only after the EVM `authorize` message is emitted; a local send failure is
    persisted as a refusal. `AUTHORIZED` is not proof that a vault intent
    exists; the vault record is authoritative.
30. The authorizer persists a refusal for every Core-side rejection it observes
    and for local EVM send failures, except for a rejected caller (which raises
    before state changes). It does not observe, and must not claim, the vault's
    later execution result. A vault-side refusal (pause, token, expiry,
    duplicate) creates no intent and no settlement authority.
31. The vault persists a record for every intent and every settlement attempt.
32. Core-side `SETTLED` is never treated as proof of an external token
    transfer. The vault balance and the vault record are the external evidence.
33. The Core ledger and the external vault are non-atomic. A vault refusal does
    not roll back Core; evidence records both outcomes separately.

## Test asset

34. `NTEST` has no minter other than its owner, no public sale, no external
    backing, and no claim of stable value.
35. The NTEST deployment, the vault deployment, and the authorizer deployment
    have separate addresses and separate source fingerprints.
