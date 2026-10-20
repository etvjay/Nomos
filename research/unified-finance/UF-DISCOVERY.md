# Unified Finance (UF) — Discovery Document

**Status:** `DISCOVERY`
**Date:** 2026-10-11
**Lane:** `research/unified-finance/**` only — no primitive, manifest, foundation, or implementation changes in this document.
**Authority:** `CONSTITUTION.md`, `CONVERGENCE.md`, `PRIMITIVE_QUALIFICATION.md`, `NOMOS_WHITEPAPER.md`, `environments/genlayer/PROFILE.md`.
**Relation to Nomos:** Nomos remaining work (`financial-contract` re-qualification, `ppa` v0.2 cross-contract extraction, `adjudicated-receipt` quorum/challenge proof, `IAS-1 1.0` multi-build) is **not blocked** by this document and **not changed** by it. UF is a future primitive family proposal only.

> Research, not specification. No SPEC.md, CAPABILITY.json, vectors, implementations, or manifest entry is created or implied. Per Art VII and Art XII, UF claims are NOT_IMPLEMENTED until executable evidence exists.

## 1. What Unified Finance is

One account that can hold, owe, receive, and settle money without rebuilding treasury + receivables + payables + obligations differently every time.

Nomos proves bottom-up mechanisms (10x CONFORMANT) and one top-down product (ppa IMPLEMENTING: policy -> attestation -> encumbrance -> claim -> settle). The missing middle: hand-wiring "this invoice receivable, that supplier payable, that loan obligation, and this treasury balance are all the same money." UF is that middle, as primitives, not as an app.

Authority separation (Art V) must hold:

```text
Evidence != Verification != Policy != Authority != Encumbrance != Commitment != Settlement != Rectification
```

GenLayer boundary (Art III-IV, ias/integration/README.md):

```text
DETERMINISTIC PRECONDITIONS -> NONDET OP (gl.nondet leader+validators)
-> EQUIVALENCE -> BOUNDED DECISION (ACCEPTED/REJECTED/UNDETERMINED)
-> DETERMINISTIC POSTCONDITIONS (authority/policy/capital/replay/settlement gates)
```

UNDETERMINED = safe, no pay. Unavailable provider = DENY, never approval.

Pattern refs: primitives/claim-verification/implementations/genlayer/claim_verification.py, primitives/adjudicated-receipt/implementations/genlayer/adjudicated_receipt.py, contracts/self_driving_account.py.

## 2. Qualification test

From PRIMITIVE_QUALIFICATION.md: can a GenLayer dev consume this independently in >1 app class without reconstructing semantics? Failures become modules/patterns, not primitives. Each candidate below carries its falsifier.
## 3. Candidate 1 — unified-balance (multi-asset available capacity)

Problem: one spendable-balance notion across sub-accounts/assets without re-deriving available = balance - committed per app. PPA does it in-account; capital-commitment per pool+asset; claim-encumbrance per claimId. No reusable cross-asset invariant.

Meaning: deterministic capacity ledger generalizing reserve/commit/release/expire to account_id+asset. Owns backing, active sum, available_capacity() only.

Non-goals: no pool creation, no DAA adjudication, no Pact, no verification, no movement, no replay (cf. capital-commitment CAPABILITY doesNotOwn).

State: balance_id = account+asset+pool; RESERVED -> COMMITTED -> RELEASED|EXPIRED; immutable backing; available = backing - sum(active); exact integers; restore exactly once.

Invariants: every active commitment backed; backing unavailable while active; binds exact allocation/beneficiary/asset/amount/pool/validity; restore exactly once; creates no replay authority.

Authority: pool owner creates backing; beneficiary/owner mutates within validity; requires prior DAA/Pact; never authorizes movement/replay/encumbrance.

Judgment: NONE. Upstream policy/verification/DAA/FC supply conditions-precedent only.

Failure: reserveOnUnbacked / overCapacity / commitNonReserved / releaseTwice / expireBeforeValidity -> reject, mutate nothing. No auto Gaia case.

