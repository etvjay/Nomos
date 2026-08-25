# Intelligent Accounts

## An account for decisions that code alone cannot resolve

### The short version

Agentic commerce needs more than payments and wallets. Agents also need to handle agreements, evidence, exceptions, and disputes.

A normal smart contract is good at fixed rules. It is not good at deciding whether a natural-language obligation was satisfied, whether evidence is relevant, or what a disputed real-world event means.

GenLayer is designed for that missing layer. It is an adjudication network where Intelligent Contracts can process language, unstructured evidence, live web inputs, and AI reasoning. Validators independently evaluate the proposed result using an Equivalence Principle and Optimistic Democracy.

Nomos uses that capability to build **Intelligent Accounts**.

An Intelligent Account can participate in adjudication when an account decision requires context. It can receive a consensus-backed judgment and turn that judgment into a proposal. Its authority, policy, and settlement rules then determine what happens next.

```text
agreement or external event
          ↓
Intelligent Contract adjudication
(language, evidence, web data, AI reasoning)
          ↓
validator consensus
(Optimistic Democracy + Equivalence Principle)
          ↓
accepted, rejected, or undetermined result
          ↓
Nomos account rules
(authority, policy, encumbrance, settlement)
```

The account is not an oracle wrapper. It is an account with an adjudication boundary.

## Why GenLayer?

Bitcoin made money trustless. Ethereum made computation trustless. GenLayer presents a third problem: **adjudication**.

Many commercial situations cannot be reduced to a fixed Boolean condition before the situation occurs:

- Did a delivery satisfy the agreement?
- Does a submitted result meet a natural-language requirement?
- Is a dispute a delivery failure, an amount mismatch, or an unauthorized action?
- Does evidence from several sources support a claim?
- What should happen when two agents disagree about performance?

Traditional systems send these questions to a company, an oracle, an arbitrator, or a human reviewer. A normal smart contract usually avoids them by requiring every condition to be encoded in advance.

GenLayer provides a third option. The Intelligent Contract contains the decision process. Its validators independently evaluate the result. The Equivalence Principle defines what counts as agreement. Optimistic Democracy determines whether the network accepts the result.

GenLayer still supports ordinary deterministic contract capabilities such as storage, value transfers, messages, and state changes. It is not correct to describe GenLayer as wholly nondeterministic. It combines ordinary contract execution with a protocol for adjudication when fixed code is not enough.

## What is an Intelligent Account?

An Intelligent Account is a proposed account architecture with two connected parts:

1. **An adjudication interface** for decisions involving language, evidence, external context, or interpretation.
2. **A financial account core** for authority, policy, capital, settlement, and history.

The adjudication interface does not replace the financial core. It supplies a decision or proposal to it.

The financial core does not pretend that every commercial question is already deterministic. It defines what the account is allowed to do after a judgment has been accepted, and what it must refuse regardless of that judgment.

## The important distinction from ERC-7710

ERC-7710 is a delegated-permission mechanism. It can express authority such as:

> This agent may call this target, for these functions, up to this amount, until this time.

That is useful and closely related to the authority layer of an Intelligent Account.

The difference is the type of question the account can place around that authority.

| | ERC-7710 | Intelligent Account |
|---|---|---|
| Main problem | Delegating bounded authority | Operating bounded authority in an adjudicating environment |
| Conditions | Primarily permission and transaction conditions | Permission conditions plus contextual decisions |
| Example | Agent may spend 50 per day until Friday | Agent may spend 50 per day if the agreement was satisfied |
| Decision source | Wallet and permission rules | Intelligent Contract adjudication plus account rules |
| Dispute handling | Not its primary purpose | A first-class composition with evidence and rectification |

This is not a claim that ERC-7710 cannot be combined with oracles or application logic. It can. The distinction is architectural: ERC-7710 is primarily a delegation primitive, while an Intelligent Account makes adjudication part of the account workflow.

## What the account does

Consider a service agreement between two agents.

The agreement says that payment should be released after a service produces a specified result. The result is not a single on-chain number. It is a document, a web response, a repository change, or another piece of evidence.

The Intelligent Account workflow is:

1. The parties define the agreement and its evidence requirements.
2. A service submits evidence.
3. An Intelligent Contract evaluates the evidence and the agreement.
4. Validators independently review the result using the declared Equivalence Principle.
5. The accepted result becomes a structured proposal or adjudication outcome.
6. The account checks authority, policy, capital, and claim conditions.
7. The account settles, denies, opens a dispute, or remains undetermined.

