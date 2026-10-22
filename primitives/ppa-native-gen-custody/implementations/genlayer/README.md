# PPA Native GEN Custody — GenLayer Usage

Deterministic native GEN custody behind an EXECUTED PPA Core consequence.
`JUDGMENT_BOUNDARY = NONE`: no LLM, web, or non-deterministic input.

## Modules

- `ppa_native_gen_custody.py` — readable canonical `PPANativeGenCustody`
  Intelligent Contract.
- `build/ppa_native_gen_custody.compact.py` — deterministic compact deploy
  artifact with the same public surface and storage annotations.
- `../../../../contracts/ppa_native_gen_custody.py` — readable-source symlink.
- `../../../../contracts/ppa_native_gen_custody.compact.py` — compact deploy
  symlink.

## Inputs and outputs

Owner-gated:

- `initialize(owner, core_address, adapter_address, max_ttl_seconds)` — one-time
  configuration. `owner`, `core_address`, and `adapter_address` are 0x-prefixed
  20-byte addresses; `max_ttl_seconds` is a positive decimal string <= 604800.
- `authorize(consequence_id, ttl_seconds)` — reads the live PPA Core consequence,
  payment, and GEN account; persists an exact intent only when all bindings pass.
  The owner cannot choose recipient or amount.
- `pause()`, `unpause()`, `set_paused(paused)`, `set_max_ttl(ttl_seconds)`.

Permissionless:

- `deposit()` — payable. Records `gl.message.value` and `self.balance`.
- `settle(consequence_id, recipient, amount)` — any caller may emit the exact
  stored recipient/amount after expiry, while unpaused and funded. Recipient and
  amount must match byte-for-byte; no caller discretion.
- `__on_errored_message__()` — payable protocol hook. Records refunded value in
  the refund ledger; it does not rewrite the intent or attribute the refund.

Views:

- `preview_authorization(consequence_id, ttl_seconds)` — dry-run Core binding.
- `preview_settlement(consequence_id, recipient, amount)` — dry-run settlement.
- `get_intent(consequence_id)`, `get_config()`, `get_balance()`,
  `get_deposit(seq)`, `get_refund(seq)`.

Statuses: `AUTHORIZED`, `PENDING_FINALITY`, `EXPIRED`, `REJECTED`,
`UNDETERMINED`, plus preview-only `SETTLEABLE`. Successful emission is
`PENDING_FINALITY`; the vault never claims the recipient was credited.

Reason codes are enumerated in `../CAPABILITY.json`. Binding failures are
persisted on `authorize`; settlement refusals are returned and leave an
`AUTHORIZED` intent intact except expiry, which is terminal.

## State ownership

The contract owns only its native GEN balance, settlement intents, deposit/refund
ledger, and configuration. It does not own PPA balances, payments, policies,
consequences, adjudication, recipient balances, or child-transaction finality.
It never mutates PPA Core.

Accounting invariant:

```text
self.balance == total_deposited - total_emitted + total_refunded
```

## Dependencies

- PPA Core at the configured address with an EXECUTED consequence/payment and an
  ACTIVE GEN account.
- The approved PPA Receipt/Proposal Adapter as the recorded `adapter_caller`.
- GenLayer native value support: payable writes, `gl.message.value`,
  `self.balance`, `emit_transfer(on="finalized")`, `__on_errored_message__`.
- SDK header: `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`.

## Security assumptions

- The owner is honest for authorization gating; the owner still cannot choose
  recipient, amount, or settle outside the Core binding.
- The configured Core and adapter are the canonical PPA authority.
- `settle` is safe for any caller because every economically relevant field is
  re-derived and compared before emission.
- `emit_transfer(on="finalized")` is the native finality boundary; monetary
  success requires independent child-transaction and recipient balance readback.
- Recipients are EOAs only in v0.1. There is no owner withdrawal, ownership
  transfer, upgrade path, partial settlement, or automatic retry.
- A refund cannot be attributed to an intent because the hook has no
  `consequence_id`; refunds are accounted globally.

## Build and tests

Bradbury currently rejects the readable source deploy because its estimate is
above the node transaction gas acceptance ceiling. The deployable artifact is
generated deterministically by `tools/nomos_compact_contract.py` with
`python-minifier==3.4.0`. The readable source remains canonical; the artifact
preserves all public methods, statuses, reason codes, error strings, storage
annotations, and checks. `tests/test_compact_artifact.py` fails if the artifact
is stale.

```bash
source ~/nomos-venv312/bin/activate
python tools/nomos_compact_contract.py \
  primitives/ppa-native-gen-custody/implementations/genlayer/ppa_native_gen_custody.py \
  primitives/ppa-native-gen-custody/implementations/genlayer/build/ppa_native_gen_custody.compact.py
python -m pytest primitives/ppa-native-gen-custody/implementations/genlayer/tests/ -q
NOMOS_CUSTODY_PATH=contracts/ppa_native_gen_custody.compact.py \
  python -m pytest primitives/ppa-native-gen-custody/implementations/genlayer/tests/ -q
python tools/nomos_run_vectors.py primitives/ppa-native-gen-custody/implementations/genlayer/ppa_native_gen_custody.py \
  --vectors primitives/ppa-native-gen-custody/vectors/v0.1.json
python tools/nomos_run_vectors.py primitives/ppa-native-gen-custody/implementations/genlayer/build/ppa_native_gen_custody.compact.py \
  --vectors primitives/ppa-native-gen-custody/vectors/v0.1.json
genvm-lint check primitives/ppa-native-gen-custody/implementations/genlayer/ppa_native_gen_custody.py
genvm-lint check primitives/ppa-native-gen-custody/implementations/genlayer/build/ppa_native_gen_custody.compact.py
```

Direct-VM tests use isolated per-contract storage and stub native
`emit_transfer`; live finality is proved separately on Bradbury.

## Unsupported

USDC, CGT, NTEST/ERC-20, bridges, Phase 2, frontend/API, production custody,
owner withdrawal, ownership transfer/upgrade, contract recipients, partial
settlement, human-decimal conversion, automatic retry, refund attribution, and
success claims based only on vault status. This capability is not part of the
released PPA composition.
