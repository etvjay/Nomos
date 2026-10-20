# Make AI Adjudication Safe Before It Moves Money

## Executive Summary

- **Separate Judgment From Payment**: GenLayer's leader proposes a nondeterministic result, validators vote on its acceptability, and deterministic code can then act on the accepted result [8][7]. -> Keep adjudication, finality, and transfer as separate states; never make a provisional verdict an immediately spendable receipt.
- **Harden The Receipt Boundary**: Your fresh, bound, single-use ACCEPTED receipt is a strong starting point. -> Bind it to the *specific obligation, funding source, payment contract, chain, policy version, evidence snapshot, amount, and consumption nonce*, not merely a payee and URL.
- **Compare Decisions, Not LLM Wording**: GenLayer explicitly supports custom validators that compare decision fields and tolerate a bounded numerical difference; strict equality is generally unsuitable for raw LLM output [4][7]. -> Keep exact matching for categorical, payment-bearing fields; remove raw confidence from exact-match consensus.
- **Agreement Is Not Correctness**: A study found that, on one benchmark, model pairs agreed about **60%** of the time when both were wrong, versus roughly **one-third** under a random-error comparison [2]. -> Add source authentication, independent evidence checks, economic challenges, and human escalation for consequential payments.
- **Delay Irreversible Release**: UMA allows anyone to challenge a proposal before settlement, while Kleros provides juror rulings and appeals [5][17]. -> Add an application-level challenge window between an accepted AI finding and withdrawal, even if the underlying GenLayer transaction has become final.
- **Treat Timeouts As Uncertainty**: GenLayer can rotate a rejected leader and ultimately leave a transaction undetermined without changing contract state [8]. -> Fetch failures, ambiguous delivery, and unavailable appeals should hold funds, not silently satisfy an obligation.
- **Price The Entire Workflow**: Validators independently execute nondeterministic work; GenLayer also has commit/reveal, on-chain phase timeouts, and idleness handling [7][6]. -> Benchmark end-to-end time and fees on the actual deployment before setting TTLs, keeper bounties, or customer-facing settlement promises.
- **Constrain High-Risk Accounts**: Chaos Labs' risk-oracle example sends threshold-triggered updates through internal validation to Aave's Risk Stewards contract rather than treating a model observation as unrestricted authority [9]. -> For lending and payment accounts, use AI to authorize a narrowly capped action, never broad discretionary access to a balance.

## 1. What Existing Systems Actually Establish

| System | Judgment and verification | Economic or procedural backstop | Transferable lesson |
|---|---|---|---|
| **UMA Optimistic Oracle** | A proposer submits an answer; anyone may dispute it within a challenge period. An undisputed proposal can settle [5]. | Disputes go to the DVM; participating token holders stake and vote, with slashing for inactive or incorrect votes [10]. | An apparently accepted assertion needs time and incentives for independent challengers to inspect it. |
| **Kleros Escrow** | Parties submit evidence and a randomly selected jury rules; an appeal can be funded during the appeal period [17]. | Fee deadlines, default outcomes when one side does not pay, and a final ruling after the appeal period [17]. | Explicit evidence submission, fee policy, deadlines, appeals, and default behavior matter as much as the first verdict. |
| **GenLayer** | A leader proposes a nondeterministic result; validators independently evaluate it under a contract-defined Equivalence Principle [4][8]. | A majority can accept; rejection rotates the leader, and persistent lack of agreement can become undetermined. Validator idleness and certain violations may be penalized [8][6]. | Put the acceptable-answer rule in code and make indeterminate results non-spendable. |
| **Ritual Chain** | Documentation describes workload-dependent verification using TEE attestations, ZK proofs, FHE, and committees [11]. | Its described fast/slow verification design uses executor bonds that can be slashed if slower proof contradicts fast attestation [11]. | Cryptographic verification of *inference execution* can complement, but cannot itself establish, whether an external delivery claim is true. |
| **Chaos Labs Risk Oracles** | Examples include parameter updates for GMX and Aave and a risk framework for Pendle principal tokens [9]. | Aave updates are submitted to a designated Risk Stewards contract after thresholds and internal validation [9]. | Keep models inside constrained risk-control and authorization pathways; this is not evidence that open-ended LLM-majority escrow is proven safe. |

The crucial distinction is between a *proven pattern* and a *proven LLM outcome*. Challenge windows, bounded authority, juror appeals, and staking exist in deployed systems; they do not establish that multiple language models can reliably establish the truth of an attacker-controlled web page. UMA's process also makes an important assumption: someone must have both the information and incentive to notice and dispute a bad answer. For low-value items, fees can overwhelm that incentive; for high-value items, a short window may be inadequate.

**Decision:** Keep GenLayer as the judgment engine, but add an explicit application-level review and settlement layer for money movement.

## 2. Priority-One Changes To Adjudicated Receipt

