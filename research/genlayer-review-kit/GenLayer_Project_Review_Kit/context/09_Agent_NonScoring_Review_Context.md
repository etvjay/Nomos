# Agent Non-Scoring Review Context

This file is for agents that produce reviewer briefs. It intentionally contains no numeric anchors or final-allocation guidance.

The agent's job is descriptive and analytical:

- detect clear gate blockers,
- summarize what the product is,
- explain how it is implemented,
- explain how GenLayer is used,
- identify evidence access issues,
- surface strengths and weaknesses for a human reviewer.

The agent must not make final steward judgments. The synthesis agent may still give a provisional reviewer-assist opinion, such as "appears strong", "appears borderline", "appears below the expected Project bar", or "cannot assess from available evidence", when that opinion is directly backed by reviewed evidence. Do not phrase that as a final accept/reject decision.

## Valid Project Paths

A Project can be valid through either path.

### Intelligent Contract Path

- The repo/deployment includes at least one real GenLayer Intelligent Contract.
- At least one material contract uses meaningful GenLayer non-deterministic consensus.

### Ecosystem Tooling Path

The project directly helps builders create, deploy, test, inspect, operate, analyze, or integrate GenLayer Intelligent Contracts.

Examples:

- deployment helpers,
- Intelligent Contract generators,
- Studio helpers,
- SDK wrappers,
- testing harnesses,
- contract analyzers,
- builder infrastructure.

These projects do not need their own Intelligent Contract if the tooling value is clearly GenLayer-specific.

## Gate Blockers

Flag a gate blocker only when reviewed evidence clearly supports it.

Gate blockers:

- no GenLayer relevance: neither a real Intelligent Contract path nor a valid ecosystem tooling path,
- deterministic-only project: the whole reviewed project has no meaningful non-deterministic GenLayer consensus and does not qualify as ecosystem tooling,
- GenLayer branding only: frontend/backend simulates consensus or on-chain behavior without calling a real contract,
- false frontend integration: app claims contract integration but only simulates locally or never calls the claimed contract methods,
- nonfunctional repo: no runnable contract/tooling path, broken structure, or obvious syntax/dependency failure,
- boilerplate: renamed or minimally changed canonical example with no substantial new value,
- live-app-only: no repository, contract source, deployed source, or ecosystem tooling source to review.

Use a narrow more-info blocker when evidence is accessible and real but a specific fix or clarification is needed:

- real-but-flawed frontend integration,
- wrong contract method calls,
- SDK/runtime compatibility clarification,
- missing specific contract/tooling path.

Use an access blocker when material evidence cannot be reviewed because of login, anti-bot, private repo, paywall, rate limit, failed extraction, or tool limitations.

## Deterministic Contracts

Evaluate determinism at the repository/project level, not per file.

Do not flag a multi-contract project merely because some contracts are deterministic. Deterministic storage, registry, routing, escrow, configuration, helper, or state-management contracts can be valid when they support a coherent architecture.

Only flag deterministic-only when:

- the only submitted/reviewed contract is deterministic-only, or
- the whole repo has no meaningful non-deterministic GenLayer consensus and does not qualify as ecosystem tooling.

## Frontend / Integration

Frontend visual polish is not part of the agent's review.

Use frontend only to understand:

- whether real integration exists,
- whether contract-use claims are accurate,
- what the human reviewer should test,
- whether the app is only simulating contract behavior.

If a frontend or live app claims to use a GenLayer contract, repository code must show a real `genlayer-js` or equivalent read/write path calling the submitted contract methods that matter. Missing `.env` contract addresses are not a problem by themselves.

- No frontend: valid for contract-only projects.
- Mock/fallback UI: acceptable only if a real integration path exists in code.
- Claimed integration with no real contract path: gate blocker.
- Real but incomplete/flawed integration or wrong methods: narrow more-info blocker.

## Qualitative Review Lenses

Use these lenses for the reviewer brief. Do not turn them into final steward judgments.

## Reviewer-Assist Opinion

The synthesized memo should not be purely descriptive when the evidence clearly points in one direction. It may include a concise opinion for the human reviewer:

- `appears strong`: GenLayer is central, the contract/tooling design supports the use case, and the implementation shows coherent product and engineering judgment.
- `appears borderline`: the project is real, but the fit, contract design, integration, or implementation depth has material weaknesses.
- `appears below the expected Project bar`: the project is real enough to discuss, but reviewed evidence shows weak GenLayer fit, thin contract logic, poor implementation judgment, or mostly decorative use of GenLayer.
- `cannot assess from available evidence`: material evidence was inaccessible or missing.

Keep this opinion evidence-tethered. Name the two or three facts that drive it, and name any uncertainty that could change it. Do not use the opinion to bypass evidence access rules, and do not output final portal actions or points.

### GenLayer Fit

Explain whether the use case actually benefits from GenLayer.

Ask:

- If GenLayer is removed, what trust model breaks?
- Is validator consensus tied to a meaningful user outcome?
- Is the product trying to improve answer quality, or does the outcome need to be trustless because parties may disagree or have conflicting incentives?
- Does the use case justify GenLayer's cost, latency, and validator-consensus complexity, or would a faster off-chain AI/backend workflow serve users better?
- Is the use case specific and thought through, or just "AI decides X"?
- Would a centralized backend, simple oracle, or normal smart contract work essentially the same?
- For games, does GenLayer affect gameplay, adjudication, anti-cheat, outcomes, or another meaningful mechanic?
- For ecosystem tooling, does it solve a real GenLayer builder workflow?

AI consensus for accuracy is not the same as trustless GenLayer consensus. Advisory products such as crop diagnosis, tutoring, health-style guidance, or recommendations can be useful AI products while still having weak GenLayer dependence if the main need is expert accuracy and there is no contested or value-bearing outcome between parties.

GenLayer consensus is not a normal LLM call with extra reviewers. It is slower, more expensive, and operationally heavier than an off-chain AI system. Treat that overhead as justified only when the project needs neutral, verifiable settlement or a GenLayer-specific builder workflow. If users mainly need a fast, personalized, high-quality answer, the fit is usually partial even when the contract technically works.

For advisory or planning products, pressure-test factual freshness and verification. Travel planners, crop-treatment assistants, health-style triage, financial suggestions, tutoring, and recommendation engines often depend on facts that can change quickly: weather, regulations, product availability, local prices, disease outbreaks, geopolitical or safety conditions, transport disruptions, market data, policy changes, and user-specific constraints. If the contract mostly relies on LLM training data or user-submitted text, and does not fetch or verify current facts, GenLayer may only be making a plausible recommendation rather than adjudicating a trust-sensitive result.

GenLayer does not automatically make a generic LLM answer specialized or reliable. Specialization must come from the project's design: source selection, web fetching, domain context, prompt constraints, output validation, and validator checks that test the actual result. If validators only approve that an answer is coherent, helpful, safe, or well formatted, they may be improving presentation rather than enforcing meaningful consensus.

The strongest GenLayer fit is not "several validators produce a better answer." It is "neutral validators settle a result that someone has reason to dispute." Look for conflicting incentives, external evidence, and consequences: a payout, claim, eligibility decision, marketplace action, moderation outcome, escrow release, audit result, attestation, or game/reward outcome. If nobody benefits from biasing the result and the user mainly wants high-quality advice, the fit is usually partial or weak.

GenLayer fit is clearer when the AI result affects an outcome where neutrality matters: insurance claims, subsidy eligibility, marketplace disputes, payouts, moderation, attestations, eligibility, audits, or any situation where one party could benefit from a particular judgment and another party should not have to trust that operator.

Common categories such as dispute resolution, bounty judging, IP checks, inheritance, oracle apps, voting, moderation, or generic AI adjudication are not automatically strong. They need a specific edge or thoughtful application.

### Contract Or Tooling Design

Explain whether the implementation supports the product claim.

For Intelligent Contracts, look at:

- meaningful state and public methods,
- nondeterministic LLM/web paths,
- EP/validator logic,
- whether validators check the meaningful result,
- whether validators verify domain-specific facts or only approve plausibility, helpfulness, safety, or formatting,
- whether outputs affect state, claims, ordering, payments, moderation, or workflow,
- whether prompts and parsing fit the use case,
- whether `run_nondet_unsafe` leader/validator logic makes sense.

For ecosystem tooling, look at:

- whether it is genuinely GenLayer-specific,
- whether it supports a useful builder workflow,
- whether it handles realistic inputs, outputs, and failure modes,
- whether it wraps or improves official tooling in a meaningful way.

Shape-only validation is weak. Shape-only means checking only JSON fields, labels, keywords, length, enum values, or numeric ranges without checking the actual verdict, recommendation, decision, or core result.

### Engineering And Implementation

Explain what the codebase shows about implementation quality.

Look for:

- coherent repo structure,
- appropriate language/framework/tool choices,
- real integration between components,
- clear setup/deploy instructions,
- error handling in important flows,
- evidence of original implementation rather than pasted boilerplate,
- whether generated/scaffolded code is backed by coherent product logic.

Do not treat repo size, file count, framework choice, generated UI, screenshots, or marketing language as meaningful evidence by themselves.

## Important Exceptions

- `gl.vm.run_nondet_unsafe(...)` is official SDK usage. Do not flag it because of the word `unsafe`.
- Older SDK names, older strict/nondet helpers, `py-genlayer:test`, `py-genlayer:latest`, or missing pinned GenVM hash are compatibility concerns, not automatic gate blockers.
- Missing deployment proof lowers certainty and affects evidence notes, but deployment is not mandatory when source evidence is complete and accessible.
- Missing tests are not a gate blocker.
