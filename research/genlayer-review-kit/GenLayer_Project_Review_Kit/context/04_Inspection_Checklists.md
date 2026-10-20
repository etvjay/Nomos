# Inspection Checklists And Official Reference Map

Use this file while inspecting Project evidence. It is a practical checklist, not a final judgment guide.

## Core Trust Model Question

Ask this before getting excited about the product:

> If GenLayer is removed, does the product lose its core trust model?

If removing GenLayer leaves essentially the same product, the project probably has weak GenLayer dependence. If removing GenLayer breaks fairness, verification, consensus, payout, ordering, eligibility, moderation, or trust assumptions, the project may have meaningful GenLayer dependence.

Also ask:

- Is GenLayer deciding something meaningful, or just producing flavor text?
- Is validator consensus tied to the core user value?
- Would a centralized backend, simple oracle, or normal smart contract do the same job just as well?
- Is the use case specific and thought through, or just "AI decides X"?

## Evidence Inventory Checklist

Look for:

- Repository URL.
- Contract files.
- Deployed contract address and network.
- Transaction hashes or explorer links.
- Live app URL.
- Demo video.
- Public post.
- README and docs.
- Dependency files.
- Deploy scripts.
- Tests or simulation files.
- Commit history.
- Frontend/backend integration code.
- Environment examples or network config.

If evidence is missing, write `not found`. Do not infer missing evidence from claims.

## Contract Markers

Search contract source for:

- `from genlayer import *`
- `import genlayer as gl`
- `gl.Contract`
- older `IntelligentContract`
- `@gl.public.write`
- `@gl.public.write.payable`
- `@gl.public.view`
- `@gl.private`
- class-level typed storage
- `TreeMap`, `DynArray`, `Array`, `Address`, `u256`
- `gl.message.sender_address`
- `gl.message.value`
- `gl.nondet.exec_prompt`
- older `gl.exec_prompt`
- `gl.nondet.web.render`
- `gl.nondet.web.get`
- older `gl.get_webpage`
- `gl.eq_principle.strict_eq`
- `gl.eq_principle.prompt_comparative`
- `gl.eq_principle.prompt_non_comparative`
- older strict/nondet helper names
- `gl.vm.run_nondet_unsafe`
- `gl.vm.Return`
- `gl.vm.UserError`
- `gl.vm.VMError`
- `gl.chain.Account(...).emit_transfer`

Review what these markers do. Do not award quality merely because markers exist.

## Deployment And Executability Markers

Look for:

- deployed address,
- network: StudioNet, Bradbury, Asimov, localnet,
- transaction hashes,
- explorer links,
- Studio import URL,
- deploy script,
- README deployment steps,
- constructor args,
- network config,
- environment example,
- receipt handling,
- lint/test commands.

For deployed source acquisition, use `tools/fetch_genlayer_contract.py` when available.

Manual review rule:

Do not write "passed GenVM lint" unless a real linter was run. If you only inspected source manually, write:

`Conceptual GenVM lint concern: ...`

SDK/header nuance:

- Missing runner/dependency headers are a compatibility or confidence concern, not an automatic reject when the project is otherwise real.
- `py-genlayer:test`, `py-genlayer:latest`, older helper names, or missing pinned GenVM hash are not automatic rejects.
- Reject only when the code is fabricated, materially misleading, or not reviewable as real GenLayer work.

## GenLayerJS / App Integration Markers

Search frontend/backend code for:

- `genlayer-js`
- `createClient`
- `readContract`
- `writeContract`
- wallet/account connection
- signer/client creation
- contract address config
- network selection
- ABI/schema/method mapping
- transaction receipt handling
- pending/accepted/finalized states
- contract-derived UI state
- error handling
- mock/sandbox/fallback paths
- server-side AI calls that shadow or replace contract results

Integration questions:

- Does the app call the submitted contract methods that matter?
- Are core results read from contract state?
- Are writes signed or otherwise justified?
- Does the UI show pending/accepted/finalized status when relevant?
- Does a server/backend decide the core AI result instead of the contract?
- Is mock/fallback behavior optional, or does it replace the real contract path?

False integration is a gate issue. A flawed but real integration is usually `more_info`.

## Equivalence Principle Pattern Fit

The validator must check the meaningful result, not just output shape.

### Comparative / Strict Equality

Use when output is deterministic or canonicalizable:

- exact structured fields,
- normalized JSON with sorted keys,
- deterministic extracted facts,
- numeric outputs with tolerance if explicitly implemented.

Risk:

- strict equality on subjective LLM prose is brittle.

### Numeric / Tolerance Comparison

Useful for prices, numeric evaluations, probabilities, or measurements.

Check:

- tolerance is explicit,
- tolerance cannot flip reject into accept,
- units and normalization are clear,
- source data is independently fetched or recomputed.