Composition: upstream daa, workflow-authorization, claim-verification, claim-encumbrance; downstream dal, financial-contract, settlement.

Prior art: ACTUS collateral (semantic), ERC-4626 (transport only), Safe balances. None enforce backed+unavailable+exact-restore as consensus machine.

Falsifier: if multi-asset is just a loop over capital-commitment + PPA.available with no new invariant, it is a pattern, not a primitive.

Provisional: QUALIFIED_EXTENSION at best — weakest of four.

## 4. Candidate 2 — unified-settlement (atomic claim application)

Problem: proof-of-payable marks ATTESTED->SETTLED but doesNotOwn settlement execution; financial-contract.apply_payment records but doesNotOwn fund transfer; ppa.send settles in-account. Nothing guarantees claim-state + obligation-application + capacity-release atomically.

Meaning: deterministic settlement-application: claim_id + contract_id + payment_id + amount applied atomically (PoP.settle + FC.apply_payment + encumbrance.settle/commitment.release). Owns only the application record.

State: settlement_id = payment_id; PREPARED -> APPLIED|DENIED; DENIED consumes no id, mutates nothing; APPLIED append-only; outstanding = principal - total_paid preserved.

Denials: EXCEEDS_OUTSTANDING, CLAIM_NOT_ATTESTED, CONTRACT_CLOSED/DEFAULTED/MATURED, INSUFFICIENT_COMMITMENT.

Invariants: overpayment denied not clipped; denied consumes no id; APPLIED immutable; claimId != proofHash; never creates authority/replay.

Authority: requires ATTESTED claim + ACTIVE contract + available commitment + DAL lane; settler proves lane authority.

Judgment: NONE. Interpretation upstream in claim-verification/policy-envelope.

Failure: partial execution impossible — all legs or none; unavailable dependency = DENIED (Art XII).

## 5. Candidate 3 — unified-obligation (netting / closeout)

Problem: financial-contract tracks one contract ACTIVE -> CLOSED|DEFAULTED with outstanding = principal - total_paid; gaia tracks OPEN -> CLASSIFIED -> RESOLVED append-only. Nothing nets multiple obligations between same parties or closes out on default without rewriting history (Art X).

Meaning: deterministic obligation-graph binding contract_ids + gaia case_ids + net_amount + version/lineage. Produces net statement + closeout record; never edits prior cashflows.

Non-goals: no per-contract accounting, no remedy execution, no authority, no custody.

State: obligation_set_id -> {members, cases, version, OPEN|NETTED|CLOSED_OUT}; amendments create new versions with supersession; history append-only.

Invariants: netting conserves sum(outstanding); closeout requires DEFAULTED or mutual Pact + Workflow Authorization; judgment cannot rewrite cashflows; remedy needs separate authorization; resolve requires all obligations dispositioned.

Authority: proposer needs Pact over all members; closeout needs creditor + Workflow Authorization; Gaia prescription alone authorizes nothing.

Judgment: SEMANTIC-adjacent. GenLayer MAY judge breach/covenants via claim-verification upstream; math + application deterministic. UNDETERMINED = no netting.

Failure: contradictory evidence stays observable; stale evidence cannot authorize netting; concurrent netting serializes via version check.

Composition: consumes financial-contract, gaia, workflow-authorization (Pact), proof-of-payable; feeds settlement.

Prior art: ACTUS closeout/netting, ISDA concepts — semantic only.

Falsifier: if FC + Gaia composition already covers netting with no new identity/lineage rules, collapse to pattern.

Provisional: SCOPE_PROVISIONAL — narrow like FC did (netting/closeout only; defer interest/fees/restructuring).

## 6. Candidate 4 — unified-attestation (fail-closed admissibility)

Problem: PPA embeds owner-registered technical attestations — fixed schema [subject, issuer, status, issued_at, expires_at, evidence_hash, policy_version], VALID|REVOKED, subject=recipient + issuer-in-allowlist + policy_version==, fail-closed. Useful beyond PPA (treasury, receivables, agents) but locked in-account.

