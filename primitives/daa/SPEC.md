# Dynamic Authority Allocation (DAA) - Canonical Specification

Status: RESEARCHING
Version: 0.2.0

## 1. Problem

Independent economic actors need a protocol-level way to create bounded authority over capital or another economic resource without collapsing that authority into underwriting, capital reservation, nonce management, or settlement.

## 2. Primitive Meaning

**Dynamic Authority Allocation (DAA) is a protocol for determining which actor receives bounded authority over which capital or economic resource, for which purpose, under which terms, constraints, and validity.**

Its canonical output is an `AuthorityAllocation` / `AllocationAward`: an immutable statement that a particular actor has been granted a particular bounded authority.

DAA answers:

```text
WHO receives authority?
OVER WHAT capital/resource?
FOR WHAT claim/purpose?
UP TO WHAT bound?
UNDER WHAT policy/conditions?
FOR HOW LONG?
```

DAA does **not** answer whether a borrower is creditworthy in the abstract, rank every financing opportunity, reserve the capital, assign a replay lane, or move funds.

## 3. Non-Goals

DAA is not:

- a credit-scoring or underwriting engine;
- a general mandate-ranking engine;
- Claim Verification;
- Claim Encumbrance;
- Capital Commitment;
- Dynamic Authorization Lanes;
- settlement or custody.

The separate **Mandate Allocation** primitive may evaluate/rank opportunities under a financing mandate. DAA may consume that result, but the result does not become authority until DAA creates the bounded allocation.

## 4. Canonical Object

A DAA award should minimally bind:

```text
allocationId
allocator / authoritySource
beneficiary
resource / capitalPool
asset or resource class
maxAuthority / maxPrincipal
purpose / facilityClass
claimId?                 # when claim-backed
evaluatedEvidenceHash?   # when evidence-bound
policyHash
conditionsHash?
validAfter
validUntil
provenance / decisionRef
```

The exact serialization is environment-specific; the semantic bindings are not.

## 5. State Model

```text
REQUESTED
   ↓
EVALUATING
   ├──→ AWARDED
   ├──→ REJECTED
   └──→ UNDETERMINED

AWARDED
   ├──→ EXPIRED
   └──→ REVOKED   # only where revocation semantics are explicitly supported
```

A finalized award is immutable. Re-allocation creates a new award/version rather than rewriting the old one.

## 6. Core Invariants

- An award is a bounded authority grant, not merely a recommendation.
- An award must identify its authority source and beneficiary.
- An award must identify the resource/capital scope and purpose it governs.
- Authority bounds and validity must be explicit.
- An award may not exceed deterministic limits supplied by the authority source or resource state.
- `REJECTED` and `UNDETERMINED` create no authority.
- Award creation does not reserve capital.
- Award creation does not encumber a claim.
- Award creation does not assign a nonce/replay lane.
- Award creation does not itself move value.
- Downstream execution must prove that the requested action is within the award.

## 7. Judgment Boundary

NONE for the v0.1 canonical slice. The allocation of authority is expressed through deterministic predicates supplied by the authority source. Qualitative mandate interpretation belongs to upstream Policy Envelope / Claim Verification consumed before requesting; its result can never relax the deterministic gates here (bound escalation is structurally impossible).

### v0.1 classification change (Article XVI record)
v0.1-draft declared DAA judgment-capable (SEMANTIC). Accepted v0.1 ships the deterministic allocation state machine with externalized judgment. Compatibility: additive; no prior release consumed a SEMANTIC DAA surface.

DAA may use GenLayer when **the allocation of authority itself** requires judgment-for example, interpreting a qualitative authority mandate or resolving which already-admissible actor should receive a bounded grant.

DAA MUST NOT absorb upstream underwriting merely because GenLayer can perform it. Creditworthiness, evidence verification, broad opportunity ranking, and mandate analysis belong to Claim Verification and/or Mandate Allocation.

Regardless of judgment, the following remain deterministic:

- authority-source identity;
- requested and maximum bounds;
- resource/capital capacity supplied to DAA;
- award uniqueness/versioning;
- validity windows;
- downstream encumbrance, commitment, replay and settlement invariants.

## 8. Composition

Typical composition:

```text
Claim / Opportunity
      ↓
Claim Verification
      ↓
Policy / Mandate
      ↓
Mandate Allocation?   # optional upstream evaluation/ranking
      ↓
DAA
      ↓
Bounded Authority Award
      ↓
Pact / Claim Encumbrance / Capital Commitment
      ↓
DAL
      ↓
Execution
```

DAA precedes DAL conceptually:

```text
DAA = what bounded authority exists
DAL = how independently granted authority is exercised without false replay ordering
```

## 9. Research Boundary

Do not present DAA as the conceptual successor to DAL. They solve different layers of the authority lifecycle. DAA creates/allocates authority; DAL supplies authorization-scoped replay/execution domains after authority exists.
