# Evidence Review Rules

Every material evidence URL must be inspected directly and assigned an access status:

- `reviewed`
- `accessible_limited`
- `inaccessible`
- `not_reviewed`

If any material evidence is `accessible_limited`, unresolved `inaccessible`, or `not_reviewed`, do not accept or reject on unseen content. Use `skip` / parent review.

Access limits include anti-bot pages, Cloudflare challenges, paywalls, login walls, private repos, rate limits, failed article extraction, missing credentials, or dynamic pages that cannot be fully inspected.

Explicit 404/deleted/nonexistent URLs may be treated as reviewed-invalid evidence.

## GitHub Repositories

Use GitHub/`gh`, raw URLs, or a clone. Do not rely on the README alone.

Inspect:

- repository tree,
- contract source when present,
- ecosystem tooling code when applicable,
- README/docs,
- dependency manifests,
- commit history,
- tests,
- deployment scripts,
- frontend/backend integration,
- live app configuration.

If a repo is private, auth-gated, or tool-limited, mark it `accessible_limited` unless another submitted source independently covers the same material evidence.

## Intelligent Contract Source

Review actual source. Source may come from:

- GitHub repo,
- raw `.py` file,
- local file,
- article/tutorial snippet,
- Studio/explorer URL,
- deployed address.

At minimum inspect:

- dependency header and SDK/import style,
- whether a real contract class exists,
- public methods,
- storage/state,
- nondeterministic paths,
- EP/validator logic,
- web/LLM result normalization,
- whether outputs affect meaningful state/payment/ordering/claims/moderation,
- access control and payable/transfer logic,
- frontend/backend method mapping if app integration is claimed.

For multiple contracts, review the material contracts used by the submitted project. Deterministic helper contracts are not a problem when they support a meaningful non-deterministic contract.

## Studio / Explorer / Deployed Address

Do not treat a Studio shell page or explorer address page as source review. Inspect deployed contract code.

If a helper is available, fetch source through `gen_getContractCode`. This kit includes `tools/fetch_genlayer_contract.py` for deployed address, Studio URL, and explorer URL evidence. If source cannot be fetched because of tool/RPC/browser limitations, mark the evidence `accessible_limited`; do not reject solely because the reviewer could not access source.

If a contract address clearly does not exist on the submitted network and no other source evidence exists, treat it as reviewed-invalid or ask for the correct network/address depending on context.

## Live Apps

Use browser/Playwright when feasible. Check whether the app loads and whether the intended workflow can be exercised.

For the Project review flow, live apps are mainly used to:

- verify claims,
- help the human test the frontend,
- detect false/simulated contract integration,
- understand user workflow.

Frontend visual polish is outside this agent's evaluation.

If login, wallet, auth, payment, or missing credentials blocks testing, mark the app `accessible_limited` and rely only on other accessible evidence.

## X / Twitter

Use Sorsa or an equivalent X post fetcher. Do not use browser screenshots as the normal review path.

Rules:

- Direct status URLs are valid X post evidence.
- Bare profile URLs are invalid evidence.
- If Sorsa cannot fetch the post, skip / parent review.
- Do not reject solely because X content could not be fetched.

## Articles / Blogs

Review must be based on readable body text, not just title, screenshot, subtitle, internal notes, or social preview.

Extraction success means the text contains the actual article body and enough content to evaluate technical claims.

If extraction fails after reasonable attempts, mark `accessible_limited` and skip / parent review.

Screenshots are secondary evidence only for formatting/error states.

## Resubmissions And Appeals

For every submission, inspect internal notes when available.

Identify:

- previous `more_info_needed`,
- requested changes,
- resubmitted evidence,
- edited submission notes,
- appeal arguments,
- previous AI/steward review notes.

Do not reuse prior review text as evidence. Use prior notes only to understand what was asked, what changed, and whether the current evidence addresses it.

For resubmissions:

- First ask whether the contributor provided the requested missing information/fix.
- If yes, proceed normally.
- If no, use `more_info` again only when a narrow missing item remains and the project appears otherwise valid.
- If current evidence clearly fails a gate, reject.
- If verification evidence is inaccessible, skip / parent review.

For appeals:

- Identify the prior decision and appeal argument.
- Check whether the appeal provides new evidence or shows the prior decision was wrong under current criteria.
- Do not accept an appeal just because the submitter disagrees.
- If prior rejection relied on a rule now changed, apply current criteria.
