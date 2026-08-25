# IAS-1 v0.2 - Account Role Profiles (Catalog Draft)

**The Intelligent Account type system: one core, composable role profiles.**

Every profile is a named configuration of the five IAS-1 modules
(Authority, Policy, Settlement, Judgment Interface, Rectification).
An account may hold multiple profiles simultaneously; profiles define the
interfaces shown to counterparties, not separate contracts.

---

## The dimensions behind every profile

| Dimension | Question it answers |
|---|---|
| Holds | What does this account contain? (capital, claims, orders, slots, access, attestations, sub-accounts) |
| Acts for | Whose interest does it serve? (self, beneficiary, principal, counterparties) |
| Governed by | How is authority exercised? (owner key, clauses, roles, judgment-adaptive, keyless) |
| Emits | What does it publish? (payments, demands, attestations, access grants) |

---

## The catalog

### 1. Payment Account (PPA)
- **Holds:** capital · **Acts for:** self/owner · **Emits:** payments
- **Does:** holds committed capital; moves it only through the four deterministic gates (policy → encumbrance → claim → settle). Invoices settle through payer-side gates. Disputes resolve via compensating entries.
- **Status:** implemented, live-verified on Bradbury. The reference profile.

### 2. Merchant Account
- **Holds:** capital + receivables + refund reserves · **Acts for:** self · **Emits:** invoices, receipts, refund payments
- **Does:** payee-side commerce. Published payment identity; invoice lifecycle as first-class state; settlement batching; refund reserves encumbering incoming revenue so refund liability is always covered; dispute-rate stats exposed.
- **New mechanism needed:** refund-reserve encumbrance on inbound revenue.

### 3. Agent Account
- **Holds:** delegated capital only · **Acts for:** a principal · **Governed by:** lanes only - no owner-key co-tenancy
- **Does:** fully agent-native occupancy. Authority exclusively via delegation lanes (caps/expiry/replay-proof); principal attestation hook binding agent to owner; kill switch defaults off; cannot self-grant authority.
- **Constitution inherited from OpenRails guardrails:** agents do not receive private keys, do not approve their own authority, do not claim success without verifiable evidence.

### 4. Trustee Account
- **Holds:** assets owned by a beneficiary · **Acts for:** beneficiary · **Owes:** accounting and duty of care
- **Does:** fiduciary custody - escrow agent, custodian, DAO treasurer, executor. Committed-vs-available segregation is trustee duty; gaia is the beneficiary's remedy path; workflow pacts are the trust terms.
- **New mechanism needed:** beneficiary rights as first-class state - inspect, demand accounting, revoke-for-cause via gaia.

### 5. Attestation Account
- **Holds:** nothing (or minimal stake) · **Emits:** signed statements about things
- **Does:** issues verifiable assertions other accounts consume without re-running consensus: evidence verification ("this hash checks out"), identity bindings ("this address ↔ this email/DID"), published facts ("as of T, metric = X"), reputation ("passed review R"). Includes a revocation list.
- **Engine:** claim-verification + monitors become sensors; the account signs and publishes.

### 6. Order Account
- **Holds:** standing/limit/scheduled orders against capital elsewhere · **Emits:** order fills
- **Does:** orderbook participant semantics - limit orders, recurring payments, scheduled transfers. Orders are encumbrances on a linked Payment Account; fills route through its gates.

### 7. Demand Account
- **Holds:** claims owed TO it · **Emits:** payment demands, calls on obligation
- **Does:** the collector side of commerce - receives demands lifecycle, tracks aging, escalates to gaia when obligations go unpaid. Counterpart of Merchant.

### 8. Agreement Account
- **Holds:** terms, not capital · **Acts for:** two parties simultaneously · **Emits:** pact state changes
- **Does:** OpenRails' Pact promoted to accounthood - a bilateral agreement as an on-chain entity with its own lifecycle (proposed → accepted → active → fulfilled/breached), holding both parties' obligations and the evidence schema that governs them.

### 9. Slot Account
- **Holds:** reservable capacity (time, inventory, bandwidth, seats) · **Emits:** bookings, confirmations
- **Does:** makes bookable capacity a ledger object. Slots are claims on future capacity; booking = encumbrance; cancellation = compensating entry. Enables appointment/scheduling markets on the same rails as money.

### 10. Access Account
- **Holds:** capability grants (permissions, content, API scopes, physical access) · **Emits:** access grants/revocations
- **Does:** non-monetary authorization through the same gate pipeline. "Grant access" is a gated action like "send"; revocation is immediate; judgment can propose access changes but never grant directly.

### 11. Keyless Account
- **Holds:** anything · **Governed by:** NO private key exists
- **Does:** authority purely through lanes, delegations, and attestation chains. Fully agent-native or custody-service-native. Recovery via social/gaia paths rather than key backup. The strongest form of the "agents don't get keys" principle.

### 12. Clause Account
- **Holds:** attached clauses that define behavior · **Governed by:** the clauses themselves
- **Does:** policy-envelope-as-account - behavior is entirely clause-driven; add/remove clauses (via governance) to reshape the account. The purest expression of "rules as data."

### 13. Dynamic Account
- **Holds:** anything · **Governed by:** rules that change at runtime
- **Does:** Module D applied to Module B - judgment proposes rule reconfigurations; deterministic dispose applies them within declared bounds. The shape-shifter: risk parameters evolve with observed reality, never by direct model mutation.

### 14. Compositor (Account of Accounts)
- **Holds:** sub-accounts · **Acts for:** the hierarchy · **Emits:** consolidated views, portfolio actions
- **Does:** the root object - Workspace-meets-PPA. Portfolio-level policies, consolidated audit, hierarchical authority (OpenRails Workspace integration). An account whose balance sheet includes other accounts.

### 15. Role Account *(meta)*
- **Does:** declares/enumerates which profiles it currently plays; the registry entry point for discovery. Any account can expose this view; it's how counterparties learn what interfaces an account supports.

---

## Composition rules

1. Profiles stack: an account can be Merchant + Keyless + Attestation issuer simultaneously.
2. Conflict rules apply (e.g., Trustee + Attestation-about-trusted-assets requires disclosure).
3. Every profile maps to specific module configurations and Nomos primitive dependencies.
4. Counterparty interfaces are the standardization surface: two accounts interoperate by declaring profiles, not matching implementations.
