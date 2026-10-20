# Orchestrator Four-Agent Workflow

Use this workflow when a reviewer wants an end-to-end AI-assisted Project review with a final scoring proposal.

The orchestrator controls context separation. Do not let the Positive Evidence Agent or Adversarial Evidence Agent see each other's outputs. Do not let either agent assign scores, points, or decisions.

## Input To Collect

```text
Submission id:
Project name:
Repository URL:
Live app URL:
Deployed contract / Studio / explorer URL:
Submission notes:
Appeal or resubmission context:
Gate handoff, if available:
Additional reviewer context:
```

## Files To Use

Core context for all source-review agents:

- `context/00_GenLayer_Basics.md`
- `context/02_Evidence_Review_Rules.md`
- `context/04_Inspection_Checklists.md`
- `context/08_Narrative_Output_Style.md`
- `context/09_Agent_NonScoring_Review_Context.md`
- `context/10_Three_Agent_Review_Flow.md`

Prompts:

- `prompts/Positive_Evidence_Agent_Prompt.md`
- `prompts/Adversarial_Evidence_Agent_Prompt.md`
- `prompts/Synthesis_Agent_Prompt.md`
- `prompts/Scoring_Agent_Prompt.md`

Templates:

- `templates/Positive_Evidence_Brief.md`
- `templates/Adversarial_Evidence_Brief.md`
- `templates/Synthesized_Reviewer_Memo.md`
- `templates/Scoring_Proposal.json`

Scoring-only context:

- `context/11_Scoring_Agent_Context.md`
- `context/12_Scoring_Calibration_Anchors.md`

Optional tool:

- `tools/fetch_genlayer_contract.py` for deployed contract source fetching when no repository contract source covers the submitted deployment.

## Execution Order

### 1. Evidence Packet

Build one evidence packet containing the submission metadata, URLs, notes, and any appeal/resubmission context. Include only current submitted evidence and necessary review history. Do not include prior opinions as facts.

### 2. Positive Pass

Launch the Positive Evidence Agent with:

- the evidence packet,
- `prompts/Positive_Evidence_Agent_Prompt.md`,
- the required non-scoring context and positive template.

The agent outputs only `templates/Positive_Evidence_Brief.md`.

### 3. Adversarial Pass

Launch the Adversarial Evidence Agent in parallel with the positive pass when possible.

Give it:

- the same evidence packet,
- `prompts/Adversarial_Evidence_Agent_Prompt.md`,
- the required non-scoring context and adversarial template.

Do not give it the positive brief. It outputs only `templates/Adversarial_Evidence_Brief.md`.

### 4. Synthesis Pass

After both briefs are complete, launch the Synthesis Agent with:

- the evidence packet,
- the Positive Evidence Brief,
- the Adversarial Evidence Brief,
- `prompts/Synthesis_Agent_Prompt.md`,
- the synthesis template.

The synthesis agent outputs only `templates/Synthesized_Reviewer_Memo.md`.

### 5. Scoring Proposal Pass

Launch the Scoring Agent last with:

- submission metadata,
- the evidence packet,
- gate handoff if available,
- both briefs,
- the synthesized memo,
- any human frontend testing notes,
- `prompts/Scoring_Agent_Prompt.md`,
- `context/04_Inspection_Checklists.md`,
- scoring context and scoring template.

The scoring agent outputs one compact JSON object matching `templates/Scoring_Proposal.json`. For multiple submissions, collect these as JSONL: one object per submission, one line per object.

The scoring agent may inspect source evidence directly if needed to resolve an important contradiction. If it cannot resolve a material contradiction because evidence is inaccessible or not reviewed, it must use `skip`.

## Final Package For The Reviewer

Return:

1. the synthesized reviewer memo,
2. the scoring proposal JSON,
3. any evidence access blockers or manual verification items.

Do not submit to the portal unless the reviewer explicitly asks for portal submission and provides the required authorized workflow. This kit can produce proposal-shaped JSON without needing portal API access.

## Guardrails

- Evidence access blockers override scoring.
- Gate failures override scoring.
- Frontend visual quality is never scored.
- The scoring agent submits pre-multiplier points only.
- Extras are recorded, not added to points.
- User-facing feedback must be short, human, and specific.
- Appeals and resubmissions require checking the new information against the prior request or appeal claim.