The important point is step 5. **An accepted judgment is not automatically a payment.** It becomes an input to the account's financial rules.

## The account boundary

The account may use GenLayer's adjudication capabilities for:

- interpreting natural-language agreements;
- evaluating unstructured evidence;
- resolving factual questions from public sources;
- classifying disputes;
- proposing an action based on an accepted outcome.

The account's financial core handles:

- ownership and delegated authority;
- allowlists and spending limits;
- expiry and revocation;
- capital availability and encumbrance;
- payment claims and settlement;
- denials and receipts;
- compensating entries and history.

This is the boundary:

> **GenLayer adjudicates the contextual question. Nomos decides what authority and financial consequences are permitted.**

## Three levels of use

The levels are not different account species. They are different risk configurations.

### Level 1: Assisted account

The account can receive or produce adjudication results and prepare a proposed action. A person approves the final financial action.

This is the safest starting point for a new application.

### Level 2: Coordinated account

The account combines several pieces of evidence or several monitors before making a proposal. It can require a threshold, a quorum, a time window, or agreement across multiple sources.

This is useful when one observation is not sufficient.

### Level 3: Autonomous account

An accepted result can trigger execution automatically, but only within declared policy. The policy may include a recipient allowlist, amount caps, daily limits, expiry, and a kill switch.

The third level does not give the model unrestricted authority. It gives the account a more automated route to the same financial gates.

## What Nomos contributes

Nomos supplies the account-side mechanisms:

- evidence-bearing claims;
- policy envelopes;
- capital encumbrance;
- capital commitment;
- workflow authorization;
- dynamic authority allocation;
- replay-proof authorization lanes;
- financial obligation lifecycles;
- Gaia dispute and rectification.

The Programmable Payment Account is the concrete payment account built from these mechanisms. The Intelligent Account is the broader architecture that adds a GenLayer adjudication interface to the account.

## What exists today

Nomos has ten independently CONFORMANT primitives out of eleven. Fresh-context builders reconstructed them from specifications and canonical vectors without reading the reference implementations. The remaining financial-contract primitive has an independent converged build but remains SPECIFIED while its narrowed scope is re-qualified.

The PPA payment lifecycle has been verified on GenLayer Testnet Bradbury: account creation, deposit, policy-gated send, settlement, and exact balance reconciliation.

The Intelligent Account stages are implemented as:

- **Stage 1:** adjudication or monitoring produces a proposal for review;
- **Stage 2:** multiple observations are coordinated before escalation;
- **Stage 3:** an accepted result may enter an autonomous execution path with hard policy limits.

The real-model consensus path has been validated in Studio across GPT-OSS, Qwen, GPT-5.4, and Claude Sonnet 4.6. A continuous Stage 3 live run remains open. That is an integration and testnet reliability gap, not evidence that the adjudication model itself has been proven in every production configuration.

## First users

The first user is the OpenRails stack. OpenRails already models workspaces, parties, paths, agreements, proof, payment, receipts, and Gaia cases. Nomos can provide the certified account and adjudication mechanisms beneath those workflows.

The next audience is GenLayer builders who need an account that can handle agreements and evidence without handing a private key to an agent.

A later integration target is Internet Court and similar agent-commerce systems that need settlement, authority, evidence, and dispute mechanisms.

The first product should remain narrow:

> **An account that can participate in adjudication, while keeping its authority and financial consequences explicit.**

## Boundaries

- Adjudication is not truth. Consensus can still be wrong or affected by correlated sources.
- Web access is not guaranteed. Sources can be unavailable, stale, manipulated, or rate-limited.
- Validator agreement is not legal enforcement.
- A permission standard is not an account product.
- Financial limits are only as good as the configuration that sets them.
- Independent convergence demonstrates reproducibility, not the absence of every bug.

## Conclusion

GenLayer is not merely a place to put an AI oracle. It is a protocol for contracts that require judgment.

Nomos uses that protocol to explore a new account architecture. The account can participate in contextual decisions, but it still exposes a clear financial boundary: authority is scoped, policy is visible, settlement is controlled, and disputes have a defined path.

**GenLayer adjudicates. Intelligent Accounts coordinate authority and consequence. Nomos supplies the financial mechanisms that make the boundary explicit.**
