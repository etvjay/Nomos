# Nomos

Nomos is a **financial primitive stack for building applications on GenLayer**.

It defines reusable economic objects, state machines, authority models, invariants, conformance tests, implementation contracts, and developer-facing modules that application builders can compose into lending, receivables, treasury, trade-finance, insurance, capital-allocation, agentic-finance, and other financial systems.

## Product goal

> Build primitives developers can use to build financial applications on GenLayer without repeatedly re-inventing evidence, authority, allocation, commitment, replay, financial-obligation, and rectification machinery.

Nomos' product target is GenLayer.

Canonical primitive specifications remain semantically explicit and mechanism-independent so that GenLayer implementation details cannot silently redefine the economic object. Cross-environment implementations may be used for research, reference models, interoperability, or conformance comparison, but they are not the primary product goal.

## GenLayer implementation model

Every Nomos primitive MUST ship an executable GenLayer implementation.

Nomos uses GenLayer through two distinct protocol capabilities:

```text
Nomos financial primitive
        ↓
Intelligent Contract
(programmable implementation surface)
        ↓
GenVM execution
        ↓
Optimistic Democracy
(network consensus / validation)
        ↓
finalized GenLayer state
```

For non-deterministic operations, each primitive MUST define the evidence, bounded decision schema, and Equivalence Principle required for validators to determine whether outcomes are acceptable.

For deterministic primitives, the Intelligent Contract implements the state machine and invariants without inventing unnecessary LLM judgment. Optimistic Democracy remains the network consensus mechanism validating execution; it is not itself a Nomos primitive.

## Primitive registry status

All 11 primitives are deployed on GenLayer Testnet Bradbury. **10 of 11 are CONFORMANT** — independently reimplemented by fresh-context builders who read only the specification and canonical vectors, with every canonical vector passing against every independent build (EXACT convergence; convergence receipts in `convergence/receipts/`).

| Primitive | Status | Convergence |
|---|---|---|
| Claim Verification | CONFORMANT | SEMANTIC |
| Claim Encumbrance | CONFORMANT | EXACT |
| Capital Commitment | CONFORMANT | EXACT |
| Proof of Payable | CONFORMANT | EXACT |
| Policy Envelope | CONFORMANT | SEMANTIC |
| Workflow Authorization | CONFORMANT | EXACT |
| Mandate Allocation | CONFORMANT | EXACT |
| Dynamic Authority Allocation (DAA) | CONFORMANT | EXACT |
| Dynamic Authorization Lanes (DAL) | CONFORMANT | EXACT |
| Gaia | CONFORMANT | EXACT |
| Financial Contract | SPECIFIED | converged 9/9 via independent lane; SCOPE_PROVISIONAL — advances after public state model re-qualification |

The Programmable Payment Account (PPA) composite has full live functional verification on Testnet Bradbury: account creation, funding, policy-gated send, settlement, and exact balance reconciliation (`primitives/ppa/`, whitepaper at `primitives/ppa/WHITEPAPER.md`).

## Composites: the Intelligent Account stack

Nomos composes into user-facing accounts through three layers:

1. **PPA — Programmable Payment Account** (`primitives/ppa/`). One contract that feels like a bank account with rules: send through four deterministic gates (policy → encumbrance → claim → settle), invoices that settle through payer-side gates, disputes with compensating-entry refunds, delegation that narrows and never widens.
2. **IAS-1 — The Intelligent Account Standard** (`primitives/ppa/IAS-1.md`). The account-type specification extracted from the PPA: five modules (authority, policy, settlement, judgment interface, rectification) with one structural invariant — *judgment proposes; determinism disposes*.
3. **Three-stage ladder** (`ias/`) — escalating autonomy over the same interface:
   - Stage 1 Monitor: observes web data under comparative validator consensus, creates proposals
   - Stage 2 Coordinator: correlates n-of-M signals within time windows, scores confidence
   - Stage 3 Autonomous: routes confirmed signals into the embedded PPA gate pipeline under per-group caps, recipient allowlists, daily ceilings, and a default-off kill switch

All stages are deployed on Testnet Bradbury. Real-model comparative consensus (GPT-OSS, Qwen, GPT-5.4, Claude Sonnet 4.6 as independent validators) is validated — see `convergence/receipts/RECEIPT-IAS-DIVERSITY-001-A.json`.

