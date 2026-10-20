# External Reviewer Three-Agent Workflow

Use this non-scoring workflow when a reviewer has repository URLs, live app URLs, deployed contract URLs, or submission notes, but no portal API access.

If the reviewer wants scores or a proposal JSON, use `prompts/Orchestrator_Four_Agent_Workflow.md` instead.

Input to collect from reviewer:

```text
Repository URL:
Live app URL:
Deployed contract / Studio / explorer URL:
Submission notes:
Additional context:
Project name:
Submission id:
```

Run three isolated passes:

1. Positive Evidence Agent
   - Use `prompts/Positive_Evidence_Agent_Prompt.md`.
   - It reviews source evidence and writes `templates/Positive_Evidence_Brief.md`.
   - It should not receive any adversarial brief.

2. Adversarial Evidence Agent
   - Use `prompts/Adversarial_Evidence_Agent_Prompt.md`.
   - It reviews the same source evidence independently.
   - It must not read the positive brief.

3. Synthesis Agent
   - Use `prompts/Synthesis_Agent_Prompt.md`.
   - It receives both briefs and writes `templates/Synthesized_Reviewer_Memo.md`.

Final output to the human reviewer:

- only the synthesized reviewer memo,
- no raw internal briefs unless the reviewer asks,
- no portal-write output,
- no final portal decision, points, or reward guidance,
- a concise reviewer orientation is allowed when it is clearly evidence-backed.
