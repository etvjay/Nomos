# Programmable Payment Account - Canonical Specification

Status: CONFORMANT
Version: 0.1.0

## Problem
A builder needs one account surface that holds committed capital and moves it
only through deterministic, rule-gated payment flows, without each builder
reinventing policy, encumbrance, claim, and settlement semantics differently.

## Primitive meaning
The PPA is the user-facing composite over the Nomos financial primitive stack:
a sub-account ledger whose only money path is
`policy gate -> attestation gate -> encumbrance gate -> payable claim -> settle`.
It owns account state and the orchestration; the economic semantics it routes
through belong to the canonical primitives it composes.

## Core invariants
- Funds move only through `send()`-gated flows; every gate is deterministic.
- DENY moves no funds, burns no payment id, and is recorded for audit.
- A payment id is consumed exactly once by a non-DENIED terminal record.
- Historical confirmed records (settled/refunded payments, denial records)
  are never rewritten; rectification is a compensating entry only.
- The attestation gate is fail-closed: an absent, stale, revoked, or
  malformed attestation can never admit a payment.
- Attestations are opaque technical-compliance evidence with a fixed JSON
  schema (no free-form fields, no PII); they never move money by themselves.

## Judgment boundary
NONE for the v0.1 canonical slice. Every decision that moves value is
deterministic rule evaluation. LLM judgment enters only in upstream
monitoring/dispute classification, composed separately.

## v0.1 attestation slice
`register_attestation` / `revoke_attestation` / `get_attestation` add
owner-controlled technical compliance evidence. When account rules set
`require_attestation=true`, `send()` admits a payment only against a currently
`VALID`, non-revoked, unexpired attestation whose `subject` binds to the
recipient, whose `issuer` is in the account's authorized `attestation_issuers`,
and whose `policy_version` equals the account's `attestation_policy_version`.
Canonical denial reasons: `ATTESTATION_MISSING`,
`ATTESTATION_SUBJECT_MISMATCH`, `ATTESTATION_REVOKED`,
`ATTESTATION_INVALID_STATUS`, `ATTESTATION_ISSUER_UNAUTHORIZED`,
`ATTESTATION_INVALID`, `ATTESTATION_EXPIRED`, `ATTESTATION_POLICY_MISMATCH`.
An unavailable attestation provider is represented exactly as an absent or
invalid attestation; it is never an approval.

## Composition
Routes money through policy-envelope (limits/allowlist), claim-encumbrance
(available = balance - committed), proof-of-payable (claim lifecycle), and
gaia-pattern dispute/rectification. Delegation follows daa/dal narrowing
semantics. Attestations are upstream admissibility evidence only.

## Research questions
Can one account contract embed primitive semantics 1:1 without drifting from
the canonical single-primitive implementations? v0.1 answer: yes for the
deterministic gates, with extraction into cross-calling contracts as the v0.2
step. The attestation surface is technical compliance only and must never be
presented as legal KYC/AML compliance.