## Quick start

Consume a primitive through its `CAPABILITY.json`:

```bash
# inspect a primitive's public contract
cat primitives/proof-of-payable/CAPABILITY.json

# run its canonical conformance vectors (embedded runner, plain CPython)
python3 convergence-lanes/pop/your_build.py \
  primitives/proof-of-payable/vectors/v0.1.json
```

Deploy the PPA for a ready-made programmable payment account, or compose individual primitives per the canonical progression below.

## Initial primitive registry

1. Proof of Payable
2. Claim Verification
3. Policy Envelope
4. Workflow Authorization — Path + Pact
5. Mandate Allocation
6. Dynamic Authority Allocation (DAA)
7. Claim Encumbrance
8. Capital Commitment
9. Dynamic Authorization Lanes (DAL)
10. Financial Contract
11. Gaia — Exception, Reconciliation & Rectification

### Allocation taxonomy

```text
Mandate Allocation
= evaluates/ranks opportunities under a mandate
= recommendation/evaluation only
= creates no authority

DAA — Dynamic Authority Allocation
= creates a bounded authority grant
= determines who receives what authority, over what resource, for what purpose, under what bounds and validity

DAL — Dynamic Authorization Lanes
= gives independently granted authorizations appropriate replay/execution domains
```

Canonical progression:

```text
Economic evidence
      ↓
Claim Verification
      ↓
Policy / Workflow Authorization
      ↓
Mandate Allocation?      # optional evaluation/recommendation
      ↓
DAA                      # bounded authority exists here
      ↓
Claim Encumbrance
      ↓
Capital Commitment
      ↓
DAL                      # replay/execution topology
      ↓
Financial Contract / execution
```

Gaia is a cross-cutting exception, reconciliation and rectification plane.

The machine-readable registry lives in `nomos.manifest.json`.

## What application developers should eventually consume

Nomos is not complete when contracts merely exist. A released primitive should expose a usable GenLayer developer surface:

```text
primitive specification
      ↓
Intelligent Contract implementation
      ↓
canonical types / schemas
      ↓
SDK / client helpers
      ↓
example composition
      ↓
conformance vectors
      ↓
receipts / deployment references
```

A developer should be able to import or deploy a primitive, understand its guarantees, compose it with another Nomos primitive, and connect it to an application without reconstructing the protocol semantics from source code.

## Authority order

When sources disagree, use this order:

1. `CONSTITUTION.md` — non-negotiable system law.
2. Canonical primitive `SPEC.md` — semantic meaning and invariants.
3. Accepted Research Foundry evidence — prior art, falsifiers, surviving research claims.
4. Current official GenLayer documentation and implementation truth.
5. GenLayer implementation profile.
6. Intelligent Contract implementation code.
7. Tests, experiments, receipts, and deployment evidence.
8. SDK/API/interface/demo material.

A lower layer may never silently redefine a higher layer.

## Build lifecycle

`RESEARCH → SPEC → GENLAYER CONTRACT → DIRECT TESTS → EQUIVALENCE/CONSENSUS TESTS → INTEGRATION → CONFORMANCE → ADVERSARIAL EXPERIMENT → RELEASE RECEIPT → SDK/EXAMPLES`

## Primitive capsule

```text
primitives/<primitive>/
  SPEC.md
  INVARIANTS.md
  THREAT_MODEL.md
  DECISION_BOUNDARY.md
  vectors/
  implementations/
    genlayer/        # mandatory product implementation
      README.md
      ...Intelligent Contract implementation...
  sdk/
  examples/
  conformance/
  receipts/
```

Additional environment implementations may exist under `implementations/` for interoperability or research, but GenLayer is the required product implementation.

## Status language

Evidence and tests use explicit states only: `PASS`, `FAIL`, `NOT_IMPLEMENTED`, `BLOCKED`.

Lifecycle state is machine-readable in `nomos.manifest.json`.

## Governance

Read, in order:

- `CONSTITUTION.md`
- `AGENTS.md`
- `GOVERNANCE.md`
- `environments/genlayer/PROFILE.md`
- `conformance/README.md`
- `experiments/README.md`

Run governance checks with:

```bash
python tools/nomos_lint.py
```
