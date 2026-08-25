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
| Financial Contract | SCOPE_PROVISIONAL | The category is reusable, but "Financial Contract" is too broad to expose as a safe developer primitive without a narrower canonical state machine. | Do not implement until the reusable state model is narrowed. Candidate direction: obligation/cash-flow lifecycle rather than generic finance logic. |
| Gaia | QUALIFIED | Dispute, exception, reconciliation and rectification recur across financial apps and need consistent append-only, authorization-preserving semantics. | Keep cross-cutting and independent from execution authority. |

## Consequence

Ten primitives currently qualify as public Nomos developer building blocks. `Financial Contract` was narrowed (Aug 2026) to an obligation/cash-flow lifecycle and entered implementation as v0.1.0 SPECIFIED/EXACT.

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
