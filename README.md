# Nomos

Nomos is the constitutional monorepo for portable economic coordination primitives.

It defines the semantics, invariants, evidence requirements, conformance tests, environment profiles, experiments, and release receipts that govern every Nomos instrument. Implementations may differ by execution environment; the primitive meaning may not.

## Core rule

> Specify the economic primitive first. Every Nomos primitive must implement on GenLayer. Additional environments may implement the same canonical semantics. Use intelligence only where judgment is intrinsic.

GenLayer is the mandatory reference implementation environment for every Nomos primitive and the reference judgment substrate where a primitive requires non-deterministic evidence evaluation, natural-language interpretation, or validator-mediated judgment.

Nomos primitives are not GenLayer-exclusive: EVM, offchain, Move, Solana, or other environment implementations may coexist when they preserve canonical semantics. But no primitive may become `CONFORMANT` or `RELEASED` without an executable GenLayer implementation.

A deterministic Nomos primitive still implements on GenLayer. It MUST keep deterministic safety properties deterministic and MUST NOT invent an LLM/validator judgment step merely to appear "intelligent".

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

`PRODUCT TRUTH → RESEARCH → SPEC → GENLAYER IMPLEMENTATION → OPTIONAL OTHER ENVIRONMENTS → CONFORMANCE → ADVERSARIAL EXPERIMENT → RELEASE RECEIPT → INTERFACE/DEMO`

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
    genlayer/        # mandatory
      README.md
      ...executable implementation...
    evm/             # optional additional profile
    offchain/        # optional additional profile
  conformance/
  receipts/
```

An environment that cannot preserve a required invariant must report `UNSUPPORTED`; it must not reinterpret the invariant.

## GenLayer completion gate

Every primitive must have a GenLayer implementation before it may be `CONFORMANT` or `RELEASED`.

The GenLayer implementation must:

- implement the canonical state model and observable guarantees;
- pass applicable environment-neutral conformance vectors;
- document how canonical semantics map to GenLayer;
- use Intelligent Contract judgment only for the declared judgment boundary;
- preserve deterministic accounting, authority, replay, capacity, identity and conservation invariants;
- include adjacent usage documentation;
- produce executable test/deployment evidence appropriate to its maturity.

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
