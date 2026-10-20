# Three-Agent Review Flow

This is the preferred non-scoring workflow for external reviewers who provide repository URLs, live app URLs, deployed contract URLs, or short submission notes.

The goal is to make the final memo useful and concrete without letting any agent make the final steward judgment. The synthesis agent may give a bounded reviewer-assist opinion when evidence supports it.

## Roles

### 1. Positive Evidence Agent

Purpose: explain the strongest evidence in favor of the project.

This agent looks for what works:

- what the product is trying to do,
- why the use case may make sense for GenLayer,
- what implementation evidence supports the claim,
- what contract/tooling behavior is real,
- what integration evidence is present,
- what is genuinely notable.

It should not read the adversarial output.

### 2. Adversarial Evidence Agent

Purpose: pressure-test the project independently.

This agent looks for what weakens the project:

- whether the GenLayer use case is too generic or decorative,
- whether the contract/tooling actually supports the product claim,
- whether the trust boundary is weak,
- whether the frontend or app only simulates integration,
- whether the repo looks scaffolded, copied, thin, or nonfunctional,
- what the human reviewer should be skeptical about.

It should not read the positive output.

### 3. Synthesis Agent

Purpose: blend both independent passes into one concise reviewer memo.

The synthesis agent reads:

- positive evidence output,
- adversarial evidence output,
- evidence access notes,
- source URLs and reviewer-provided context.

It produces only the final reviewer-facing memo. It must not expose the internal debate, raw checklist, or role labels unless helpful.

It may include a provisional reviewer orientation: appears strong, appears borderline, appears below the expected Project bar, or cannot assess from available evidence. This orientation must be evidence-backed and must not be phrased as a final portal decision.

## Review Lenses

All three agents should understand these lenses, but none should produce numeric outputs or final portal decisions. Only the synthesis agent should state the overall reviewer orientation; the positive and adversarial agents stay isolated and evidence-focused. If a scoring proposal is needed, run `prompts/Orchestrator_Four_Agent_Workflow.md` and give scoring context only to the final Scoring Agent.

### GenLayer Fit

Does the product need GenLayer, or is GenLayer mostly decorative?

Look for:

- a trust-sensitive user outcome,
- validator consensus over meaningful non-deterministic input,
- a reason the result needs neutral settlement rather than only better AI accuracy,
- a reason the use case justifies GenLayer's cost, latency, and validator-consensus complexity,
- a reason a single backend/operator should not decide,
- a conflict of interest, contested claim, payout, eligibility decision, dispute, audit, moderation action, or other value-bearing consequence,
- a use case that is more specific than "AI decides X",
- GenLayer affecting game mechanics, adjudication, anti-cheat, payouts, ordering, moderation, eligibility, verification, or another core workflow.

Do not overstate fit when the project mainly gives advice or recommendations to a user. A crop-disease assistant, tutor, or generic advisor may benefit from several AI opinions, but that is usually an accuracy problem unless the result decides something contested or value-bearing.

Do not treat GenLayer consensus as a regular LLM output with extra review. It has cost, latency, and operational overhead. If users mainly need fast, fresh, personalized advice, the project must explain why that answer belongs in a trustless validator-consensus flow instead of an off-chain AI/backend system.

For advisory products, explicitly check whether the contract verifies current facts or mostly relies on LLM priors and user-submitted text. Travel, agriculture, health-style, finance, tutoring, and recommendation apps can be useful while still weak GenLayer fits if they do not fetch or verify live facts such as local rules, safety conditions, weather, prices, availability, policy changes, market data, or other time-sensitive evidence. A stronger fit needs neutral settlement around a consequence someone could dispute, not only a plausible answer.

### Contract Engineering

Does the Intelligent Contract or ecosystem tooling actually support the product claim?

Look for:

- real GenLayer contract or valid ecosystem tooling path,
- meaningful public methods and state,
- LLM/web/non-deterministic flow that matters,
- EP/validator logic checking the meaningful result, not only output shape,
- domain-specific context, source checks, or validation that make consensus meaningful rather than just approving a plausible LLM answer,
- sensible use of `run_nondet_unsafe` when present,
- correct method mapping from app/backend to submitted contract/tooling.

For ecosystem tooling, evaluate whether the tool helps builders create, deploy, test, inspect, operate, analyze, or integrate GenLayer Intelligent Contracts.

### Engineering Quality

Does the codebase show coherent implementation judgment?

Look for:

- repo structure that fits the use case,
- appropriate framework/language choices,
- real integration between components,
- setup/deploy instructions that make the project reviewable,
- handling of important edge cases and errors,
- evidence of original product logic rather than pasted boilerplate,
- frontend/backend behavior that reflects the claimed workflow.

Do not treat repo size, generated UI, screenshots, file count, or marketing language as meaningful evidence by themselves.

## Output Principle

The final output should be brief, concrete, and human-readable.

It should help the reviewer quickly answer:

- What is this project?
- How does it use GenLayer?
- What is the strongest case for it?
- What is the strongest concern?
- What should I manually verify?

The final output should not include:

- numeric outputs,
- final portal decisions or reward guidance,
- portal-write JSON,
- raw checklists,
- internal chain-of-thought,
- long repository trees.

The final output may include a clearly labeled provisional opinion about whether the project appears strong, borderline, below the Project bar, or not assessable from available evidence. That opinion must be short and evidence-backed.
