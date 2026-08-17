# Workflow Authorization — Invariants

- Path represents standing bounded authority; Pact represents specific accepted terms.
- Revoked/expired Path cannot authorize later execution.
- Pact binds exact workflow references and accepted terms.
- Blocked decisions cannot yield executable Pacts.
- Quantitative/capability bounds remain deterministic.
