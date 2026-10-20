# Scoring Calibration Anchors

Use these anchors to prevent inflated Project scoring. They are not examples to copy; they are pressure tests for the scoring agent.

## Global Calibration

- Real GenLayer usage is the start of review, not proof of high quality.
- Most valid submissions should score 1 to 2 in at least one section.
- A project with 3 or more in every section should have clear, cited evidence that it is more than a generic demo.
- A 4 means clearly strong. A 5 means exceptional.
- Pretty UI, many files, and AI-generated polish do not raise scores.
- Frontend visual polish is not scored.

## Fit Anchors

Low fit:

- The product mainly gives advice, summaries, plans, or recommendations.
- The main benefit is "more AI opinions" or "better answer quality."
- No one has a clear incentive to bias the result.
- No payout, eligibility, moderation, audit, claim, escrow, ranking, game result, marketplace action, or other consequence depends on the consensus result.
- The contract does not verify current facts that the answer depends on.

Middle fit:

- GenLayer consensus supports a real workflow, but a centralized operator could still plausibly run it.
- The outcome has some trust sensitivity, but the product does not deeply use validator consensus.
- The use case is common but implemented with a specific enough edge to be credible.

High fit:

- The result settles something someone could dispute or benefit from biasing.
- Validators evaluate external evidence or domain-specific facts tied to a consequence.
- The product design would be meaningfully worse if a single party decided the outcome.
- The use case is specific, thoughtful, and GenLayer-native.

## Contract Quality Anchors

Low contract quality:

- One thin contract around an LLM call.
- Validators check only JSON shape, labels, enum values, keywords, length, or generic helpfulness.
- The contract stores a plausible answer but does not validate the meaningful result.
- The prompt is broad and the output is not tied to verified evidence.
- The contract is a renamed canonical example or shallow modification.

Middle contract quality:

- Real state and public methods.
- Non-deterministic flow affects the project workflow.
- EP or validator logic checks the actual result, but validation is still basic.
- Prompts and parsing are constrained enough to review.

High contract quality:

- Strong EP choice for the output type.
- Validators check the meaningful value, not just shape.
- Web fetching, source verification, domain-specific validation, or leader/validator logic materially improves trust.
- Multiple specialized/interacting contracts or a strong architecture justify the complexity.

## Engineering Anchors

Low engineering:

- Messy scaffold, code dump, thin single file, or pasted boilerplate.
- The repo looks generated without enough product-specific decisions.
- Setup, integration, or core flow is unclear.
- Important errors and edge cases are ignored.

Middle engineering:

- Coherent structure for the project size.
- Components connect in the expected way.
- Setup and deployment evidence are understandable.
- The code shows some original decisions beyond the scaffold.

High engineering:

- Architecture choices match the use case.
- Important failure modes are handled.
- Frontend/backend/contract integration is clear and reliable.
- The repo demonstrates the builder understood GenLayer and the surrounding tools.

## Quality Reject Pressure Test

Before rejecting a gate-passed project for quality, ask:

- Is it merely low-scoring but still a real valid Project? If yes, accept with low points.
- Is the main issue a narrow fix or clarification? If yes, use `more_info`.
- Is the problem that material evidence is inaccessible? If yes, use `skip`.
- Is the project so thin, generic, decorative, or unverifiable that Project credit would be misleading? If yes, reject and explain the concrete reason.

Quality reject should be uncommon, but available when the evidence clearly shows the project does not meet the minimum Project bar.