### Comparative LLM Judgment

Useful for subjective but comparable results.

Check:

- criteria are explicit,
- validator compares meaningful decision fields,
- source evidence is included,
- output is constrained enough for stable comparison.

### Non-Comparative Validation

Useful for open-ended summaries or qualitative text judged against explicit criteria.

Non-comparative does not mean trusting the leader. The validator still checks the leader output against source data and acceptance criteria.

Do not use non-comparative validation as a schema check for classification, numeric evaluation, extraction, authenticity, ordering, settlement, or payout decisions.

## Weak / Shape-Only Validators

Shape-only validation usually caps contract quality at 1.

Examples:

- valid JSON only,
- expected keys exist,
- output is non-empty,
- string length within range,
- confidence between 0 and 100,
- winner is a string,
- enum value is allowed,
- summary exists,
- no independent source/evidence check,
- validator re-runs an LLM but never compares the relevant verdict/result.

These checks prevent crashes; they do not prove correctness, fairness, or equivalence.

## Stronger Validator Signals

Stronger validators:

- re-fetch/recompute source data,
- compare decision fields,
- check winner/top-result consistency,
- ensure output references valid participants/items,
- compare numeric outputs with tolerance,
- verify ordering or eligibility against submitted evidence,
- use comparative/non-comparative EP with explicit criteria,
- handle `Return`, `UserError`, and `VMError`,
- bound inputs/outputs,
- avoid replay/double-finalization.

## Advisory And Recommendation Fit Checks

For travel planners, crop-treatment assistants, health-style triage, tutors, financial suggestions, and other advisory products, check whether the contract is verifying current facts or only producing a plausible LLM answer.

GenLayer consensus has cost, latency, and operational overhead. For advisory products, that overhead needs a reason beyond "multiple validators may produce a better answer." Stronger projects explain why the answer needs trustless settlement; weaker projects mainly need a fast, current, specialized AI/backend workflow.

Weak signals:

- no contract-side web fetch or other independent source verification,
- heavy reliance on LLM training data for facts that change over time,
- no check for current safety, geopolitical, weather, regulatory, price, availability, or market conditions when those facts matter,
- validators only judge whether the answer is helpful or well formatted,
- no domain-specific source checks, context, or validation beyond generic LLM plausibility,
- no contested party, payout, eligibility decision, escrow, marketplace consequence, moderation action, attestation, or other value-bearing result.

Stronger signals:

- contract-side fact-checking from web-fetching capabilities or another verifiable source,
- clear handling of time-sensitive facts relevant to the use case,
- domain-specific context and validator checks that test the actual result, not just coherence or usefulness,
- validator consensus tied to a result someone could dispute or benefit from biasing,
- output affects a concrete workflow such as claim approval, escrow release, eligibility, reward, audit, moderation, or verified marketplace action.

## Official Docs Reference Map

Use current official docs when available. Useful reference topics:

- Intelligent Contracts introduction: `https://docs.genlayer.com/developers/intelligent-contracts/introduction`
- Equivalence Principle: `https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle`
- GenLayerJS: `https://docs.genlayer.com/api-references/genlayer-js`
- Testing: `https://docs.genlayer.com/developers/intelligent-contracts/testing`
- GenVM linter: `https://docs.genlayer.com/api-references/genlayer-linter`
- Optimistic Democracy / protocol concepts: `https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy`
- Skills/examples: `https://skills.genlayer.com`
- GenLayer SDK runner docs: `https://sdk.genlayer.com/main/python-sdk/runners/index.html`

If a reviewer cites a doc URL, the cited topic must match the issue.

## Official Examples / Boilerplate Comparison

Compare suspicious projects against official examples and common boilerplate:

- Storage / user storage examples.
- LLM hello-world.
- Wizard of Coin.
- Fetch web content examples.
- Football prediction / betting boilerplate.
- GenLayer project boilerplate.
- Skills from `skills.genlayer.com`.

Questions:

- Is this mostly a renamed example?
- Did the builder add meaningful product logic?
- Are there new contracts, new state transitions, real integration, or new validator design?
- Is the frontend just restyled boilerplate?
- Does the README overclaim beyond the code?

Renamed examples with cosmetic changes are gate rejects or very low value. Meaningful extension of a known pattern can be valid.

## Reviewer Justification Lines

Use concise language:

- A real GenLayer project needs evidence that GenLayer is central to the trust model, not only named in the README.
- A contract-looking file is not enough; the submitted source must be reviewable as real GenLayer code.
- A validator that only checks JSON shape, expected keys, or numeric ranges does not validate the substance of the AI result.
- A live app that claims contract integration must show a real read/write path to the submitted contract methods.
- Missing deploy proof lowers confidence, but deployment is not mandatory when source evidence is complete and accessible.
- Tests are positive evidence, but missing tests are not a hard cap by themselves.
