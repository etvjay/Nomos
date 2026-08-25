# IAS-1: The Intelligent Account Standard

**Draft 0.1 - August 2026**
**Nomos Project · for GenLayer**

---

## 0. Abstract

GenLayer has two account types: Externally Owned Accounts (key-controlled) and
Intelligent Contract Accounts (code deployed at an address). Both are inert.
Neither can hold spending rules, grant scoped authority, process evidence-
bearing payments, dispute its own history, or safely host an AI agent -
unless every developer re-invents those mechanisms ad hoc, and gets them
wrong in new ways.

Ethereum solved the equivalent gap with **smart accounts** (ERC-4337): accounts
whose authorization logic is programmable. But smart accounts only abstract
*signature verification and transaction flow*. Their rules are written in
rigid code, and their holders cannot reason.

IAS-1 defines the next account type: the **Intelligent Account** - a GenVM-
native account standard with five composable modules (Authority, Policy,
Settlement, Judgment Interface, Rectification) and one inviolable invariant:

> **Judgment proposes; determinism disposes.**

AI may observe, classify, and propose actions inside an Intelligent Account.
It may never move funds, override a gate, or rewrite history. The line is not
a policy preference; it is enforced by the account's own execution semantics.

---

## 1. Motivation

### 1.1 What smart accounts gave us - and what they lack

Smart accounts (ERC-4337, Safe, and successors) made authorization
programmable: social recovery, batched calls, session keys, spend limits,
gas abstraction. Three limits define their ceiling:

1. **Rules are code-only.** A spending policy can check amounts and
   counterparties, but cannot interpret evidence ("was this delivered?"),
   read external reality ("has the oracle window closed?"), or understand
   intent expressed in language.
2. **Delegation is static.** Session keys expire by time or block height;
   they cannot be conditioned on observed state, and they carry no replay
   discipline beyond nonces.
3. **No native dispute lifecycle.** When a payment goes wrong, resolution
   lives outside the account.

### 1.2 Why GenLayer changes the possible

GenLayer's Optimistic Democracy lets Intelligent Contracts reach consensus on
*non-deterministic* outputs - LLM reasoning over web data, classification of
unstructured facts - with validator diversity and appeal finality. This makes
judgment *settleable* for the first time: not trusted to one model, but agreed
by many.

That capability creates the temptation this standard exists to prevent:
putting judgment directly in the money path. An account whose model can be
prompted into releasing funds is worse than a dumb account.

The correct synthesis: **accounts that think, gated by code that counts.**

### 1.3 Prior art within GenLayer

The mechanisms IAS-1 composes were proven separately as Nomos primitives
(deployed on Testnet Bradbury):

| Mechanism | Primitive | Proven |
|---|---|---|
| Scoped authority allocation | Dynamic Authority Allocation | vectors + tests |
| Replay-scoped execution lanes | Dynamic Authorization Lanes | vectors + tests |
| Pact-based workflow authorization | Workflow Authorization | vectors + tests |
| Deterministic policy gates | Policy Envelope | vectors + tests |
| Evidence-bearing settlement | Proof of Payable | vectors + tests |
| Capacity reservation | Claim Encumbrance | convergence receipts |
| Dispute rectification | Gaia | vectors + tests |

Composite proof: the Programmable Payment Account implemented all of the
above in-account and executed its full payment lifecycle on Testnet Bradbury.

---

## 2. The standard

An Intelligent Account is any GenLayer contract implementing the five modules
below, honoring the Invariant, and exposing the Core Interface.

### Module A - Authority

*Who may act, with what scope, until when.*

- **A1 Owner.** Exactly one controller; the only principal that can change
  rules, resolve disputes, revoke delegations, or withdraw.
- **A2 Delegations.** Named grants to principals carrying: per-action limit,
  period limit, expiry, and optional domain restriction. Two invariants:
  - *Narrowing:* a delegate's effective cap is the minimum of delegation and
    account policy. Delegation never widens authority.
  - *Termination:* revocation is immediate; expiry is evaluated at call time
    against block time - silent, exact, no keeper required.
- **A3 Execution lanes (replay discipline).** Time-windowed lanes with
  monotonic nonces: each authorization is single-use within its domain,
  atomically consumed, immune to replay even by the delegate itself.
  *(Drawn directly from DAL: `open_lane` / `exercise` / nonce advancement.)*

### Module B - Policy

*Deterministic gates evaluated before any state mutation.*

