# Nomos Primitive Qualification

Purpose: determine whether each registered Nomos concept deserves to remain a first-class developer primitive for financial applications on GenLayer.

Qualification test:

> Can a GenLayer application developer consume this primitive independently in more than one class of financial application without reconstructing its economic semantics from scratch?

A primitive that fails this test should become an internal module, composition pattern, or application-specific layer rather than a public Nomos primitive.

## Results

| Primitive | Qualification | Why it is independently reusable | Immediate action |
|---|---|---|---|
| Proof of Payable | QUALIFIED | Payables/claims appear in receivables, trade finance, lending, insurance, procurement and agentic commerce. Stable claim identity + evidence lineage is reusable across all of them. | Define canonical claim/proof schema and lifecycle vectors. |
| Claim Verification | QUALIFIED | Many financial apps need a reusable way to turn heterogeneous evidence into a bounded, consensus-backed claim state. | Build first vertical reference implementation. |
| Policy Envelope | QUALIFIED | Spending, treasury, facility, insurance and agent workflows repeatedly need reusable deterministic + qualitative constraints. | Specify hard-vs-judgment policy boundary. |
| Workflow Authorization - Path + Pact | QUALIFIED | Delegated financial workflows repeatedly need standing authority plus specific accepted agreement. | Keep as one package with two explicit sub-primitives/interfaces. |
| Mandate Allocation | QUALIFIED_EXTENSION | Reusable across treasury, lending, insurance capacity, grants and portfolio construction, but it is an optional evaluation/recommendation layer rather than a universal financial dependency. | Keep public but lower priority than authority/accounting primitives. |
| Dynamic Authority Allocation (DAA) | QUALIFIED | Reusable whenever a financial system must create a bounded authority grant over scarce capital/resource. | Preserve strict separation from underwriting and commitment. |
| Claim Encumbrance | QUALIFIED | Preventing over-financing/double-use of the same economic claim is reusable across receivables, secured lending and structured finance. | Define deterministic capacity accounting. |
| Capital Commitment | QUALIFIED | Financial apps repeatedly need to distinguish permission/allocation from economically reserved backing capacity. | Define reservation/backing invariants. |
| Dynamic Authorization Lanes (DAL) | QUALIFIED | Any system with multiple independently valid signed/delegated authorizations can need authorization-scoped replay domains. | Preserve as deterministic authorization infrastructure. |
| Financial Contract | QUALIFIED | Re-qualified 2026-10-11 after the directed narrowing (Aug 2026) to an obligation/cash-flow lifecycle: principal conservation, deterministic payment application, maturity, closure, creditor-declared default. Lending, trade finance, structured finance, and any post-drawdown obligation tracking consume the same state machine. Interest/fees/covenants/restructuring remain deferred to future capability versions with declared judgment boundaries. | Keep as the canonical obligation-lifecycle primitive; extend only via versioned capability changes. |
| Gaia | QUALIFIED | Dispute, exception, reconciliation and rectification recur across financial apps and need consistent append-only, authorization-preserving semantics. | Keep cross-cutting and independent from execution authority. |
| Programmable Payment Account | QUALIFIED_EXTENSION | Re-qualified 2026-10-11: the user-facing composite account (policy → attestation → encumbrance → claim → settle) is independently consumable by wallets, treasuries, payroll, and agent-commerce apps without reconstructing gate semantics; it is a composition product, not part of the minimum dependency chain. | Keep public; v0.2 cross-contract extraction restores per-primitive attestation chains. |
| Adjudicated Receipt | QUALIFIED | Re-qualified 2026-10-11: the GenLayer-native settlement lock (quorum adjudication over tx-time external evidence + challenge window + exactly-once release) is reusable by escrow, milestone procurement, insurance triggers, and delivery-vs-payment flows. | Keep as the judgment-bearing settlement-lock primitive; token rails remain an explicit downstream surface. |

## Consequence

Thirteen primitives qualify as public Nomos developer building blocks (2026-10-11):

- `Financial Contract` was narrowed (Aug 2026) to an obligation/cash-flow lifecycle and re-qualified (Oct 2026) on the implemented v0.1.0 surface: 9/9 canonical vectors, independent convergence lane 9/9, creditor-authority direct tests, and live GLSim payment-cycle evidence.
- `Programmable Payment Account` qualifies as an extension primitive: a composition product, public and reusable, but not part of the minimum dependency chain for consuming the underlying primitives.
- `Adjudicated Receipt` qualifies as the judgment-bearing settlement-lock primitive; its quorum/challenge/finalize/settle lifecycle is proven in direct mode (13/13) and its deterministic envelope plus consensus-path adjudication on GLSim; post-window finalization is BLOCKED on the current GLSim frozen-clock build and tracked as such.

`Mandate Allocation` qualifies as an extension primitive: public and reusable, but not part of the minimum dependency chain for the first Nomos reference application.

## First reference vertical slice

Claim Verification is the first implementation benchmark because it exercises the GenLayer capabilities Nomos must use correctly:

```text
canonical financial claim
        ↓
heterogeneous evidence
        ↓
Intelligent Contract
        ↓
non-deterministic evidence interpretation
        ↓
Equivalence Principle
        ↓
Optimistic Democracy validation
        ↓
structured canonical decision
        ↓
deterministic state update
        ↓
SDK / application consumption
```

The resulting implementation pattern becomes the template for judgment-bearing Nomos primitives. Deterministic primitives reuse the packaging, conformance, SDK and receipt conventions without inventing non-deterministic judgment.
