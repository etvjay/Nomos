# Intelligent Accounts

## The short version

Agents need to use money without receiving unrestricted control of a treasury.

An **Intelligent Account** is an account that can use GenLayer validators to observe and interpret external information, then propose an action. The account still applies ordinary financial rules before anything settles.

The core flow is:

```text
external event
    -> web observation and AI interpretation
    -> validator consensus
    -> structured proposal
    -> account rules and authority checks
    -> deterministic settlement
```

**AI observes and proposes. Consensus validates. Account rules execute.**

That is the idea. Everything else in this document supports it.

## Why GenLayer?

Deterministic execution is not the reason to use GenLayer. Ethereum and other blockchains already handle deterministic state changes well.

The difficult question is often outside the chain:

- Did a delivery arrive?
- Does a public page show that a price crossed a threshold?
- Does a document satisfy an agreed clause?
- Has a service provided the result it promised?

A traditional application normally answers these questions through a trusted oracle, an operator, or a single AI system. GenLayer provides another model. A leader validator performs the observation and proposes a result. Other validators independently execute the relevant work, using their own AI models and web access. They compare the results under an Equivalence Principle. If enough validators agree, the result can be accepted by the network.

This does not make an AI answer automatically true. It reduces dependence on one oracle or one model and gives the application a declared way to handle disagreement.

During Nomos testing, a Studio transaction reached finalized consensus across validators using GPT-OSS, Qwen, GPT-5.4, and Claude Sonnet 4.6. The receipt is recorded in:

```text
convergence/receipts/RECEIPT-IAS-DIVERSITY-001-A.json
```

## How this differs from ERC-7710

ERC-7710 is the closest existing comparison. It lets an account delegate restricted authority with conditions such as a target, amount, expiry, or spending limit.

That is useful, and Intelligent Accounts retain the same basic ideas. The difference is what the conditions can refer to.

| | ERC-7710 | Intelligent Account |
|---|---|---|
| Main purpose | Delegate authority | Operate an account with bounded autonomy |
| Conditions | Mainly transaction and on-chain conditions | Those conditions plus consensus-backed external observations |
| Example | Agent may spend 50 per day until Friday | Agent may spend 50 per day after delivery is confirmed |
| Perception | No native web or AI observation | GenLayer validators can observe and interpret external data |
| Execution | Permission checks a delegated action | Proposal enters policy, authority, encumbrance, and settlement gates |

The simplest description is:

> **An Intelligent Account is an account with outcome-aware authority.**

ERC-7710 can be combined with oracles and application logic to approximate some of this behavior. The distinction is that observation, validator consensus, proposal handling, and bounded execution are central to the Intelligent Account design rather than external add-ons.

## The safety boundary

An Intelligent Account has two different kinds of work.

### Intelligent work

The account may use AI and nondeterministic operations to:

- fetch external data;
- interpret text;
- classify an event;
- compare observations;
- calculate a confidence score;
- propose an action.

### Financial work

The account uses deterministic rules to:

- identify the caller;
- check delegation and expiry;
- check recipient allowlists;
- enforce per-transaction and daily limits;
- check available capital;
- reserve or settle a claim;
- record a denial or payment;
- preserve history.

A proposal never bypasses these checks. If the validators disagree, the proposal can remain unresolved. If the validators agree but a policy gate rejects the action, the action is denied. The model does not receive a hidden route around the account's rules.

This is the design principle:

> **Judgment proposes. Deterministic gates dispose.**

## Three levels of autonomy

The same account model can be configured for different risk appetites.

### Level 1: Monitor

The account observes selected sources and records proposals. A person reviews and executes any payment.

Use this when the priority is visibility rather than automation.

### Level 2: Coordinate

The account combines multiple signals. For example, three monitors may need to agree within a time window before the account creates a stronger proposal.

Use this when one observation is too weak but full automation is not acceptable.

### Level 3: Execute

A confirmed proposal may trigger an action automatically. The action still requires the account's policy, authority, capital, and settlement checks. Limits include per-action caps, daily ceilings, recipient allowlists, expiry, and a kill switch that starts off.

Use this only when the operator understands and accepts the configured limits.

Higher levels add evidence and automation. They do not grant the AI broader authority to bypass the account.

## What Nomos has built

Nomos provides the financial mechanisms beneath the account:

- policy and spending limits;
- evidence-bearing payment claims;
- capital encumbrance;
- scoped authority allocation;
- replay-proof authorization lanes;
- workflow agreements;
- dispute and rectification cases.

The Programmable Payment Account is the concrete payment product. The Intelligent Account is the broader account architecture that adds the observation and proposal layer.

Ten of Nomos's eleven primitives are independently CONFORMANT. Fresh-context builders reconstructed them from specifications and canonical vectors without reading the reference implementations. The remaining financial-contract primitive has a converged independent build but remains SPECIFIED while its narrowed scope is re-qualified.

The PPA payment lifecycle has also been verified on GenLayer Testnet Bradbury: account creation, deposit, policy-gated send, settlement, and exact balance reconciliation.

The three account stages are implemented in `ias/` and deployed to Bradbury. The complete uninterrupted Stage 3 loop remains open live work. The deterministic account operations are proven; the judgment step has been validated separately through Studio and simulated consensus. This distinction matters and is not hidden.

## First users and distribution

The first user is the Nomos and OpenRails stack itself. OpenRails already coordinates workspaces, authority, agreements, proof, payments, and receipts. Intelligent Accounts can provide the GenLayer-native observation and bounded financial-account layer for those workflows.

The second audience is GenLayer builders who need a payment account with rules rather than a raw wallet.

The third audience is agent-commerce systems such as Internet Court, where Nomos can provide certified mechanisms for policy, claims, delegation, disputes, and settlement.

The initial product is not a general-purpose autonomous economy. It is a narrow account that makes one useful promise:

> **An agent can act financially within rules, and external intelligence cannot silently rewrite those rules.**

## What this does not claim

- Validator consensus is not the same as truth.
- Model diversity does not eliminate correlated source failures.
- A policy cap chosen badly is still a bad policy cap.
- Certification demonstrates reproducibility, not the absence of every bug.
- The account does not make an agreement legal or a counterparty honest.

## Closing

Smart accounts made authority programmable. Intelligent Accounts add bounded perception to that authority.

GenLayer supplies the consensus mechanism for nondeterministic observation. Nomos supplies the account rules and financial primitives. The account connects them without letting AI directly mutate the ledger.

**GenLayer provides consensual intelligence. The account provides bounded authority. Deterministic gates provide exact financial consequences.**
