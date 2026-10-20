# Narrative Output Style

The review artifacts are for human reviewers. They should read like clear briefings, not checklist dumps.

## Positive Evidence Style

The positive evidence brief should explain the strongest evidence in favor of the project as if briefing someone who has not opened the repo yet.

Use natural paragraphs. The reader should understand:

- what the product is,
- who it is for,
- what user problem or workflow it addresses,
- how the repository implements it,
- where GenLayer appears in the actual architecture,
- what the Intelligent Contract or ecosystem tool does,
- how the frontend/backend/tooling connects to it,
- what evidence was verified,
- what is genuinely interesting or worth highlighting.

Avoid turning every checklist item into its own bullet. The checklist is for inspection, not for the final prose.

Acceptable bullets:

- up to three concrete highlights,
- short human test notes,
- evidence access notes.

Weak style:

```text
Repository And Component Map
- contracts/foo.py
- frontend/bar.ts
- README
```

Better style:

```text
This is a creator-consent dispute workflow. A creator defines reuse rules, submits evidence about original and AI-generated content, and asks a GenLayer contract to produce a verdict receipt. The repo implements this as a Next.js frontend connected to a Python Intelligent Contract in `contracts/consent_vault_trial/main.py`; the frontend calls `run_trial` and later reads the stored receipt through `get_result_by_case`.
```

## Adversarial Evidence Style

The adversarial brief should be a natural critique of the project's potential and execution, not a list of axes.

It should answer:

- Is the use case actually right for GenLayer?
- Is the product built around that use case in a thoughtful way?
- Does the contract/tooling implementation support the product claim?
- Where is the trust model weak?
- What is missing before this could be a stronger project?
- What should the human reviewer be skeptical about?

Use paragraphs grouped by theme. Be direct, but fair. Do not manufacture concerns.

Weak style:

```text
Genericness / Novelty: generic AI adjudication.
Trust-Boundary Integrity: trusts frontend JSON.
Engineering Skepticism: no wallet transaction tested.
```

Better style:

```text
The use case is plausible for GenLayer because creator-consent disputes benefit from neutral adjudication, but the current implementation is still closer to an adjudication demo than a full rights-enforcement product. The contract judges text submitted by the frontend; it does not independently fetch source media, verify platform records, or anchor consent policies to an external registry.
```

## Synthesis Style

The final synthesized memo should blend the positive and adversarial briefs into one concise reviewer-facing artifact.

It should:

- keep `GenLayer Fit`, `Contract Engineering`, and `Engineering Quality` visible,
- state the strongest positives and concerns plainly,
- include only evidence-backed claims,
- include a concise reviewer orientation when the evidence supports it,
- include a short human verification checklist,
- hide internal role labels unless they help explain a conflict.

It should not:

- restate both briefs in full,
- expose raw checklists,
- make a final portal decision or reward recommendation,
- include portal-write output.

## Citation Style

Cite evidence inline with file paths, method names, URLs, or command results. Do not overload the prose with long lists.

Good:

```text
The contract stores verdict receipts in a `TreeMap` and exposes `run_trial` plus `get_result_by_case` in `contracts/consent_vault_trial/main.py`.
```

Avoid:

```text
- TreeMap
- run_trial
- get_result_by_case
- contracts/consent_vault_trial/main.py
```

## Length

Aim for:

- Positive brief: 3 to 5 concise paragraphs plus optional short highlights and evidence notes.
- Adversarial brief: 3 to 5 concise paragraphs plus reviewer watchouts.
- Synthesized memo: one brief snapshot, three lens sections, concise positives/concerns, verification checklist, evidence access.

The output should be dense enough to support human judgment, but readable enough that a reviewer can quickly explain the project to someone else.