- **B1 Rules envelope.** Per-account: per-action limit, periodic limit with
  rolling window, recipient allowlist/denylist, currency/asset scope,
  attestation requirement flag.
- **B2 Gate ordering.** Gates evaluate in fixed order (policy → encumbrance →
  claim → settle); no gate may be skipped and no later gate may authorize what
  an earlier gate denied.
- **B3 Auditable denials.** Denials are permanent records (reason code,
  timestamp) that consume no funds and do not burn request identifiers -
  rule changes are safely testable by retry.

### Module C - Settlement

*Evidence-bearing value movement.*

- **C1 Committed/available split.** The ledger tracks balance, committed, and
  available (= balance − committed). Overcommitment is structurally
  impossible.
- **C2 Payment claims.** Every settlement produces a claim record: parties,
  amount, evidence hash, memo, actor identity, status. Ledger lines alone are
  insufficient; settlement must be verifiable after the fact.
- **C3 Immutable history, compensating recovery.** Confirmed records are never
  rewritten. Corrections (refunds) are new compensating entries linked to the
  original.

### Module D - Judgment Interface

*Where intelligence enters - bounded.*

- **D1 Observation.** The account may consume consensus-verified external
  facts (web data, metrics) produced via comparative equivalence - validators
  agree on extracted values within declared tolerance.
- **D2 Classification.** Structured decisions over unstructured input
  (e.g., dispute category, clause interpretation) may be produced by LLM
  consensus under a declared decision relation (SEMANTIC convergence).
- **D3 Proposals.** Judgment output may *create a proposed action* that then
  passes Modules B and C like any other action.
- **D4 The Line (invariant).** No judgment output may: debit or credit a
  balance, bypass a policy gate, alter authority, mutate history, or waive a
  denial. Judgment's only power is proposal. **Enforcement is structural:**
  proposal paths terminate in the same gate pipeline as human-initiated ones.

### Module E - Rectification

*When settled things go wrong.*

- **E1 Case lifecycle.** Declared economic categories; OPEN → CLASSIFIED →
  RESOLVED with premature-resolution blocked.
- **E2 Remedies.** refund (compensating entry), waive, reject. Original
  records annotated, never mutated.
- **E3 Resolution authority.** Owner-only; classification (which category)
  may be judgment-sourced via D2.

### The Core Interface

```python
class IIntelligentAccount(gl.Contract):
    # --- Authority ---
    def initialize(owner: Address) -> str: ...
    def delegate(delegation_id: str, principal: Address,
                 per_action_limit: str, period_limit: str,
                 expires_epoch: int, domains: list[str]) -> str: ...
    def revoke_delegation(delegation_id: str) -> str: ...

    # --- Settlement ---
    def deposit(sub_account_id: str, amount: str) -> str: ...
    def withdraw(sub_account_id: str, amount: str) -> str: ...
    def send(sub_account_id: str, payment_id: str, to: Address,
             amount: str, evidence_hash: str = "", memo: str = "") -> dict: ...

    # --- Rectification ---
    def open_dispute(dispute_id: str, payment_id: str,
                     category: str, facts_json: str) -> str: ...
    def resolve_dispute(dispute_id: str, remedy: str) -> str: ...

    # --- Views (minimum surface) ---
    def get_account(sub_account_id: str) -> dict: ...
    def get_payment(payment_id: str) -> dict: ...
    def get_delegation(delegation_id: str) -> dict: ...
    def get_dispute(dispute_id: str) -> dict: ...

    # --- Judgment Interface (optional module D; MUST honor D4 if present) ---
    def submit_proposal(proposal_id: str, source: str,
                        payload_json: str) -> str: ...
```

Implementations MAY add methods. They MUST NOT expose any path that mutates
balances, authority, or history except through the gate pipeline (D4).

---

## 3. Drawn from the primitives: what each contributes

### From DAL - replay-scoped execution

DAL's contribution is the hardest-won insight in the stack: **authority must
be single-use at the execution layer, not just time-boxed.** A session key
that expires tomorrow can still be replayed ten times today. DAL's lane model
(issuer + domain + monotonic nonce, atomic consumption, fail-closed denials
that mutate nothing) becomes IAS-1 §A3. Every delegated action consumes exactly
one lane nonce; replays are structurally impossible rather than detected.

Sharpening applied: lanes bind to *domains* (what kind of action), not just
identities - so "the agent may make three settlement calls" is expressible
without allowing three arbitrary calls.

### From DAA - authority as allocated capacity

