# Financial Contract — GenLayer Implementation

Obligation/cash-flow lifecycle Intelligent Contract, v0.1 (scope-narrowed).

## Public modules/interfaces

Single contract: `FinancialContract` in `financial_contract.py`.

Write methods:
- `open_contract(contract_id, creditor, obligor, principal, asset, valid_after, maturity, authority_ref)` — open an ACTIVE obligation bound to its exact upstream authority origin. Self-dealing rejected.
- `apply_payment(contract_id, payment_id, amount, at_timestamp)` — deterministic application with exact conservation. Returns applied amounts or a DENY decision (`EXCEEDS_OUTSTANDING`, `BEFORE_VALIDITY_WINDOW`, `CONTRACT_CLOSED`, `CONTRACT_DEFAULTED`, `CONTRACT_MATURED`). Full repayment → CLOSED.
- `declare_default(contract_id)` — **creditor only**, after maturity, with outstanding balance. ACTIVE → DEFAULTED (terminal for payments).

Views: `get_contract`, `get_payment`.

## Conservation guarantee

`outstanding == principal − total_paid` holds after every operation, in exact
integer arithmetic. Overpayment is denied, never clipped. Denied payments
consume no payment id and mutate nothing.

## State ownership

Obligation state and append-only payment records. The contract does NOT move
funds: `apply_payment` records application; actual transfer belongs to
settlement/custody layers. Historical records are never rewritten.

## Expected errors

`FinancialContract:`-prefixed ValueError/UserError: unknown/duplicate ids,
empty fields, zero/malformed amounts, inverted dates, self-dealing,
non-creditor default declaration, premature default, terminal-state mutations,
duplicate payment ids per contract.

## Security assumptions

- Addresses compare case/prefix-insensitively.
- v0.1 implements no interest/fees/covenants — deferred to future capability
  versions with declared judgment boundaries.
- Block time read from the transaction datetime; default requires maturity
  strictly past.

## How to run tests

```bash
python tools/nomos_run_vectors.py primitives/financial-contract/implementations/genlayer/financial_contract.py --vectors primitives/financial-contract/vectors/v0.1.json
python -m pytest primitives/financial-contract/implementations/genlayer/tests/ -v
```

9 canonical vectors + 3 direct tests (creditor-gated default, pre-maturity
rejection, post-default payment denial).

## What remains unsupported

Interest accrual, contingent clauses, covenants, restructuring, in-contract
interpretation of external events (compose claim-verification), deployment
receipts, and independent-partner convergence evidence.
