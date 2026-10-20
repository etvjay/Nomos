# Programmable Payment Account - Decision Boundary

`JUDGMENT_BOUNDARY = NONE` for the v0.1 canonical slice. Policy limits,
allowlists, attestation admissibility (status/issuer/time window/policy
binding), encumbrance arithmetic, payment-id consumption, delegation
narrowing, and dispute remedies are deterministic and implemented as such.
Substantive judgment over whether an attestation's underlying evidence
actually establishes real-world compliance, and over dispute category or
remedy selection, is outside this primitive and belongs to upstream
monitoring/claim-verification composition. No judgment output can move
funds directly; only the deterministic gates admit a payment.

## v0.3 — adjudication front-end, deterministic disposition

The judgment-bearing component is **not** inside this primitive. It is a separate
GenLayer adjudication contract that owns web retrieval, non-deterministic
reasoning, validator equivalence, and the resulting `ACCEPTED` / `REJECTED` /
`UNDETERMINED` status. PPA consumes its verdict; it never produces one.

The split follows one rule: **judgment proposes, deterministic gates dispose.**

What stays inside PPA and is implemented deterministically:

- adjudicator registry lifecycle — register, revoke, expiry — and the authority
  fingerprint comparison;
- binding receipt origin to `gl.message.sender_address` against that registry;
- receipt schema, terminal-status vocabulary, equivalence-mode vocabulary, and
  expiry-window arithmetic;
- the decision that only `ACCEPTED` + authorized + unexpired yields
  `ACTIONABLE`;
- `decision_id` consumption and replay refusal;
- proposal admission and the unchanged `send()` gate sequence.

What is explicitly outside:

- whether external evidence actually supports the conclusion;
- whether validators should agree, and what consensus status results;
- which remedy or actionability a human or model ought to choose.

A subtlety worth stating plainly: authenticating the adjudicator does **not**
make its verdict safe, only attributable. PPA verifies *who spoke*, never
*whether they were right*. A compromised or merely buggy registered adjudicator
can still emit `ACCEPTED` for a false conclusion, and PPA will honour it. That
residual risk is the adjudicator's to carry, which is why registration pins an
authority fingerprint and why revocation exists. Origin binding converts an
unattributable claim into an attributable one; it is an integrity property, not
a correctness oracle.
