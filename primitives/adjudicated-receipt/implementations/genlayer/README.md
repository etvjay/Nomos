# Adjudicated Receipt - GenLayer Implementation

Judgment-bearing Intelligent Contract implementing Adjudicated Receipt v0.2.

This is the GenLayer-native settlement lock: validator-quorum adjudication
over tx-time external evidence is the ONLY path to release value, and the
ONLY release it authorizes is the single registered surrender value, once,
while the evidence is fresh. Without GenLayer quorum judgment there is no
trigger at all.

## Public modules/interfaces

Single contract: `AdjudicatedReceipt` in `adjudicated_receipt.py`.

Write methods:

- `initialize(owner)` - one-time owner registration; owner registers objects and settles.
- `register_release(invoice_id, object_ref, surrender_value, surrender_asset, evidence_pointer, adjudication_clause, valid_for_seconds)` - bind a release object; creates obligation identity with an evidence TTL. Returns `release_registered`.
- `adjudicate_object(invoice_id, receipt_id)` - permissionless tick: fetches the registered evidence pointer in-transaction, runs the LLM verdict, and records a canonical receipt under validator quorum. Returns `{success, status, ...}` with status `ACCEPTED` / `REJECTED` / `UNDETERMINED` / `UNDETERMINED_DELIVERY_UNCERTAIN`. Triggering confers no release right.
- `settle_release(receipt_id)` - owner-only single release against a fresh, matching, unconsumed ACCEPTED receipt. Returns `{success, status, payment_id, amount, asset, to}`; the payment id is deterministically `pay-<receipt_id>`.

Views: `get_object`, `get_receipt`, `get_release`.

## Inputs and outputs

Registration inputs are plain strings; amounts/TTL are positive uint-strings; `evidence_pointer` must be `https://`. The adjudication input is the byte content fetched from the registered pointer at tick time — the only admissible evidence.

Decision record (immutable except the one-way `consumed` bit): `{receipt_id, invoice_id, evidence_pointer, evidence_digest, verdict, confidence, status, reason_code, at, consumed}` with bounded status vocabulary `ACCEPTED | REJECTED | UNDETERMINED | UNDETERMINED_DELIVERY_UNCERTAIN`.

## State ownership

Release objects (`objects`), adjudication receipts (`receipts`), and release records (`releases`) only. The primitive deliberately owns NO policy, delegation, capital, commitment, encumbrance, or rectification state — settlement authorizes exactly one recorded release of the registered surrender value (Article V separation).

## Dependencies

- GenLayer network with validator quorum over `gl.vm.run_nondet` (load-bearing: no quorum judgment, no trigger).
- Deterministic TIME for TTL enforcement comes from the transaction clock (`gl.message`/`gl.message_raw` datetime).
- Composition points (not dependencies): upstream Proof of Payable / Claim Verification / Mandate Allocation for claim identity and eligibility; downstream Policy Envelope, Claim Encumbrance, Capital Commitment, Gaia, Financial Contract.

## Expected errors

`AdjudicatedReceipt:`-prefixed errors for: duplicate/unknown object and receipt ids, non-open objects, non-ACCEPTED receipts, consumed receipts, binding mismatch, post-TTL record or settlement, invalid URLs/amounts/TTL, non-owner registration/settlement, unknown receipts/releases on views.

## Security assumptions

- Validator set re-fetches and re-judges independently; exact-field equivalence over (satisfied, verdict, confidence) holds.
- ACCEPTED additionally requires (satisfied=true, verdict=delivered, confidence=high) — enforced in deterministic postconditions, not in the model.
- Evidence pointer content is attributable to the registered URL at tick time; URL+TTL binding is the v0.1 mechanism (content-hash binding is an open research question).
- Raises precede every mutation; a failed tick/settlement leaves no phantom receipts and no partial consumption.
- Receipts are immutable evidence even when they deny; consumption is the only mutable bit.

## How to run tests

```bash
# Deterministic envelope + judgment-surface tests with mocked web/LLM:
pytest primitives/adjudicated-receipt/implementations/genlayer/tests/ -v

# Canonical vectors (deterministic envelope only):
python tools/nomos_run_vectors.py primitives/adjudicated-receipt/implementations/genlayer/adjudicated_receipt.py --vectors primitives/adjudicated-receipt/vectors/v0.1.json

# Consensus path (GLSim leader + validators on :4000):
gltest primitives/adjudicated-receipt/implementations/genlayer/tests/integration/ -v -s

# Lint:
genvm-lint check primitives/adjudicated-receipt/implementations/genlayer/adjudicated_receipt.py
```

## What remains unsupported

Token rails: settlement records a release obligation, it does not transfer tokens. Cross-contract receipt consumption (receipt in one contract, settlement in another). Per-object (non-owner) settler bindings — settlement is owner-held in v0.2. Partial-release tiers — partial/low-confidence verdicts are observable non-approval. Conformance: `primitives/adjudicated-receipt/receipts/CONFORMANCE-v0.2.md`; convergence: `convergence-lanes/adjudicated-receipt/your_build.py` 5/5 (deterministic envelope; quorum paths proven direct + GLSim). GLSim post-window finalization is BLOCKED on this build's frozen clock (documented in the integration test and receipt).