### P0: Make acceptance provisional until the payment-specific challenge period ends

Replace `ACCEPTED -> settle` with `REGISTERED -> EVALUATING -> PROVISIONAL_ACCEPTED -> FINAL_ACCEPTED -> CONSUMED`, plus `REJECTED`, `UNDETERMINED`, `CHALLENGED`, `EXPIRED`, and `CANCELLED`. An accepted GenLayer execution is not necessarily the right business event for immediate, irreversible payment: GenLayer's consensus establishes acceptability under the programmed equivalence test, whereas UMA and Kleros add explicit opportunities to contest a judgment [4][5][17].

At provisional acceptance, record a challenge deadline. Permit the payer, payee, and a permissionless watcher to challenge with a bond and counterevidence; freeze withdrawal and route a material dispute to a larger review committee or an agreed human/arbitration forum. Only the *final*, unchallenged or appeal-resolved result may authorize settlement. Set the window by transaction risk rather than borrowing an undocumented GenLayer default. Rejection and indeterminacy must not implicitly refund the payer either: define separate refund, cancellation, and expiry rules so neither side can exploit a failed oracle call.

### P0: Bind evidence, clause, and receipt to one immutable obligation version

A URL identifies a *location*, not a stable piece of evidence. At registration, freeze a canonical obligation identifier and a hash of its payment terms, natural-language clause, policy version, permitted evidence-source policy, and any milestone schedule. At adjudication, record the observed URL, retrieval time or block context, canonicalized content hash, content type, source identity or signature where available, and a bounded evidence excerpt or archive reference. If a source cannot be retrieved, its identity is uncertain, or snapshots conflict, report `UNDETERMINED`; do not let the model substitute a convenient mirror.

A content hash proves that later readers can identify **the bytes actually judged**; it does not prove those bytes were true, published by the claimed party, or current. Conversely, a TTL only limits *when a receipt can be spent*; it does not make old evidence fresh. Define separate limits for evidence age, observation-to-adjudication delay, challenge duration, and final-receipt validity. Prefer signed delivery events, authenticated carrier APIs, or multiple independent sources over a seller-editable page for larger amounts. Treat page text as untrusted data, not instructions to the judge; OWASP identifies attacker-supplied instructions in lower-trust content as a prompt-injection vulnerability [3].

### P0: Enforce replay resistance at the paying contract

The payment authorization should commit to at least `chainId | adjudicatorContract | settlementContract | obligationId | obligationVersion | trancheId | asset | recipient | maximumAmount | evidenceHash | verdict | finalizedAt | expiresAt | nonce`. The escrow or treasury must independently verify that these fields match *its own funded object*, that the receipt is final and unexpired, and that the nonce or tranche has not been consumed. Use one atomic state transition to mark consumption and reduce available funds **before** the external transfer; employ the target chain's established reentrancy protections. If a bridge carries results between chains, bind the destination chain and receiver as well as the source, and verify the authenticated message path: a copied receipt is not a cross-chain authorization.

Crucially, do not confuse `owner may settle` with adequate replay protection. An authorized owner can make an implementation mistake, settle the wrong escrow, or pay twice through two integrations. Put the final checks in *each contract that releases value*, and make a receipt for one object unusable by every other object.

**Decision:** P0 changes are prerequisites to moving meaningful funds; they prevent a valid-looking but stale, cross-object, challenged, or replayed finding from becoming a payment.

## 3. Priority-Two Changes To LLM Equivalence And Evidence Review

### P1: Replace exact confidence equality with a decision-focused validator

Your exact comparison of `satisfied`, `verdict`, and `confidence` combines two good instincts - a bounded schema and independently rerun validators - with one fragile field. GenLayer recommends comparing material decision fields rather than incidental prose; its examples permit exact labels and bounded numerical tolerances, and its documentation warns that exact matches are generally unsuitable for open-ended LLM responses [4][7].

Use a schema such as `{status: DELIVERED|PARTIAL|NOT_DELIVERED|UNKNOWN, eligible_units: bounded_integer, evidence_refs: [...], reason_code: enum, uncertainty_flags: [...]}`. Validate its types and ranges deterministically, but do not mistake valid JSON for substantive verification: GenLayer expressly warns against validators that merely check the leader's schema or a permitted enum [8]. Require exact agreement on payee-relevant eligibility and any payable quantity, or a conservative rule such as *pay no more than the minimum independently supported quantity*; compare ancillary measured values only within precommitted domain-specific tolerances. Keep free-text rationale and raw model confidence out of payment-bearing equality. An LLM saying `high` is not a calibrated probability.

