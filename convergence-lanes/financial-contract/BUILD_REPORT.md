# BUILD_REPORT - financial-contract (convergence lane)

## Result
- **PASS** - all 9 canonical v0.1 vectors pass in EXACT mode, plus direct tests for the sender-gated default path (vector fc-default-declared-by-authority-006 declares itself "sender-gated; covered by direct tests").
- Build: `your_build.py` (independent reimplementation from spec artifacts only).

## Inputs read
Only: `primitives/financial-contract/{SPEC.md, CAPABILITY.json}` and `vectors/v0.1.json`. Implementations dir NOT read.

## Semantics implemented
- `open_contract`: binds creditor/obligor/principal/asset/valid_after/maturity + exact upstream `authority_ref`. Rejects duplicate ids, empty fields, zero principal, inverted dates (valid_after > maturity), self-dealing.
- `apply_payment`: deterministic application, exact integer conservation `outstanding = principal − total_paid`; status APPLIED records append-only/immutable. Overpayment → DENY EXCEEDS_OUTSTANDING (never clipped, no id consumed). Duplicate payment_id per contract rejected (replay-safe); denied payments consume no id. Payment before valid_after → DENY BEFORE_VALIDITY_WINDOW. Full repayment → CLOSED (terminal). CLOSED → DENY CONTRACT_CLOSED; DEFAULTED → DENY CONTRACT_DEFAULTED.
- `declare_default`: **creditor-gated** (`sender == creditor`), only at/after maturity timestamp, requires outstanding balance > 0; result terminal for payments. Non-creditor / pre-maturity / non-existent balance rejected.
- Contract statuses ACTIVE/MATURED/DEFAULTED/CLOSED; payments APPLIED.

## Key interpretation choice
Vector fc-maturity-and-full-repayment-005 applies a payment at ts far past maturity and expects APPLIED - so in v0.1 the **maturity timestamp gates default declaration, not payment application**. MATURED is a declared status; CONTRACT_MATURED denial is returned only from that explicit status. Documented inline in code.

## Verification
```
python3 your_build.py ../../primitives/financial-contract/vectors/v0.1.json   # PASS x9
python3 - <<EOF ... direct default-gate tests ... EOF                          # PASS
```
Determinism: integer-only arithmetic, canonical JSON output, no clock/randomness inside methods (timestamps passed explicitly). JUDGMENT_BOUNDARY = NONE.