DAA's contribution: authority is **awarded against a declared maximum**, and
the award is a distinct, auditable state transition (REQUESTED → AWARDED →
REVOKED/EXPIRED) from the exercise of that authority. IAS-1 §A2 inherits the
award/revoke lifecycle and the max-capacity bound. Sharpening applied: DAA's
"award does not imply usage; usage does not extend award" separation maps to
delegation limits being independent of actual spend, and expiry never resets
on activity.

### From Workflow Authorization - the pact between proposal and execution

Workflow Authorization separates *proposing* a pact (anyone) from *accepting*
it (principal only) from *executing* it (within path validity). This is the
exact shape of the Judgment Interface: AI proposals are pacts proposed to the
account; acceptance and execution remain deterministic. Sharpening applied:
path validity windows become proposal TTLs - stale intelligence cannot execute.

### From Policy Envelope - deny without consuming

The denied-request pattern (recorded, fund-free, retryable) came from testing
policy-envelope live: burning request ids on denial made rule changes
untestable. IAS-1 §B3 standardizes it.

### From Proof of Payable + Claim Encumbrance - settlement with memory

Claims carry evidence hashes; encumbrance splits committed from available.
Together they mean every settlement is post-hoc verifiable and no payment can
strand another. IAS-1 §C inherits both.

### From Gaia - rectification without revision

Gaia proved the case lifecycle and the compensating-entry refund. IAS-1 §E
standardizes both, plus the category taxonomy boundary: categories are
declared inputs, so classification can be judgment-sourced without judgment
entering resolution.

---

## 4. Comparison with existing account standards

| Capability | EOA | Smart Account (ERC-4337) | **Intelligent Account (IAS-1)** |
|---|---|---|---|
| Programmable auth | ✗ | ✓ (signatures) | ✓ (owner + scoped delegation) |
| Spend limits | ✗ | ✓ (static) | ✓ (deterministic + narrowing) |
| Session/scoped keys | ✗ | ✓ (time-based) | ✓ (time + replay-lane + domain) |
| Recovery | social | social/guardians | owner + dispute lifecycle |
| Reads external world | ✗ | ✗ | ✓ (consensus-verified observation) |
| Classifies unstructured input | ✗ | ✗ | ✓ (SEMANTIC consensus, bounded) |
| Proposes actions | ✗ | ✗ | ✓ (gated proposals) |
| Judgment moves funds | n/a | n/a | **✗ - structural invariant** |
| Native dispute lifecycle | ✗ | ✗ | ✓ (cases + remedies) |
| Replay-proof delegation | ✗ | partial (nonces) | ✓ (lane nonces, atomic) |

---

## 5. Threat model highlights

- **Prompt injection → fund movement:** blocked by D4. Injected content may
  reach the judgment interface; its output can only become a proposal, which
  passes the same deterministic gates as everything else. Worst case: a
  denied-payment record.
- **Delegate runaway:** per-action + periodic caps, lane nonces (no replay),
  immediate revocation, expiry at block time.
- **Concurrent requests:** encumbrance split serializes capacity; lane nonces
  serialize delegated execution.
- **Stale authority:** expiry evaluated against block time at call time; no
  keeper, no grace period.
- **Partial execution:** gate pipeline is ordered; a failure at gate N leaves
  state exactly as after gate N−1 (denials write audit records only).

---

## 6. Conformance

An implementation is IAS-1 conformant when:

1. All five modules are present (D may be minimal but must exist as a defined
   boundary, even if empty);
2. The D4 invariant holds under adversarial test (attempted judgment-driven
   transfer must fail);
3. Canonical interface methods behave per §2 semantics;
4. The implementation passes its published vector suite and declares its
   conformance level:

   - **IAS-1-Basic:** A + B + C (deterministic account)
   - **IAS-1-Full:** A + B + C + D + E (with live judgment composition)

(The Nomos PPA is the reference implementation of IAS-1-Full minus deployed
cross-contract composition; its six-flow live test suite and Bradbury
deployment receipt constitute the first conformance evidence.)

---

## 7. Roadmap

- **0.2** - cross-contract extraction (modules call the deployed primitive
  contracts), restoring per-primitive convergence attestation chains.
- **0.3** - x402 facade (HTTP 402 flows settle through the gate pipeline) and
  ERC-7710-style export of delegations for EVM-side composability.
- **1.0** - multi-implementation conformance: at least two independent builds
  passing identical canonical vectors, per the Nomos repository-mediated
  convergence protocol.

---

*Nomos - financial primitives whose semantics survive any builder.*