Meaning: standalone admissibility evidence: register/revoke/get + check(subject, issuer, policy_version, time) -> ADMIT/DENY + reason. Owns attestation lifecycle only.

Non-goals: not legal KYC/AML, not substantive judgment, never moves money, not issuer identity verification.

State: attestation_id -> fixed fields; VALID -> REVOKED one-way; expiry at call time; unknown fields/PII rejected.

Denials: ATTESTATION_MISSING / SUBJECT_MISMATCH / REVOKED / INVALID_STATUS / ISSUER_UNAUTHORIZED / INVALID / EXPIRED / POLICY_MISMATCH.

Invariants: absent/stale/revoked/malformed/unavailable = DENY never approval; opaque fixed schema; revocation future-only; approval implies nothing beyond admissibility.

Authority: owner/issuer-controller registers/revokes; checker needs none; attestation never grants authority.

Judgment: NONE for gate. Substantive compliance belongs upstream (claim-verification / IAS-D).

Failure: outage = absent evidence; replayed old attestation fails expiry/policy; duplicate id rejected.

Composition: upstream none (owner input); downstream policy-envelope, ppa.send, daa, workflow-authorization.

Falsifier: if attestation is just a policy-envelope clause type, it is an extension, not a primitive.

Provisional: strongest QUALIFIED candidate — payments, treasury, receivables, agent commerce.

## 7. Worked example (illustrative, not normative)

Acme treasury holds 50,000 USDC, owed INV-1001 800 USDC receivable (PoP), owes LOAN-7 outstanding 10,000 (FC), rule: approved vendor + valid attestation. attestation.check -> ADMIT; balance.available -> 48,000; settlement.apply(INV-1001 800) -> PoP SETTLED + FC 10,000 -> 9,200 + encumbrance released atomically; dispute -> obligation nets LOAN-7 + gaia case -> compensating entry, history preserved.

## 8. Explicit NOT_IMPLEMENTED

Not custody/transfer; not authority (daa), replay (dal), or verification judgment; not legal KYC/AML; not history rewriting. Not a replacement for finishing Nomos: FC re-qual, PPA v0.2 extraction, adjudicated-receipt live proof, IAS-1 1.0 multi-build all remain unaffected.

## 9. Open research questions (Art VII)

1. Does unified-balance add invariant beyond capital-commitment + PPA.available? Experiment: 2 assets x 2 sub-accounts, show double-spend current primitives cannot express.
2. Can unified-settlement atomicity break under concurrent apply in ways app sequencing cannot prevent? Experiment: concurrent settlement vectors vs PoP+FC+encumbrance triple.
3. Minimal unified-obligation machine covering netting without absorbing FC/Gaia? Candidate: OPEN -> NETTED -> CLOSED_OUT with versioned membership only.
4. Is unified-attestation a primitive or policy-envelope clause? Experiment: consume checks from PPA send + DAA request with zero duplication.
5. Which candidate reaches SPECIFIED first without widening current lanes? Constraint: UF stays in research/unified-finance/** until dedicated WORK-UF-*.json accepted.

## 10. Promotion path

DISCOVERY (this doc) -> RESEARCHING (prior art + falsifiers + experiment, research/ only) -> SPECIFIED (SPEC+INVARIANTS+THREAT+DECISION_BOUNDARY + qualification entry) -> IMPLEMENTING (CAPABILITY + genlayer impl + vectors + docs) -> CONFORMANT (vectors + lint + direct/integration + adversarial + independent lane + receipt) -> RELEASED. No manifest/foundation changes authorized here.

Composition: upstream proof-of-payable, financial-contract, claim-encumbrance, capital-commitment, dal; downstream gaia.

Falsifier: if app-level sequencing enforces atomicity with no new shared state, it is docs, not a primitive.

Provisional: QUALIFIED candidate — receivables, treasury-usecase, lending.
