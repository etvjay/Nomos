# Nomos

Financial primitives and Intelligent Accounts for GenLayer.

## What Nomos is

Nomos provides reusable mechanisms for financial applications:

- evidence and claims;
- authority and delegation;
- spending policies;
- capital commitment and encumbrance;
- workflow agreements;
- replay protection;
- financial obligations;
- disputes and rectification;
- payment account composition.

## Why GenLayer

GenLayer is designed for contracts that require adjudication, not only fixed code. Its Intelligent Contracts can process language, unstructured evidence, live web inputs, and AI reasoning. Optimistic Democracy and Equivalence Principles let validators evaluate and accept or reject nondeterministic results.

Nomos uses GenLayer in two ways:

1. **Adjudication:** external evidence, language, and judgment can produce a consensus-backed result.
2. **Execution:** accepted results enter explicit authority, policy, capital, and settlement rules.

The account does not treat an accepted judgment as an automatic payment. The account evaluates what consequences are permitted.

## Documentation

- [Nomos Master Whitepaper](NOMOS_WHITEPAPER.md)
- [Intelligent Account Whitepaper](primitives/ppa/INTELLIGENT_ACCOUNT_WHITEPAPER.md)
- [PPA Whitepaper](primitives/ppa/WHITEPAPER.md)
- [IAS-1 Standard](primitives/ppa/IAS-1.md)
- [Fact-Check Ledger](docs/FACT_CHECK_LEDGER.md)
- [GenLayer Truth Freeze](docs/GENLAYER_TRUTH_FREEZE.md)

## Primitive status

10 of 11 primitives are **CONFORMANT** through independent implementation and canonical vector convergence. One remains **SPECIFIED** pending scope re-qualification.

| Primitive | Function | Status | Mode |
|---|---|---|---|
| Proof of Payable | Evidence-bearing claims and settlement | CONFORMANT | EXACT |
| Claim Verification | Judgment over mandate clauses and evidence | CONFORMANT | SEMANTIC |
| Policy Envelope | Allowlists, amount limits, daily limits, and denials | CONFORMANT | SEMANTIC |
| Workflow Authorization | Paths and pacts with validity windows | CONFORMANT | EXACT |
| Mandate Allocation | Eligibility of capital under mandates | CONFORMANT | EXACT |
| Dynamic Authority Allocation | Bounded authority grants and lifecycle | CONFORMANT | EXACT |
| Claim Encumbrance | Capital reservations against obligations | CONFORMANT | EXACT |
| Capital Commitment | Available and committed capital | CONFORMANT | EXACT |
| Dynamic Authorization Lanes | Replay-proof authorization nonces | CONFORMANT | EXACT |
| Gaia | Disputes, reconciliation, and rectification | CONFORMANT | EXACT |
| Financial Contract | Obligation and cash-flow lifecycle | SPECIFIED* | EXACT |

*Financial Contract has an independent 9/9 vector convergence result. Its public state model must be re-qualified before promotion.*

Evidence receipts are in [`convergence/receipts/`](convergence/receipts/).

## Products built on the primitives

### Programmable Payment Account

The PPA is the payment account product. It provides:

- sub-accounts;
- account balances;
- payment rules;
- deposits;
- invoices;
- disputes;
- delegation;
- policy-gated sends.

Every send follows:

```text
policy → encumbrance → claim → settlement
```

The PPA payment lifecycle is live-verified on GenLayer Testnet Bradbury:

```text
create account → deposit 3,000 → send 1,200 → settled balance 1,800
```

See [`primitives/ppa/WHITEPAPER.md`](primitives/ppa/WHITEPAPER.md).

### Intelligent Account

An Intelligent Account adds a GenLayer adjudication interface to an account.

It can use Intelligent Contracts to:

- process agreements and evidence;
- evaluate external context;
- create proposals;
- coordinate multiple observations;
- route accepted proposals into account rules.

The account still applies authority, policy, capital, and settlement checks.

The three configurations are:

1. **Monitor:** observe and propose.
2. **Coordinate:** combine observations and require a threshold.
3. **Autonomous:** execute accepted proposals within configured limits.

See [`primitives/ppa/INTELLIGENT_ACCOUNT_WHITEPAPER.md`](primitives/ppa/INTELLIGENT_ACCOUNT_WHITEPAPER.md) and [`primitives/ppa/IAS-1.md`](primitives/ppa/IAS-1.md).

## ERC-7710 comparison

ERC-7710 delegates bounded authority with conditions such as targets, functions, amounts, and expiry.

An Intelligent Account includes similar authority controls and adds an adjudication path for conditions involving language, evidence, and external context.

```text
ERC-7710:
  agent may spend up to 50 per day until Friday

Intelligent Account:
  agent may spend up to 50 per day after an agreement is adjudicated as satisfied
```

ERC-7710 is a delegation primitive. An Intelligent Account is a broader account architecture.

## Evidence levels

- Primitive vectors: passing.
- Independent convergence: 10 of 11 primitives.
- PPA payment lifecycle: live-verified on Bradbury.
- Real-model adjudication: validated in GenLayer Studio across GPT-OSS, Qwen, GPT-5.4, and Claude Sonnet 4.6.
- Full uninterrupted Stage 3 autonomous loop on Bradbury: **BLOCKED**, pending a clean testnet run.

The PPA invoice, dispute, and delegation paths are simulation-tested. Their separate live calls remain open work.

## Quick start

Inspect a public primitive contract:

```bash
cat primitives/proof-of-payable/CAPABILITY.json
```

Run an independent lane's canonical vector runner:

```bash
python3 convergence-lanes/pop/your_build.py \
  primitives/proof-of-payable/vectors/v0.1.json
```

Run repository checks:

```bash
python tools/nomos_lint.py
python tools/nomos_converge.py check
```

## Repository structure

```text
primitives/       specifications, implementations, vectors, receipts
ias/              Intelligent Account stages
contracts/        relative links to contract implementations
convergence/      deployment, verification, and convergence evidence
convergence-lanes independent rebuilds used for certification
examples/         example compositions
docs/              fact-checks and truth freezes
tools/             linting, vector, convergence, and deployment tools
```

## Current limits

- Financial Contract is not yet CONFORMANT.
- Some primitive live write-call coverage is incomplete.
- Full Stage 3 live autonomous execution is not yet proven.
- External web sources can be stale, unavailable, rate-limited, or manipulated.
- Validator consensus is not the same as truth.
- PPA and IAS-1 are reference implementations and specifications, not adopted external standards.

## Project position

GenLayer provides adjudication for decisions that require context and judgment.

Nomos provides reusable financial mechanisms and account rules for applying those decisions.

The governing boundary is:

> **GenLayer adjudicates. Nomos controls authority and financial consequences.**
