# Adjudicated Receipt - Invariants

- No release without a quorum ACCEPTED record.
- ACCEPTED requires (satisfied=true, verdict=delivered, confidence=high) leader/validator agreement.
- Exactly-once settlement per receipt; the `consumed` bit is one-way (`false → true`) and flips only inside an admitted settlement.
- Receipt records are immutable after recording, except the single consumption bit.
- Non-acceptance states (`REJECTED`, `UNDETERMINED`, `UNDETERMINED_DELIVERY_UNCERTAIN`) can never settle.
- Uncertain, partial, low-confidence, or malformed model output is recorded as non-approval, never approval.
- Settlement executes exactly the registered surrender value, asset, and payee; no other amount, asset, payee, or invoice is expressible on the release path.
- Evidence binding: a receipt settles only the invoice whose `evidence_digest` it carries; re-registered terms invalidate prior receipts.
- TTL freshness: adjudication and settlement must both fall inside the invoice's evidence TTL (`registered_at + valid_for_seconds`).
- History is append-only: invoices, receipts, and payments are never edited or deleted.
- Triggering adjudication confers no settlement right; settlement confers no other authority.
