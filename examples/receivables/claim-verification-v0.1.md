# Receivables Example - Claim Verification v0.1

This example shows how a financial application can consume Nomos Claim Verification before authority allocation or capital reservation.

## Scenario

Supplier A presents invoice claim `C123` for 100,000 USD against Acme Buyer.

The application prepares an immutable evidence bundle offchain:

```json
{
  "invoice": {
    "number": "INV-42",
    "amount": "100000",
    "asset": "USD"
  },
  "delivery": {
    "status": "accepted"
  }
}
```

The application computes and persists the exact evidence snapshot digest, then calls:

```text
ClaimVerification.verify_claim(
  verification_id = "V-C123-1",
  claim_id = "C123",
  evidence_digest = "sha256:...",
  claim_json = "...",
  evidence_json = "..."
)
```

A finalized canonical decision may be:

```json
{
  "verification_id": "V-C123-1",
  "claim_id": "C123",
  "evidence_digest": "sha256:...",
  "status": "VERIFIED",
  "reason_code": "EVIDENCE_SUPPORTS_CLAIM",
  "requested_by": "0x..."
}
```

## Downstream composition

A financial application can then use the verification record as an input to later Nomos primitives:

```text
Proof of Payable / Claim C123
        ↓
Claim Verification V-C123-1
        ↓
Policy Envelope
        ↓
DAA
        ↓
Claim Encumbrance
        ↓
Capital Commitment
```

The Claim Verification decision does **not** itself mean:

- the borrower is creditworthy;
- capital should be allocated;
- the claim is unencumbered;
- capital has been reserved;
- settlement is authorized.

Those remain separate financial guarantees supplied by other Nomos primitives.
