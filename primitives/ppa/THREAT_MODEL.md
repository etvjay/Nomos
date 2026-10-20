# Programmable Payment Account - Threat Model

Test replay of settled payment ids, denied-id retry abuse, balance overcommit,
daily-window manipulation, delegation widening, stale/expired/revoked
attestations authorizing new state, attestation substitution under another
subject, unauthorized issuers, policy-version drift, schema loosening that
carries PII onchain, provider outage mistaken for approval, and partial
execution leaving an impossible balance. The core failures to prevent are
bypassing the deterministic gate sequence and treating stale or unavailable
compliance evidence as current approval. Attestations here are technical
compliance evidence only; they do not constitute legal KYC/AML compliance.

## Receipt fields are claims unless origin is authenticated

Found against the v0.2 receipt/proposal spine deployed at
`0xa4fbEc963Bc105bc950648D092d11bAE7eF191fb`, and fixed in v0.3.

`submit_decision_receipt` validated receipt *shape* only: exact field set,
non-empty string values, `decision_status` within the terminal vocabulary,
`equivalence_mode` within its vocabulary, and `expires_at > created_at`. It did
not authenticate *origin*. `source_contract` was a self-asserted string, and
`evidence_hash`/`question_hash` were unverified labels.

Attack path:

```text
attacker supplies receipt JSON with decision_status = ACCEPTED
  -> source_contract = any 20-byte address, registered nowhere
  -> _validate_receipt passes (shape is well-formed)
  -> actionability = ACTIONABLE
  -> admit_proposal admits an executable proposal
  -> execute_proposal routes through send() gates and settles
```

This was reproduced, not merely reasoned about: the live spine run on
`0xa4fbEc96…` settled 100 units on a receipt whose `source_contract` was the
placeholder `0xabc000000000000000000000000000000000001`.

**Immediate blast radius is bounded, and the bound must not be overstated.**
`_resolve_actor` admits only the account owner into `submit_decision_receipt`,
and the owner can already call `send()` directly with no receipt at all, under
policy limits and the attestation gate. So v0.2 does not, by itself, hand an
outsider the ability to move funds it could not already move. The owner could
also simply write the receipt by hand, which is what happened.

**The severity is that the receipt is an unauthenticated evidence artifact.**
It is stored and presented as a GenLayer consensus result — carrying
`equivalence_mode: comparative`, a `source_contract`, and a `decision_status` —
while being nothing more than a string the caller typed. Under v0.2 nothing
downstream was entitled to trust it, so nothing was yet exploitable. That
ceases to hold as soon as any other component treats the receipt as
authority:

- a custody module releasing value against a receipt;
- a bridge adapter accepting receipt-backed settlement;
- an external counterparty requiring judgment-backed proof of settlement;
- a frontend rendering a "judgment-backed" badge;
- an auditor or conformance lane treating stored receipts as the evidence set.

At each of those points the forgery becomes privilege escalation rather than a
no-op, and it does so silently, because the record is well-formed.

The same reasoning forbids a weaker repair. An adjudicator that merely writes
its own address into a JSON field the caller supplies is not a provenance
mechanism; the caller can write any address. Provenance must derive from who
actually invoked the PPA — `gl.message.sender_address` — compared against a
registered adjudicator, with an authority fingerprint pinning the adjudicator's
code identity. See INVARIANTS.md and DECISION_BOUNDARY.md for the v0.3 rules.
