# Programmable Payment Account - GenLayer Implementation

Deterministic Intelligent Contract implementing the PPA v0.1 canonical slice.

Implementation notes: `ppa.py` is intentionally size-optimized for GenLayer
Bradbury deploy gas headroom (docstrings/comments stripped; blank lines
collapsed). All 20 public method type annotations are retained so the
executable matches `CAPABILITY.json`. Helper/private method annotations may
be omitted. GenVM dependency header and `TreeMap` storage field annotations
are preserved. Behavioral semantics remain owned by `primitives/ppa/SPEC.md`,
`INVARIANTS.md`, `DECISION_BOUNDARY.md`, `CAPABILITY.json`, and this README.

## Public modules/interfaces

Single contract: `ProgrammablePaymentAccount` in `ppa.py`.

Write methods:

- `initialize(owner)` - one-time owner registration; owner is the account controller.
- `create_account(account_id, rules_json)` - open a sub-account under a rules
  envelope (required: `daily_limit`, `per_tx_limit`, `currency`; optional:
  `allowlist`, `require_attestation`, `attestation_issuers`,
  `attestation_policy_version`).
- `update_rules(account_id, rules_json)` - owner replaces the rules envelope.
- `deposit(account_id, amount)` / `withdraw(account_id, amount)` - ledger
  credit / owner-only withdrawal of uncommitted balance.
- `send(account_id, payment_id, to, amount, evidence_hash="", memo="")` -
  core flow: policy gate -> attestation gate -> encumbrance gate -> settle.
  DENY returns a recorded denial (tx succeeds); the payment id stays consumable.
- `issue_invoice` / `settle_invoice` / `get_invoice` - structured receivables
  paid through the same send() gates (`pay-<invoice_id>` payment id).
- `dispute_payment` / `resolve_dispute` / `get_dispute` - gaia-pattern case
  lifecycle; `refund` is a compensating entry, never a history rewrite.
- `delegate` / `revoke_delegation` / `get_delegation` - scoped spending
  authority that narrows, never widens.
- `register_attestation(attestation_id, attestation_json)` - owner registers a
  technical compliance attestation. Fixed schema (subject, issuer, status,
  issued_at, expires_at, evidence_hash, policy_version); unknown fields are
  rejected so no PII can be written onchain. Registration is evidence
  registration only - NOT a KYC/AML or legal-authorization judgment.
- `revoke_attestation(attestation_id)` - owner revocation; affects future
  sends only.

View methods: `get_account`, `get_payment`, `get_invoice`, `get_dispute`,
`get_delegation`, `get_attestation`.

## GenLayer spine (v0.2)

```text
submit_decision_receipt(ACCEPTED|REJECTED|UNDETERMINED)
→ admit_proposal (ACCEPTED+ACTIONABLE only)
→ execute_proposal
→ existing send gates (policy/attestation/capital/replay)
→ SETTLED or DENIED
```

Judgment never moves funds directly. Invoice/dispute/delegate are modular extensions not in the core deploy under Bradbury gas limits.

## Attestation gate semantics

Runs only when the account rules set `require_attestation=true`; otherwise
`send()` behaves exactly as before (backward compatible). Fail-closed: a
payment settles only against a currently `VALID`, non-revoked, unexpired
attestation whose subject binds to the recipient, whose issuer is in the
account's `attestation_issuers`, and whose `policy_version` equals the
account's `attestation_policy_version`. Candidates are evaluated in ascending
`attestation_id` order; the first fully valid candidate admits. Canonical
denial reasons: `ATTESTATION_MISSING`, `ATTESTATION_SUBJECT_MISMATCH`,
`ATTESTATION_REVOKED`, `ATTESTATION_INVALID_STATUS`,
`ATTESTATION_ISSUER_UNAUTHORIZED`, `ATTESTATION_INVALID`,
`ATTESTATION_EXPIRED`, `ATTESTATION_POLICY_MISMATCH`. An unavailable
attestation provider is represented exactly as an absent/invalid attestation
- never an approval.

## Inputs and outputs

State is stored as JSON records in TreeMaps; views return parsed JSON.
`send()` returns a decision object; denial reasons are canonical strings
also visible via `get_payment` (`status=DENIED`, `reason=<code>`).

## State ownership

The contract owns sub-account ledger state, payment/invoice/dispute/delegation
records, and owner-registered attestations. It does not custody external
tokens in v0.1 (deposit credits on authority check) and does not judge whether
attestation evidence substantively establishes real-world compliance.

## Dependencies

Pinned GenLayer Python SDK. Composes canonical primitive semantics embedded
in-account (policy-envelope, claim-encumbrance, proof-of-payable, gaia,
daa/dal patterns); cross-contract extraction is the v0.2 step.

## Expected errors

Rejections raise `ValueError` with a `PPA:` prefix: unknown ids, duplicate
ids, invalid addresses/amounts, schema-violating attestations, non-owner
callers, inactive accounts, reuse of a non-DENIED payment id. Denial of a
payment is NOT an exception - it is a recorded decision.

## Security assumptions

- Owner key compromise controls rules, attestations, and withdrawals; the
  gate sequence cannot be bypassed even by the owner.
- Attestations are self-declared technical evidence registered by the owner;
  this surface does not constitute legal KYC/AML compliance.
- `JUDGMENT_BOUNDARY = NONE` for every money path.

## How to run tests

```bash
python tools/nomos_run_vectors.py \
  primitives/ppa/implementations/genlayer/ppa.py \
  --vectors primitives/ppa/vectors/v0.1.json
# gltest flows (requires glsim on :4000 and contracts/ppa.py symlink):
gltest primitives/ppa/implementations/genlayer/tests/test_ppa_flows.py -q
gltest primitives/ppa/implementations/genlayer/tests/test_ppa_attestations.py -q
```

Canonical vectors cover gate-off backward compatibility, each canonical
attestation denial reason, revoked/expired handling, duplicate-id and
PII-schema rejection, payment-id replay, denied-id retryability, and balance
conservation.

## What remains unsupported

Legal/compliance certification of any kind, cross-contract composition, and
external token settlement.