In the validator path, independently fetch authorized evidence and independently derive the decision. Where appropriate, first run a deterministic validator for source signature, order ID, date, units, and hash, then ask an LLM only the residual semantic question. GenLayer's custom `run_nondet_unsafe` leader/validator pair is the documented choice for bespoke validation; the docs describe `gl.vm.run_nondet` as primarily internal to convenience functions, and also provide comparative and non-comparative prompt wrappers [8]. Non-comparative verification can save work but still requires the validator to examine the source and evaluate the leader's claim, not merely trust it [8][4].

Test two distinct errors: **divergence**, where correct validators disagree because a page changes or a numeric boundary is unstable; and **false convergence**, where every judge follows the same misleading source or prompt injection. Model diversity helps the former only conditionally and does not solve the latter: research documents substantial correlated errors among LLMs, including more accurate models [2]. Maintain adversarial fixtures for changed pages, conflicting snapshots, spoofed delivery documents, partial shipments, ambiguous clauses, output-schema manipulation, and near-threshold scores.

### P1: Put escalation and keepers on an economic footing

A permissionless `tick` needs an enforceable reward for *useful* evaluation, funded in advance and capped per obligation. Add an initial evaluation bounty, bounded retry policy and cooldown, a challenge bounty when a challenge succeeds, and an idempotent finalization bounty. Charge or slash frivolous challenges under preannounced rules, but avoid a bond so large that a customer cannot dispute a small payment. Allow anyone to call timeouts and finalization; do not assume an unpaid volunteer will monitor a deadline. GenLayer documents permissionless idleness calls that can replace an inactive participant or advance a timeout, while repeated idleness or failures to reveal can lead to penalties [6]. Those network incentives do **not** themselves finance your application's evidence monitoring and appeals.

**Decision:** Accept a small amount of additional nondeterministic work and slower settlement to avoid making exact-string coincidences or unchecked agreement the sole payment control.

## 4. Four Concrete Payment Designs

| Use case | What the AI may decide | Deterministic release rule and authority | Failure and appeal path |
|---|---|---|---|
| **Escrow or milestones** | Whether specified milestone evidence meets a versioned clause; eligible tranche or verified units. | Lock each tranche; cap cumulative paid amount by funded balance and approved milestone schedule. Allow a payer or an explicitly scoped delegate to create a milestone, but do not let that role raise the cap or change a payee without separate authorization. | Freeze the disputed tranche, not unrelated completed milestones. Kleros Escrow illustrates direct partial payment or reimbursement, settlement negotiation, and court escalation when parties cannot agree [18]. |
| **Delivery versus payment** | Whether authenticated evidence matches order ID, recipient, delivered quantity, and deadline. | Release only the corresponding units; for a partial delivery, compute `payable = min(verified_units * contracted_unit_price, unpaid_tranche_cap)` using deterministic arithmetic. | Missing scan, returned goods, conflicting carrier data, or ambiguous acceptance -> hold disputed units and allow a challenge, not an all-or-nothing release. |
| **Lending-pool drawdown** | Whether covenants or project-progress evidence meet specified draw conditions. | Approve only a draw from a prefunded, risk-limited facility with per-borrower ceilings, utilization and collateral checks, expiry, and a pause switch. Keep rate, collateral, and liquidation controls separate from semantic judgment. | Ambiguous financial evidence -> manual credit or risk review. Chaos Labs' Aave example illustrates routing automated risk updates through thresholds, internal validation, and a designated steward contract [9]. |
| **Neobank-style payment account** | Whether a specific invoice or documented service satisfies a payment policy. | An account owner authorizes a **per-object delegate** with payee allowlist, asset, maximum amount, expiry, and revocable scope. The judgment can release only a reserved, on-chain balance or issue a constrained instruction to an authorized custodian. | Hold disputed transfers and offer reversal or customer support where the underlying payment rail permits it. A smart contract cannot itself compel a bank to transfer fiat or reverse a completed off-chain payment. |

**Kleros case study.** In Kleros Escrow, parties lock funds before delivery; when they agree, a buyer can pay, a seller can refund, or parties can negotiate partial settlement. When agreement fails, they can submit evidence and pay arbitration fees for a juror ruling [18]. The lesson for Adjudicated Receipt is not to replace those paths with an LLM label. Instead, make the label one input to a settlement workflow that preserves partial payment, negotiation, evidence submission, and an appeal when the stakes justify it.

**Chaos Labs case study.** Its examples separate risk signals from authority: GMX uses risk oracles to adjust price-impact and open-interest parameters, while Aave submits threshold-triggered updates to a Risk Stewards contract after internal validation [9]. This suggests a safer drawdown architecture: AI can identify evidence satisfying a covenant, but a separate pool contract enforces collateral, per-borrower limits, and total exposure. A wrong judgment then faces a capped loss rather than unrestricted treasury access.

**Decision:** Choose a different release cap, delegate scope, and challenge duration for each object. Do not use one generic `ACCEPTED` flag as authority over an entire account or credit facility.

