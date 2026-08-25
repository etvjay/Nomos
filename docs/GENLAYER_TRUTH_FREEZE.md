# GenLayer Truth Freeze for Nomos Documentation

**Purpose:** source-bound foundation for rewriting the Nomos, PPA, and Intelligent Account documents.

**Audited:** 2026-08-23
**Method:** Research Foundry source verification plus Evaluated Build Instantiation truth-freeze discipline.

## What GenLayer is

GenLayer presents itself as **the adjudication layer for the agentic economy**. Its Intelligent Contracts are designed for decisions that require judgment, including natural language, unstructured data, live web inputs, and AI-based reasoning.

This is broader than an oracle network. An oracle normally delivers a value to another contract. GenLayer provides a contract execution environment and validator consensus process in which the contract can define how a judgment is produced, checked, accepted, rejected, rotated, or left undetermined.

## What GenLayer offers

### Intelligent Contracts

GenLayer Intelligent Contracts combine ordinary contract features with nondeterministic capabilities. The official feature documentation separates:

- deterministic features: storage, errors, value transfers, messages, contract interactions, EVM interactions, and other ordinary state-machine operations;
- nondeterministic features: LLM calls, image processing, web access, and other operations whose outputs can vary across validators.

The distinction is a capability distinction inside one contract model, not a claim that GenLayer execution is wholly deterministic or wholly nondeterministic.

### Optimistic Democracy

Optimistic Democracy selects a leader to execute and propose a result. Other validators independently evaluate the transaction. They vote using the contract's declared Equivalence Principle. Majority agreement accepts the result; disagreement can cause leader rotation, an undetermined result, or an appeal/finality path.

### Equivalence Principles

GenLayer documents several validation approaches:

- strict equality for outputs that should match exactly;
- comparative validation, where leader and validator independently perform the task and their decision-bearing outputs are compared;
- non-comparative validation, where validators assess the leader's output against the source and declared criteria without producing a second candidate answer;
- custom validation, where the developer writes the leader and validator functions.

The developer must define what counts as equivalent. A schema check alone is not substantive validation. For extraction, classification, scoring, ranking, authenticity, safety, and settlement decisions, the validator should independently derive or verify the decision where feasible.

### Web and LLM access

Leaders and validators independently fetch external data and run LLM operations. External sources can vary, rate-limit, fail, or return different content to different validators. Contracts must extract stable decision fields, classify errors, and define safe behavior when consensus cannot be reached.

## What Nomos should claim

Nomos should not say:

- GenLayer is merely an oracle replacement;
- GenLayer makes all account execution deterministic;
- the LLM handles accounting;
- consensus makes an observation true;
- an accepted proposal automatically authorizes settlement;
- Intelligent Accounts are simply ERC-7710 accounts with web access.

Nomos may say:

> Nomos uses GenLayer's adjudication model to let an account participate in decisions that require external context or interpretation. The account then applies explicit authority and financial rules to determine whether an accepted judgment can produce a state change.

The financial gates remain deterministic because they must produce one exact state transition. GenLayer is necessary for the preceding judgment, not because the whole system should be deterministic.

## Revised Intelligent Account model

```text
GenLayer adjudication capability
  observe context
  interpret evidence
  compare or judge results
  reach validator consensus
  return accepted / rejected / undetermined outcome

Nomos account capability
  hold authority and capital
  apply policies and agreements
  encode proposals as claims
  settle or deny deterministically
  preserve evidence and rectification history
```

The account is not an oracle consumer with an AI wrapper. It is a financial account whose decision boundary includes a GenLayer adjudication path.

## ERC-7710 comparison boundary

ERC-7710 is a delegation and permission mechanism. It expresses bounded authority such as targets, functions, amounts, expiry, and caveats.

The Intelligent Account proposal is broader and should be described cautiously:

- it can include ERC-7710-like bounded authority semantics;
- it can use GenLayer adjudication for conditions involving language, external evidence, or real-world outcomes;
- it still requires deterministic authority, policy, and settlement checks;
- ERC-7710 can be combined with external oracles and application logic, so the distinction is architectural emphasis and native execution context, not absolute capability exclusivity.

## Evidence status

| Claim | Status | Source/evidence |
|---|---|---|
| GenLayer positions itself as adjudication for the agentic economy | VERIFIED | Official GenLayer docs and genlayer.com |
| Intelligent Contracts support deterministic and nondeterministic features | VERIFIED | Official Intelligent Contract feature documentation |
| Optimistic Democracy uses leader proposal, validator evaluation, majority, rotation, and finality/appeal states | VERIFIED | Official Optimistic Democracy documentation |
| Equivalence includes strict, comparative, non-comparative, and custom patterns | VERIFIED | Official Equivalence Principle documentation |
| Nomos PPA full payment lifecycle is live-verified | VERIFIED | `convergence/deployment/ppa-bradbury.json` |
| Nomos real-model diversity test finalized | VERIFIED | `convergence/receipts/RECEIPT-IAS-DIVERSITY-001-A.json` |
| Intelligent Account is a recognized industry-standard account type | NOT CLAIMED | Nomos terminology remains proposed |

## Documentation constraint

The rewrite must explain one closed path before introducing future concepts:

```text
Why judgment is needed
→ why GenLayer is relevant
→ what the account does with an accepted judgment
→ how authority and money remain bounded
→ one concrete user scenario
→ what is built and what is not
```

Do not introduce merchant accounts, identity, markets, workspaces, or role catalogs in the opening explanation.
