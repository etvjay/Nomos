# Mandate Allocation — Canonical Specification

Status: RESEARCHING
Version: 0.1.0

## 1. Problem

Capital allocators often express financing mandates that combine deterministic constraints with qualitative preferences, comparative judgment, and heterogeneous evidence. Applications need a way to evaluate and rank opportunities against such a mandate without confusing recommendation with authority.

## 2. Primitive Meaning

**Mandate Allocation evaluates one or more admissible opportunities against a financing/capital mandate and returns a structured recommendation, ranking, or bounded allocation suggestion.**

It answers:

```text
Which opportunities satisfy this mandate?
How do they compare?
What amount or priority should be recommended?
What conditions or reservations should accompany that recommendation?
```

Its output is advisory/evaluative. It creates **no executable economic authority**.

## 3. Non-Goals

Mandate Allocation does not:

- grant authority;
- reserve capital;
- encumber claims;
- assign replay lanes;
- move funds;
- replace DAA.

A Mandate Allocation result may feed DAA. DAA is the protocol step that converts an accepted allocation decision into bounded authority.

## 4. Canonical Output

A result may bind:

```text
mandateAllocationId
mandateHash
candidate / opportunity refs
eligibility
recommendedAmount
rank / score class
conditionsHash
reason/evidence root
validUntil
```

## 5. Judgment Boundary

GenLayer is the mandatory reference implementation and is particularly relevant where mandate interpretation, contradictory evidence, comparative ranking, qualitative risk, or natural-language policy requires validator-mediated judgment.

Deterministic hard constraints remain deterministic.

## 6. Core Invariants

- Result is not authority.
- Result is not commitment.
- Result is not encumbrance.
- Result cannot move value.
- Result must bind the exact mandate and evaluated evidence/opportunities.
- `UNDETERMINED` cannot be treated as approved.
- DAA must independently create any downstream authority grant.

## 7. Composition

```text
Claim / Opportunity
      ↓
Claim Verification
      ↓
Policy / Mandate
      ↓
Mandate Allocation
      ↓ recommendation only
DAA
      ↓ authority grant
DAL / downstream execution
```