## 5. GenLayer Capabilities, Limits, And Deployment Tests

GenLayer's Equivalence Principle is written as contract logic: a leader produces a value, validators judge acceptability, majority approval selects that leader value, rejection can rotate the leader, and unresolved transactions need not change state [4][8]. The leader also participates in committee voting; committee selection is stake-weighted but damped rather than strictly proportional to raw stake, and voting uses commitment and reveal [6]. Keep *all* web and LLM operations inside the nondeterministic block, and perform storage writes, contract calls, and transfers in the deterministic context afterward [7].

The official descriptions characterize Optimistic Democracy as starting with a small committee and finalizing an uncontested result after an appeal window [13]. GenLayer also describes monitoring deadlines and appeals as validator duties [6]. **Do not hard-code a purported live validator count, fixed appeal duration, fixed quorum beyond the documented majority rule, or a standard price or latency per prompt from this evidence**: those deployment-specific values were not established in the material reviewed. Read the current network's governance parameters and transaction state before deciding when an application-level receipt becomes spendable. In particular, distinguish *network finality* from your longer, optional *commercial challenge period*.

As of the material reviewed, GenLayer describes Bradbury as a **testnet** milestone toward mainnet, not evidence of production-grade custody guarantees [16][15]. Its testing suite documents mocked web responses, a useful starting point for reproducible adversarial cases [14]. Before live value release, measure on your actual network: web-render success and variance, prompt tokens and fees for both leader and validators, rejected-leader retry rates, commit/reveal and appeal durations, undetermined frequency, and p50/p95 time to *spendable finality*. A benchmark for just `exec_prompt` omits the costs most likely to determine whether your TTL and keeper bounty work.

**Decision:** Use custom equivalence, explicit transaction-state gating, appeal-aware finalization, and adversarial mocked-web tests now; publish fees, live validator count, and latency only after measuring the deployment that will actually custody funds.

## Synthesis

These systems solve different pieces of the same problem. **GenLayer** offers programmable, distributed judgment but can produce an accepted *wrong* answer when validators share a mistaken source. **UMA** makes incorrect assertions challengeable, but depends on informed challengers showing up. **Kleros** offers evidence-based human adjudication and appeals at the cost of fees and delay. **Ritual** offers ways to verify aspects of computation, not the real-world truth of every input. **Chaos Labs** illustrates restricting an automated signal to bounded, validated parameter changes [8][5][11][9].

The best architecture combines rather than substitutes those controls: **authenticated and frozen evidence -> independent, decision-focused GenLayer validation -> provisional receipt -> economically viable challenge and escalation -> final, domain-bound, one-use authorization -> capped deterministic transfer**. For trivial amounts, shorten or omit the *application* challenge window under an explicit risk limit; for high-value or hard-to-reverse payments, require stronger evidence and a longer review. The central rule is simple: an LLM quorum may answer a carefully bounded question, but only deterministic, independently checked policy decides how much money that answer can move.

## References

1. *Page Not Found*. https://docs.uma.xyz/protocol-overview/dvm-2.0
2. *Correlated Errors in Large Language Models*. https://arxiv.org/html/2506.07962v1
3. *LLM Prompt Injection Prevention - OWASP Cheat Sheet Series*. https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html
4. *Equivalence Principle*. https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy/equivalence-principle
5. *How does UMA work?*. https://docs.uma.xyz/protocol-overview/how-does-umas-oracle-work
6. *Validators and roles*. https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/validators-and-validator-roles
7. *Non-determinism*. https://docs.genlayer.com/developers/intelligent-contracts/features/non-determinism
8. *The Equivalence Principle*. https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle
9. *Risk Oracles: Real-Time Risk Management for DeFi - Chaos Labs*. https://chaoslabs.xyz/posts/risk-oracles-real-time-risk-management-for-defi
10. *DVM 2.0*. https://docs.uma.xyz/using-uma/voting-walkthrough/dvm-2.0
11. *Ritual Chain Developer Documentation*. https://docs.ritualfoundation.org/
12. *Optimistic Democracy: How Consensus Works*. https://docs.genlayer.com/understand-genlayer-protocol
13. *Optimistic Democracy*. https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy
14. *GenLayer Testing Suite | GenLayer Documentation*. https://docs.genlayer.com/api-references/genlayer-test
15. *GenLayer Roadmap to Mainnet | GenLayer*. https://genlayer.com/blog/genlayer-roadmap-to-mainnet
16. *Announcing Testnet Bradbury | GenLayer*. https://genlayer.com/blog/announcing-testnet-bradbury
17. *kleros-docs/products/escrow/kleros-escrow-specifications.md at master · kleros/kleros-docs · GitHub*. https://github.com/kleros/kleros-docs/blob/master/products/escrow/kleros-escrow-specifications.md
18. *Escrow*. https://docs.kleros.io/products/escrow
