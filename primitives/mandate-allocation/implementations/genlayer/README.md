# Mandate Allocation — GenLayer Implementation Contract

Status: NOT_IMPLEMENTED

## Required GenLayer behavior

- Receive a canonical mandate, deterministic hard constraints, candidate/opportunity set, and admissible evidence.
- Interpret qualitative mandate terms only inside the declared judgment boundary.
- Compare admissible opportunities and return structured recommendation results.
- Preserve `UNDETERMINED` and evaluator disagreement.
- Bind results to exact mandate/evidence/candidate versions.
- Enforce deterministic ceilings before exposing recommended amounts.

## Suggested structured result

```text
outcome: RECOMMENDED | REJECTED | UNDETERMINED
candidateRef
recommendedAmount
priorityClass / rank
conditionsHash
evidenceRoot
mandateHash
validUntil
```

## Must never do

- issue executable authority;
- impersonate DAA;
- reserve or commit capital;
- encumber claims;
- assign DAL lanes;
- directly move value;
- turn `UNDETERMINED` into recommendation.

## Required evidence

GenVM lint, direct tests, mandate-interpretation tests, comparative-stability tests, contradictory-evidence tests, canonical vectors, integration tests, and deployment/CLI evidence.
