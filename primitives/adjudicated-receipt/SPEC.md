# Adjudicated Receipt - Canonical Specification

Status: CONFORMANT
Version: 0.1.0

## 1. Problem

Determine, for a registered economic object (invoice, obligation, milestone), whether tx-time-external evidence satisfies a natural-language release clause — deterministically enforceable afterwards — without letting evidence, models, or any single party move value.

Structural validity alone (schemas, signatures, addresses) cannot answer "was the service actually delivered?". Subjective committees reintroduce trusted intermediaries. Free-form model output wired to settlement reintroduces unbounded judgment into money movement.

## 2. Primitive Meaning

Adjudicated Receipt is the GenLayer-native settlement lock: it converts external evidence + a natural-language clause into a validator-quorum adjudication receipt whose bounded decision relation is the ONLY path to release value, and the ONLY release it authorizes is the single registered surrender value, once, while the evidence is fresh.

## 3. Non-Goals

- The primitive does not underwrite, price, or validate claim economics (composition: upstream Proof of Payable / Claim Verification / Mandate Allocation).
- The primitive does not enforce spending policy beyond the registered surrender value (composition: Policy Envelope).
- The primitive does not allocate authority to callers (composition: DAA / Workflow Authorization); settlement authority is owner-held in v0.1.
- The primitive does not reserve capital or move tokens (composition: Claim Encumbrance / Capital Commitment / PoP settle). v0.1 records an obligation release; token rails are an explicit NOT_IMPLEMENTED downstream surface.
- The primitive does not rectify, accelerate, or collect (composition: Gaia / Financial Contract).

## 4. Economic Object / State Model

Identity: `invoice_id` (stable, caller-chosen, 1..64 chars, unique per contract).
Lifecycle: `OPEN → SETTLED` (terminal). No other invoice states exist.
- `OPEN`: eligible for adjudication ticks and for settlement against an ACCEPTED receipt.
- `SETTLED`: terminal; no further adjudication, no further settlement.

Receipt identity: `receipt_id` (stable, caller-chosen, 1..64 chars, globally unique per contract).
Receipt lifecycle: recorded status is IMMUTABLE once written (`ACCEPTED` / `REJECTED` / `UNDETERMINED_*`), with exactly one mutable bit: `consumed` (`false → true`, one-way, at settlement only).

Payment identity: `pay-<receipt_id>` is derived deterministically from the consuming receipt.

Ownership: settlement is owner-held in v0.1 (see Falsifiers for the per-object authority generalization). Adjudication ticks are permissionless (liveness).

## 5. Inputs

Canonical environment-neutral inputs:

- `register_release(invoice_id, object_ref, surrender_value, surrender_asset, evidence_pointer, adjudication_clause, valid_for_seconds)`
- `adjudicate_object(invoice_id, receipt_id)`
- `settle_release(receipt_id)`

Identity rules: invoice ids unique; receipt ids globally unique; evidence digest is derived canonically from registered terms so substitution is detectable.

## 6. Outputs

Canonical environment-neutral outputs:

- `invoice_registered` + immutable invoice record `{invoice_id, object_ref, surrender_value, surrender_asset, evidence_pointer, adjudication_clause, registered_at, valid_for_seconds, status, evidence_digest}`.
- Receipt decision record: `{receipt_id, invoice_id, evidence_pointer, evidence_digest, verdict, confidence, status, reason_code, at, consumed}` where status is in `ACCEPTED | REJECTED | UNDETERMINED | UNDETERMINED_DELIVERY_UNCERTAIN`.
- Settlement record: `{payment_id = pay-<receipt_id>, invoice_id, to, amount, asset, receipt_id, status: SETTLED}` — the surrender value, no other amount possible.

## 7. State Transitions

Valid:

- `OPEN` invoice + fresh receipt id → adjudication tick → immutable receipt recorded.
- `ACCEPTED` + unexpired + unconsumed + binding-matched receipt → `SETTLED` (single consumption bit-flip + invoice terminal transition + payment record).
- `REJECTED` / `UNDETERMINED*` receipts → no transition authorized; invoice stays `OPEN` for re-adjudication.

Invalid (all must fail closed):

- adjudication against non-`OPEN` invoice or duplicate receipt id;
- settlement against missing, non-`ACCEPTED`, consumed, binding-mismatched, or TTL-expired receipts;
- settlement naming any amount, asset, payee, or invoice other than the registered/bound ones;
- any release not preceded by a quorum ACCEPTED record.

## 8. Invariants

Enumerated in `INVARIANTS.md` (testable statements). Core: no release without ACCEPTED; ACCEPTED requires (delivered, high) quorum agreement; exactly-once consumption; evidence/TTL binding; history append-only; uncertainty is never approval.

## 9. Authority Boundary

