# Nomos

Nomos is the constitutional monorepo for portable economic coordination primitives.

It defines the semantics, invariants, evidence requirements, conformance tests, environment profiles, experiments, and release receipts that govern every Nomos instrument. Implementations may differ by execution environment; the primitive meaning may not.

## Core rule

> Specify the economic primitive first. Implement the same primitive across environments. Use intelligence only where judgment is intrinsic.

GenLayer is the reference judgment substrate for primitives that require non-deterministic evidence evaluation, natural-language interpretation, or validator-mediated judgment. GenLayer is not a branding requirement and Nomos primitives are not GenLayer-exclusive.

## Initial instrument registry

1. Proof of Payable
2. Claim Verification
3. Policy Envelope
4. Workflow Authorization — Path + Pact
5. Dynamic Authority Allocation (DAA)
6. Claim Encumbrance
7. Capital Commitment
8. Dynamic Authorization Lanes (DAL)
9. Financial Contract
10. Gaia — Exception, Reconciliation & Rectification

The machine-readable registry lives in `nomos.manifest.json`.

## Authority order

When sources disagree, use this order:

1. `CONSTITUTION.md` — non-negotiable system law.
2. Canonical primitive `SPEC.md` — semantic meaning and invariants.
3. Accepted Research Foundry evidence — what is known, prior art, falsifiers.
4. Current official environment/standards sources — implementation truth.
5. Environment profile — how the canonical primitive maps into a VM/runtime.
6. Implementation code.
7. Tests, experiments, and receipts.
8. Interface/demo material.

A lower layer may never silently redefine a higher layer.

## Build lifecycle

`PRODUCT TRUTH → RESEARCH → SPEC → ENVIRONMENT PROFILE → IMPLEMENT → CONFORMANCE → ADVERSARIAL EXPERIMENT → RELEASE RECEIPT → INTERFACE/DEMO`

No implementation is called a Nomos implementation merely because it compiles. It must pass the canonical conformance suite for the guarantees it claims.

## Repository contract

Every mature primitive capsule will have this shape:

```text
primitives/<primitive>/
  SPEC.md
  INVARIANTS.md
  THREAT_MODEL.md
  DECISION_BOUNDARY.md
  vectors/
  implementations/
    genlayer/
    evm/
    offchain/
  conformance/
  receipts/
```

An environment that cannot preserve a required invariant must report `UNSUPPORTED`; it must not reinterpret the invariant.

## Status language

Evidence and tests use explicit states only: `PASS`, `FAIL`, `NOT_IMPLEMENTED`, `BLOCKED`.

Lifecycle state is separate and machine-readable in `nomos.manifest.json`.

## Governance

Read, in order:

- `CONSTITUTION.md`
- `AGENTS.md`
- `GOVERNANCE.md`
- `environments/README.md`
- `conformance/README.md`
- `experiments/README.md`
- `RESEARCH_LEDGER.md`

Run governance checks with:

```bash
python tools/nomos_lint.py
```
