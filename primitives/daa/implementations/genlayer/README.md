# DAA — GenLayer Implementation Contract

Status: NOT_IMPLEMENTED

## Required GenLayer behavior

The GenLayer implementation must create a **bounded authority award**, not perform generic underwriting.

It must:

- receive an authority source/allocator, candidate beneficiary, governed resource/capital scope, requested authority bounds, purpose, policy/conditions, validity, and any optional upstream evidence/mandate result;
- enforce deterministic preconditions before judgment;
- use validator-mediated judgment only where the **allocation of authority itself** requires qualitative interpretation;
- return a structured authority-allocation decision;
- preserve `REJECTED` and `UNDETERMINED` as outcomes that create no authority;
- enforce deterministic postconditions on bounds, identity, resource scope, validity and uniqueness;
- store or emit an immutable `AllocationAward` / `AuthorityAllocation` object.

## Suggested structured result

```text
outcome: AWARDED | REJECTED | UNDETERMINED
beneficiary
maxAuthority
purpose
conditionsHash
validUntil
evidenceOrDecisionRoot
```

## Must never do

- act as a general credit-scoring engine;
- rank an open universe of opportunities as part of DAA semantics;
- replace Claim Verification;
- move funds from a judgment result;
- treat authority allocation as commitment or encumbrance;
- assign a DAL lane or nonce as part of the award;
- mutate unrelated pool accounting;
- hide validator disagreement behind approval.

## Required evidence

GenVM lint, direct tests, bounded-authority tests, identity/substitution tests, decision-boundary tests, canonical vectors, adversarial authority-allocation tests, integration tests, and deployment/CLI evidence.