- Invoice registration and settlement: the account owner (v0.1).
- Adjudication ticks: permissionless — any caller may trigger; triggering confers no settlement right.
- Prior authority required: none beyond contract ownership for registration; an ACCEPTED receipt for settlement.
- This primitive can never authorize by itself: capital movement, policy changes, delegation, commitment, encumbrance, or rectification. It authorizes exactly one recorded release of the registered surrender value.

## 10. Judgment Boundary

Intrinsic judgment exists (evidence satisfaction is not reducible to deterministic computation without changing the problem):

- exact judgment question: "does the evidence fetched at adjudication time from the registered evidence_pointer satisfy the registered adjudication_clause for releasing this object?"
- admissible evidence: the byte content fetched in-transaction from the registered `evidence_pointer` (https). No other evidence is admissible.
- deterministic preconditions: invoice OPEN; receipt id fresh; contract initialized.
- structured decision schema: `{satisfied: bool, verdict: delivered|partial|not_delivered|ambiguous, confidence: high|medium|low, reason: string}`.
- equivalence/consensus requirement: independent validator re-fetch + re-judgment; leader and validator must agree on (satisfied, verdict, confidence); ACCEPTED additionally requires (satisfied=true, verdict=delivered, confidence=high).
- UNDETERMINED behavior: malformed output, consensus failure, partial delivery, or low confidence record terminal non-approval evidence; invoice stays OPEN.
- deterministic postconditions: immutable receipt; single-consumption settlement; TTL freshness enforced at adjudication-read AND settlement time.
- invariants judgment can never override: non-acceptance states; exactly-once; binding; TTL; history; owner-only settlement; the surrender value/asset/payee.

## 11. Failure Semantics

- Ordinary rejection: `REJECTED` (evidence not satisfying) — terminal for that receipt, invoice retryable with fresh evidence.
- Retryable failure: re-adjudication with a new receipt id while invoice OPEN; stale evidence requires re-registration first (new `registered_at` re-anchors the TTL).
- Exceptional state: `UNDETERMINED` / `UNDETERMINED_DELIVERY_UNCERTAIN` — observable uncertainty, never approval.
- Terminal failure: `SETTLED` — invoice closed; no corrective path inside this primitive (composition: Gaia prescribes new obligations; they flow through a new adjudication, never by editing this receipt).
- Exception handling creates no authority: raises precede every mutation; post-revert reads must show no phantom receipts or partial consumption.

## 12. Composition

- Typical upstream: `proof-of-payable` (claim identity), `claim-verification` (pre-adjudicated claim state), `mandate-allocation` (eligibility recommendation).
- Typical downstream: `policy-envelope` (spending policy on top of released value), `claim-encumbrance` / `capital-commitment` (back the released obligation), `gaia` (rectification of disputed releases → new adjudications), `financial-contract` (obligation lifecycle).
- Never inherits authority: settlement sets no policy, grants no delegation, reserves no capital, rectifies nothing.

## 13. Environment-Neutral Conformance Vectors

`vectors/v0.1.json`. Vectors target the deterministic envelope (registration identity, TTL freshness, binding, single consumption, non-acceptance immutability), executable with no LLM: any action whose expected outcome depends on a validator quorum verdict is adversarial-tested instead (see DECISION_BOUNDARY.md), because fixed vectors cannot be SEMANTIC for model prose.

## 14. Prior Art / Standards

- Semantic prior art: escrow release conditions; milestone-based procurement; insurance claim payout triggers; delivery-vs-payment.
- Transport/encoding standards: JSON records; canonical digest = ordered concatenation of registered terms (upgrade path: content hash of canonical JSON).
- Execution/account standards: GenLayer Intelligent Contracts (mandatory reference environment).
- Settlement/custody standards: none in v0.1 — token rails explicitly unsupported; release records are obligations, not transfers.
- Related but non-equivalent: ERC-7710 delegation (authority, not adjudication); oracle price feeds (deterministic data, not judgment); Claim Verification (verifies claims, settles nothing).

## 15. Security / Threat Model

Link `THREAT_MODEL.md`.

## 16. Falsifiers

- If the (delivered, high) acceptance bar proves unusable for a real invoice class (partial delivery is the norm), the decision relation needs a `PARTIAL` release tier — a capability-version change, not a silent relaxation.
- If evidence_pointer content cannot be made stable-addressable in practice, binding degrades to URL-only + TTL; the digest check then adds cost without security.
- If validator re-fetch shows systematic divergence (leader/validator see different web content), independence fails and equivalence must move to bounded-tolerance — a versioned change.
- If owner-only settlement proves too narrow for the first downstream (treasury bots, co-signers), authority generalizes to per-object settler bindings — a specified, vectored change.

## 17. Open Research Questions

- Canonical evidence content-hash vs URL+TTL binding strength on live validator networks.
- Exact-field vs bounded-tolerance validator equivalence for real-model prose.
- Cross-contract receipt consumption (v0.2): receipt in one contract, settlement in another, replay-safe across both.
- Token-rail settlement: who converts a release record into a transfer, and through which authorization.
