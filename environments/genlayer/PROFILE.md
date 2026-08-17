# GenLayer Environment Profile

Role: **reference judgment substrate** for Nomos primitives whose semantics intrinsically require non-deterministic evidence evaluation, natural-language interpretation, or validator-mediated judgment.

## Mapping

- deterministic preconditions: `NATIVE`
- Intelligent Contract judgment: `NATIVE`
- validator/equivalence resolution: `NATIVE`
- canonical structured decision: `NATIVE`
- deterministic postconditions/state: `NATIVE`
- EVM-side external settlement: `ADAPTER` or `EXTERNAL` depending on topology
- non-GenLayer cross-chain finality: `EXTERNAL`

## Constitutional boundary

GenLayer may answer bounded judgment questions. It does not gain authority to bypass capacity, identity, replay, encumbrance, commitment, expiry, authorization or settlement invariants.

Every judgment-bearing implementation must expose:

1. exact judgment question;
2. admissible evidence;
3. deterministic preconditions;
4. structured output schema;
5. equivalence/consensus criterion;
6. `UNDETERMINED` path;
7. deterministic postconditions;
8. invariants judgment cannot override.

## Required verification stack

Use the official GenLayer tooling/skills available in the working environment for:

- Intelligent Contract authoring;
- GenVM linting;
- direct tests;
- integration tests;
- documentation/source verification;
- CLI/deployment checks.

These supplement, not replace, Nomos canonical conformance vectors and adversarial experiments.

## Reject

- free-form LLM output directly moving unrestricted value;
- deterministic accounting delegated to subjective judgment without necessity;
- `UNDETERMINED` treated as approval;
- validator disagreement hidden behind permissive defaults;
- GenLayer-specific state shape silently redefining the canonical primitive.
