# PPA Custody EVM Implementation

Foundry implementation of the two EVM components in the `ppa-custody` slice.

## Contracts

- `src/NomosTestAsset.sol` — minimal owner-minted ERC-20 (`NTEST`, 18 decimals).
  Testnet-only; no external backing or economic claim.
- `src/NomosCustodyVault.sol` — holds allowlisted ERC-20s, stores
  proposal-bound intents, and executes exact-intent settlements.

## Public interface

`NomosCustodyVault`:

- `authorize(proposalId, token, recipient, amount, expiresAt)` — only the
  configured authorizer; stores the exact intent.
- `settle(proposalId, token, recipient, amount)` — permissionless; can only
  execute the stored exact fields.
- `deposit(token, amount)` — pulls an allowlisted token.
- `withdraw(token, to, amount)` — owner-only emergency withdrawal; makes
  outstanding intents underfunded rather than rewriting them.
- `setAuthorizer(address)`, `setPaused(bool)`, `allowToken(address,bool)`,
  `transferOwnership(address)` — owner-only configuration.
- `getSettlement(proposalId)`, `custodyBalance(token)`, `owner()`,
  `authorizer()`, `paused()`, `allowedTokens(token)`.

`NomosTestAsset`: standard ERC-20 `transfer`, `approve`, `transferFrom`,
`balanceOf`, `allowance`, plus owner-only `mint` and `transferOwnership`.

## State ownership

The vault owns custody balances and intent/settlement records. It does not own
PPA policy, payments, or consequences, and it cannot read PPA Core. The
authorizer is the only address allowed to create intents; the owner cannot
create or rewrite one.

## Expected errors

Authorization refusals are stored as `REFUSED` with a stable reason code:
`VAULT_PAUSED`, `VAULT_TOKEN_NOT_ALLOWED`, `VAULT_INVALID_PROPOSAL_ID`,
`VAULT_INVALID_RECIPIENT`, `VAULT_INVALID_AMOUNT`, `VAULT_INVALID_EXPIRY`,
`VAULT_INTENT_EXISTS`, `VAULT_INTENT_ALREADY_SETTLED`, `VAULT_INTENT_EXPIRED`.
Non-authorizer calls revert with `VAULT_CALLER_NOT_AUTHORIZER`.

Settlement refusals: `VAULT_INTENT_NOT_FOUND`, `VAULT_INTENT_ALREADY_SETTLED`,
`VAULT_INTENT_EXPIRED`, `VAULT_PAUSED`, `VAULT_TOKEN_NOT_ALLOWED`,
`VAULT_TOKEN_MISMATCH`, `VAULT_RECIPIENT_MISMATCH`, `VAULT_AMOUNT_MISMATCH`,
`VAULT_INSUFFICIENT_CUSTODY`, `VAULT_TRANSFER_FAILED`.

## Security assumptions

- The authorizer address is trusted to create exact intents; a compromised
  authorizer can choose any token/recipient/amount allowed by the vault.
- The owner can pause, rotate the authorizer, allow/deny tokens, and withdraw
  custody; a compromised owner is a custody-authority compromise.
- `settle` is permissionless by design. It cannot change the stored fields.
- The vault checks balance only at settlement. Authorizing an underfunded intent
  does not move tokens and does not rewrite the intent.
- Standard ERC-20 assumptions; fee-on-transfer, rebasing, and non-standard
  tokens are unsupported.

## Tests

```bash
forge test --root primitives/ppa-custody/implementations/evm -vv
```

21 tests cover token mechanics, authorization binding, replay, pause, token
allowlisting, exact-settlement mismatches, underfunding, expiry, and
authorizer rotation.
