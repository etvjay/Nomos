# PPA Custody Adapter — Threat Model

## Trust boundaries

| Boundary | Trusted for | Not trusted for |
| --- | --- | --- |
| PPA Core | policy, internal ledger, consequence/payment records | external token custody |
| PPA Receipt/Proposal Adapter | being the approved consequence caller | custody, correctness of the vault |
| `PPACustodyAuthorizer` | deterministic Core-to-EVM binding | holding funds, PPA policy, adjudication |
| `NomosCustodyVault` | holding NTEST and enforcing exact intents | Core policy, adjudication, asset legitimacy |
| Vault owner | pause, token allowlist, authorizer rotation, emergency withdrawal | forging a Core consequence without the authorizer |
| NTEST owner | minting the test fixture | economic value, external backing |

The authorizer is trusted to read Core correctly and to call the vault with the
exact bound fields. A compromised authorizer is equivalent to a compromised
custody authority: it can create intents up to the vault balance. The vault
cannot independently verify Core. Mitigations are owner pause, authorizer
rotation, and emergency withdrawal. This is the primary residual trust.

## Threats and handling

### Unauthorized authorization

An EOA or unrelated contract calls `vault.authorize`. The `onlyAuthorizer`
modifier reverts with `VAULT_CALLER_NOT_AUTHORIZER` before any state change.
Evidence: a live reverted transaction and an unchanged intent record.

### Forged or caller-supplied Core records

The authorizer's write surface accepts only `proposal_id` and `ttl_seconds`. It
reads `get_consequence`, `get_payment`, and `get_account` from the configured
Core itself. A caller cannot inject an `EXECUTED` JSON blob. The `preview`
surface accepts only the proposal id as well.

### Wrong adapter / wrong Core

The consequence `adapter_caller` must equal the configured approved Adapter.
A consequence written by a different registered Core adapter is
`REJECTED_WRONG_ADAPTER`. The Core address is immutable after initialization.

### Stale consequence

A Core consequence has no custody expiry. The authorizer assigns a fresh,
bounded TTL at authorization. The vault refuses at or after expiry. An expired
intent is terminal and cannot be re-authorized. A stale Core consequence cannot
authorize a new intent under a fresh proposal id because the proposal id is
part of the binding and Core records one consequence per proposal id.

### Replay

The vault keys intents by `keccak256(proposal_id)` and marks successful
settlements `SETTLED`. A replay is refused with `VAULT_INTENT_ALREADY_SETTLED`.
The authorizer also refuses to re-authorize an `AUTHORIZED` or `SETTLED`
proposal. A refusal record may be retried; that is not a replay because no
transfer occurred.

### Wrong token / recipient / amount

The vault stores the exact values at authorization and compares all three at
settlement. Any mismatch is refused, the intent remains executable with the
correct values, and token balances are unchanged. The authorizer never accepts
these fields from the settlement caller.

### Paused custody

The vault checks `paused` at authorization and settlement. A paused vault
refuses without moving tokens. The authorizer does not preflight the pause in
v0.1; the message executes at finality and the vault records the refusal. That
refusal is not observable in the authorizer record, which stays
`AUTHORIZED/PENDING_FINALITY`; the vault record is authoritative.

### Insufficient custody

Authorization does not require a balance; settlement does. An underfunded intent
is refused with `VAULT_INSUFFICIENT_CUSTODY`, no partial transfer, and remains
`AUTHORIZED`. A later deposit can make it settleable. Core has already debited
its internal ledger; the non-atomic gap is recorded.

### Transfer failure / non-standard token

The vault catches a reverting token transfer and records
`VAULT_TRANSFER_FAILED`; the intent is not consumed. Only allowlisted tokens are
accepted. The only deployed token is the standard bool-returning NTEST. Tokens
with fee-on-transfer, rebasing, or no return value are unsupported and must not
be allowlisted.

### Reentrancy

`settle` is `nonReentrant`, and it records the settlement before the external
transfer. A malicious allowed token that re-enters `settle` is blocked. Token
allowlisting is owner-only and restricted to NTEST for this slice.

### Front-running / keeper griefing

`settle` is permissionless. A third party can execute an authorized transfer
only with the exact token, recipient, and amount. They cannot redirect funds or
change the amount; they only pay gas. This is the intended separation between
authorization and execution.

### Cross-chain / non-atomic failure

The GenLayer authorizer's `EthSend` and its own state write are not atomic with
Core or with the EVM vault. Failure modes:

- EVM send succeeds, GenLayer state write later fails: the vault intent exists,
  the authorizer record may be missing. The vault remains the authority; a
  retry gets `VAULT_INTENT_EXISTS` and is recorded as an EVM failure. The intent
  can still be settled exactly.
- GenLayer state commits, EVM send succeeds: normal path.
- Core consequence exists, EVM send fails: the authorizer records a refusal;
  Core is not rolled back.

No path claims a successful external settlement without a vault record and a
balance readback.

### Key management

The live deployment uses the repository's tracked Bradbury deployer key. It is
read at runtime and never printed or copied into an artifact. The key is
testnet-only but must be treated as sensitive; it should be rotated if it was
exposed. Deployment scripts print only the public address, transaction hashes,
and gas figures.

### Owner compromise

A compromised vault owner can pause, rotate the authorizer to a malicious
contract, or emergency-withdraw. This is an explicit trusted-operator boundary.
It cannot forge a Core consequence, but it can bypass the authorizer by
rotating it. Production use would require a multisig/timelock; this testnet
slice does not claim that.

### NTEST misrepresentation

The symbol/name are clearly test-only. The docs and evidence must never call it
USDC, a stablecoin, production collateral, or an official GenLayer asset.

## Out-of-scope attacks

- LayerZero/Hyperlane message forgery (no bridge is implemented).
- USDC blacklist/freeze semantics (no USDC is used).
- Phase 2 chain migration (not implemented).
- Frontend/API authorization (no frontend exists).
- Adjudication manipulation (the custody slice does not adjudicate; it consumes
  an already-EXECUTED Core consequence).
