# Programmable Payment Account - Invariants

- Funds move only through the full send() gate sequence; no method mutates
  balances outside deposit/withdraw/refund paths with their own authority checks.
- A DENY moves no funds, consumes no payment id, and records an auditable reason.
- A payment id reaches a non-DENIED terminal state at most once.
- Settled payments, denial records, and refunded payments are immutable history;
  rectification is a compensating entry (refund), never a rewrite.
- `available = balance - committed` is the only spendable capacity; sends cannot
  overcommit it.
- When `require_attestation=true`, a payment settles only against a currently
  valid, non-revoked, unexpired, correctly bound attestation; the gate is
  fail-closed and unavailability is a denial, never an approval.
- Attestation records have a fixed schema; unknown fields (including any PII)
  are rejected at registration.
- Delegation narrows limits; it never widens account rules.
- Revoking an attestation or delegation affects future sends only; historical
  records are never rewritten.

## Receipt origin (v0.3)

- A receipt is admissible only if the account owner has registered the calling
  adjudicator's `source_contract` and that entry is `ACTIVE` and unexpired at
  submission time.
- Origin is bound to the invoking address, `gl.message.sender_address`, never to
  a `source_contract` string inside caller-supplied JSON. A JSON field asserting
  a source is a claim, not provenance.
- A registered adjudicator entry additionally pins an authority fingerprint over
  the adjudicator's code identity. A receipt presented by an address whose
  registered fingerprint no longer matches is refused
  (`RECEIPT_AUTHORITY_MISMATCH`); registration cannot silently retarget a
  different contract.
- An unregistered, revoked, expired, or mismatched source yields a stored,
  non-actionable receipt with an explicit reason code
  (`RECEIPT_SOURCE_UNREGISTERED`, `RECEIPT_SOURCE_REVOKED`,
  `RECEIPT_SOURCE_EXPIRED`, `RECEIPT_SOURCE_MISMATCH`,
  `RECEIPT_AUTHORITY_MISMATCH`). Refusal is recorded, never silent.
- Only `ACCEPTED` and unexpired receipts from an authorized, non-revoked source
  become actionable. `REJECTED` and `UNDETERMINED` stay non-actionable
  regardless of origin: the fail-closed rule does not relax for trusted callers.
- A `decision_id` is consumed on first submission, actionable or not. A refused
  receipt must not be re-presented under a fresh id to obtain a second
  evaluation.
- Revoking a registered adjudicator affects future receipts only; receipts
  already admitted keep their recorded provenance and are never rewritten.
- Origin authentication never widens authority. It only establishes who may
  propose; the existing `send()` gate sequence still disposes.
