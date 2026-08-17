# Offchain Environment Profile

Role: reference models, evaluators, APIs, indexers, simulators, policy engines, orchestration and integration runtimes.

## Mapping

- deterministic reference computation: `NATIVE`
- durable economic finality: `EXTERNAL` unless backed by an explicitly named persistence/consensus system
- signatures/authentication: `ADAPTER`
- external data retrieval: `NATIVE` or `ADAPTER`
- subjective evaluation: `NATIVE` but trust model MUST be explicit
- settlement/custody: `EXTERNAL` unless the runtime explicitly owns those capabilities

## Required trust disclosure

Every offchain implementation must state:

- who operates it;
- where authoritative state lives;
- persistence and recovery assumptions;
- authentication/signature model;
- external source trust;
- whether results are advisory, attested, or authoritative;
- how replay/idempotency is enforced;
- what happens during partial failure or restart.

## Constitutional boundary

An offchain service may implement the same primitive semantics, but it must not imply blockchain/consensus guarantees it does not possess.

A simulator/reference model is valuable even when non-authoritative. Label it accurately.

## Reject

- in-memory state represented as durable commitment;
- API success represented as settlement finality;
- unsigned evaluator output represented as authenticated judgment;
- retry behavior that can duplicate economic actions;
- hidden operator override paths;
- swallowing external dependency failures and returning approval/default success.
