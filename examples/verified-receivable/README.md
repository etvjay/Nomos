# Verified Receivable (EXP-CONV-002, lane D)

A tiny financial application composed from two canonical Nomos primitives using
only their published capability contracts, SDK types, and composition docs:

- **Claim Verification** (`primitives/claim-verification`) - SEMANTIC,
  judgment-bearing. Produces a canonical decision (`VERIFIED` | `CONFLICTED` |
  `INSUFFICIENT` | `UNDETERMINED`) for a claim against immutable evidence.
- **Claim Encumbrance** (`primitives/claim-encumbrance`) - EXACT,
  deterministic. Owns immutable financeable capacity per claim and a reservation
  lifecycle (`RESERVED -> COMMITTED`, `-> RELEASED/SETTLED`).

## Flow

```text
Verified receivable (invoice claim)
        |
        v
Claim Verification  verify_claim(verification_id, claim_id, evidence_digest, claim_json, evidence_json)
        |               -> canonical decision { status: VERIFIED | CONFLICTED | INSUFFICIENT | UNDETERMINED }
        v
VERIFIED?  ------------------------------- no ------------------> reserve REJECTED
        |
       yes
        v
Claim Encumbrance  set_financeable_amount(claim_id, amount)
        |           reserve(reservation_id, claim_id, amount)
        v
financeable balance changes:
  active_encumbrances(claim_id) increases by the reserved amount,
  financeable_amount(claim_id) is unchanged (capacity is immutable).
```

Concretely:

1. The application prepares an immutable evidence bundle and calls
   `ClaimVerification.verify_claim(...)`, persisting a canonical decision.
2. The composition layer (`VerifiedReceivable`) reads the decision via
   `get_verification(verification_id)`.
3. If and only if `decision.status == "VERIFIED"` (and the decision's
   `claim_id` matches the target claim), the composition layer calls
   `ClaimEncumbrance.reserve(reservation_id, claim_id, amount)`.
4. `active_encumbrances(claim_id)` reflects the reservation; the financeable
   balance changes.

## Composition gate

Capital is never reserved against a claim unless a VERIFIED decision exists for
it. Missing verification, or any non-VERIFIED decision (`CONFLICTED`,
`INSUFFICIENT`, `UNDETERMINED`), rejects the reservation before the encumbrance
primitive is touched. See `implementations/genlayer/verified_receivable.py`.

## Layout

```text
examples/verified-receivable/
  README.md                                        this file
  sdk/types.ts                                     composition-level TypeScript types
  implementations/genlayer/verified_receivable.py  composition layer (VerifiedReceivable)
  tests/test_verified_receivable.py                direct-mode composition tests
```

## Running the tests

```bash
cd /workspaces/Nomos
python3 -m pytest examples/verified-receivable/tests/ -v
```

## What this composition does NOT claim

A VERIFIED decision is not creditworthiness, capital allocation authority,
claim unencumberedness, or settlement authorization. Those guarantees remain the
responsibility of other Nomos primitives and the application itself.