---
kit: genlayer-project-review
version: 2026-07-08
---

# GenLayer Project Review Kit

This is a self-contained review kit for GenLayer Builder `Project` submissions reviewed from evidence URLs.

It is designed for external reviewers who usually have:

- a GitHub repository URL,
- optionally a live app URL,
- optionally a deployed contract, Studio, or explorer URL,
- optionally submitter notes.

## Purpose

The kit supports two review modes:

1. a non-scoring memo mode for external reviewers,
2. a four-agent proposal mode where a separate scoring agent produces conservative scores and pre-multiplier points.

In both modes, source evidence must be inspected directly. The evidence agents should produce a concise reviewer memo covering:

- what the product is,
- how it uses GenLayer,
- what evidence supports it,
- what the strongest concerns are,
- whether the reviewed evidence appears strong, borderline, below the Project bar, or not assessable,
- what the human reviewer should verify manually.

The Positive Evidence Agent, Adversarial Evidence Agent, and Synthesis Agent must not produce portal-write JSON, numeric outputs, or allocation guidance. The optional Scoring Agent is the only role allowed to assign `genlayer_fit`, `contract_quality`, `engineering`, and pre-multiplier points.

## Preferred Flow

Use the three-agent workflow when the reviewer only needs a memo:

1. **Positive Evidence Agent**
   - Reviews the evidence independently.
   - Extracts the strongest product, GenLayer, implementation, and integration signals.

2. **Adversarial Evidence Agent**
   - Reviews the same evidence independently.
   - Does not read the positive brief.
   - Pressure-tests GenLayer fit, contract/tooling design, integration, and implementation quality.

3. **Synthesis Agent**
   - Reads both briefs.
   - Produces one concise reviewer-facing memo.

The human reviewer sees only the synthesized memo unless they ask for the internal briefs.

Use the four-agent workflow when the reviewer also wants a proposal. Run the first three roles above, then run:

4. **Scoring Agent**
   - Reads the evidence packet, both briefs, the synthesized memo, gate handoff, and any human frontend test notes.
   - Applies strict scoring only after evidence access and gates are resolved.
   - Produces one JSON proposal with three section scores, pre-multiplier points for accepts, internal reasoning, and brief user-facing feedback.

## File Map

- `context/00_GenLayer_Basics.md` — protocol facts, SDK compatibility, real/fake primitives.
- `context/02_Evidence_Review_Rules.md` — GitHub, Studio, live app, X, article, and access rules.
- `context/04_Inspection_Checklists.md` — API markers, GenLayerJS markers, EP pattern fit, examples/boilerplate comparison, docs map.
- `context/08_Narrative_Output_Style.md` — writing style for positive, adversarial, and synthesized review artifacts.
- `context/09_Agent_NonScoring_Review_Context.md` — agent-facing project policy without final-decision guidance.
- `context/10_Three_Agent_Review_Flow.md` — preferred external-review flow with isolated positive, adversarial, and synthesis passes.
- `context/11_Scoring_Agent_Context.md` — strict decision, scoring, point formula, and feedback rules for the final scoring agent only.
- `context/12_Scoring_Calibration_Anchors.md` — compact anchors to prevent inflated fit, contract quality, and engineering scores.
- `templates/Positive_Evidence_Brief.md` — output shape for the positive pass.
- `templates/Adversarial_Evidence_Brief.md` — output shape for the adversarial pass.
- `templates/Synthesized_Reviewer_Memo.md` — final reviewer-facing memo.
- `templates/Scoring_Proposal.json` — output shape for the final scoring proposal.
- `prompts/External_Reviewer_Three_Agent_Workflow.md` — operator instructions for the full flow.
- `prompts/Orchestrator_Four_Agent_Workflow.md` — operator instructions for the full evidence, synthesis, and scoring proposal flow.
- `prompts/Positive_Evidence_Agent_Prompt.md` — isolated positive pass.
- `prompts/Adversarial_Evidence_Agent_Prompt.md` — isolated adversarial pass.
- `prompts/Synthesis_Agent_Prompt.md` — final memo synthesis.
- `prompts/Scoring_Agent_Prompt.md` — final scoring/proposal pass.
- `tools/fetch_genlayer_contract.py` — optional helper for deployed contract source fetching.

## Non-Negotiables

- Review evidence directly. Do not rely on README claims, screenshots, titles, cached excerpts, contributor history, or prior review text.
- Access limitations are evidence blockers, not project conclusions.
- X posts require Sorsa or an equivalent X post fetcher. If the post cannot be fetched, mark the evidence limitation.
- Articles require readable body text extraction.
- Studio/explorer evidence requires contract source inspection, not just a shell page.
- `gl.vm.run_nondet_unsafe(...)` is official SDK usage. Do not treat the word `unsafe` as a problem by itself.
- Older SDK names and missing recent dependency pins are compatibility issues, not automatic blockers.
- Ecosystem tooling can be valid without its own Intelligent Contract if it directly helps builders create, deploy, test, inspect, operate, analyze, or integrate GenLayer Intelligent Contracts.
- Deterministic helper contracts are allowed in multi-contract projects when at least one contract has meaningful non-deterministic GenLayer consensus.
- Advisory or recommendation apps need extra GenLayer-fit scrutiny: better AI accuracy is not enough unless the contract verifies current facts or settles a contested/value-bearing outcome.
- GenLayer consensus has cost, latency, and operational overhead. Do not treat it as a normal LLM call with extra reviewers; the project should justify why the result belongs in trustless consensus.
- Frontend visual polish is outside this review; frontend is used only to understand workflow and integration.
- The final external-review output is the synthesized reviewer memo, not raw checklists or internal briefs.
- The synthesis may openly say that a project appears strong, borderline, below the Project bar, or not assessable, but only with concrete evidence and uncertainty notes.
- Only the Scoring Agent may output scores, points, or proposal JSON. It scores three sections only: `genlayer_fit`, `contract_quality`, and `engineering`.
- Scoring proposals use pre-multiplier points: `Q = (F / 5) * ((2*C + 2*E) / 20)`, `points = round(50 * Q)`. Do not multiply by 20, score frontend, or add extras into points.
- A quality reject is allowed when a gate-passed project is still too thin, generic, decorative, or unsupported to meet the Project bar. Low fit alone is not enough: valid fit-1 projects can still receive low-point accepts.

## Exporting

This folder is intentionally standalone. It should not require files from the original review workspace.

Recommended export. This intentionally excludes local review runs, fetched portal data, contract fetch caches, and Playwright logs:

```sh
zip -r GenLayer_Project_Review_Kit.zip Project_Review_Kit -x 'Project_Review_Kit/data/*' 'Project_Review_Kit/reviews/*' 'Project_Review_Kit/.playwright-mcp/*' 'Project_Review_Kit/__pycache__/*'
```
