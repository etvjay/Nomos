# Positive Evidence Brief

## Project In One Paragraph

Callout is an on-chain reputation court for crypto accusations: a filer opens an evidence-backed case against a wallet or public Web3 entity, the accused can add a defense, and a GenLayer Intelligent Contract reviews the case before storing a final wallet record. The reviewed repository implements the core court workflow in `contracts/callout_reputation_court.py` and wraps it with a Next.js demo frontend for filing, docket browsing, case detail, and wallet reputation pages.

## Strongest GenLayer Argument

The strongest GenLayer fit is the contested verdict step. Accusations about rug pulls, impersonation, governance abuse, or other crypto misconduct are trust-sensitive because a filer and accused party have conflicting incentives, and the outcome can affect a wallet's public reputation. If GenLayer is removed, Callout becomes either a deterministic case registry or a centralized AI moderation service; the neutral review of natural-language accusations, evidence links, and defenses disappears. In the current contract, `review_case` is the GenLayer-dependent step: it assembles the stored case packet, asks for a `valid`, `invalid`, or `inconclusive` result, and stores the verdict and reasoning back into contract state.

## Strongest Implementation Evidence

The appeal-specific source evidence is materially stronger than the prior rejection notes described. The current `contracts/callout_reputation_court.py` uses a GenVM dependency header, `from genlayer import *`, `class CalloutReputationCourt(gl.Contract)`, class-level `DynArray`/`TreeMap` storage, five `@gl.public.write` methods, and two `@gl.public.view` methods. The public flow is concrete: `create_case`, `add_defense`, `review_case`, `finalize_verdict`, and `mark_appealed` mutate case status and stored verdict fields, while `list_cases` and `get_cases_by_accused` expose docket reads.

The corrected `review_case` path uses real GenLayer primitives rather than the previously rejected mocked `Contract`/`public`/`view`/`call_llm` placeholders. It calls `gl.nondet.exec_prompt(..., response_format="json")`, wraps that call with `gl.eq_principle.prompt_comparative(...)`, validates the returned verdict shape through `is_valid_ai_result`, and then writes `verdict`, `reasoning`, and `status` into contract storage. The latest GitHub commit, `4959a28` (`Fix GenLayer intelligent contract primitives`, 2026-06-18), directly replaces the older mocked concept contract and adds the local flow test.

Deployment evidence also supports the appeal. I fetched source for the claimed Bradbury address `0xcD216A59c0154C49DB3451b1252377960398CBE0` and Studionet address `0x846a5dcB0b4B381AdD32F970C6259551aCfc5F34` with `gen_getContractCode`; both deployed sources matched the GitHub contract exactly and compiled locally. The Studionet `gen_getContractSchema` response exposed the same five write methods and two read methods named in the appeal. The local test `tests/test_callout_reputation_court.py` also ran successfully, with the important caveat that it intentionally mocks the AI/equivalence edge for offline testing.

## Concrete Highlights

- The current contract directly addresses the prior `no_real_genlayer_contract` concern: the deployed/GitHub source now uses `gl.Contract`, `@gl.public.write`, `@gl.public.view`, `gl.nondet.exec_prompt`, and `gl.eq_principle.prompt_comparative`.
- The reviewed deployed source for both submitted addresses matched the repository source, and the Studionet schema independently listed `create_case`, `add_defense`, `review_case`, `finalize_verdict`, `mark_appealed`, `list_cases`, and `get_cases_by_accused`.
- The repository is explicit that the frontend still uses demo/mock docket data; the strongest evidence is the corrected deployed Intelligent Contract and Shippyard-style method flow, not a fully wired frontend.

## Evidence Access Notes

- `reviewed` - GitHub repository `https://github.com/justbruno1/Call-out`: inspected via `gh api`, including tree, README, commit history, contract source, tests, package manifest, frontend contract config, and mock/demo UI paths.
- `reviewed` - Bradbury deployment `0xcD216A59c0154C49DB3451b1252377960398CBE0`: source fetched via `gen_getContractCode`, matched GitHub, and `py_compile` passed; schema fetch returned `VMError: invalid_contract absent_runner_comment`, and GenVM validate was blocked by SDK load timeout.
- `reviewed` - Studionet deployment `0x846a5dcB0b4B381AdD32F970C6259551aCfc5F34`: source fetched via `gen_getContractCode`, matched GitHub, schema exposed the claimed methods, and `py_compile` passed; GenVM validate was blocked by SDK load 404.
- `reviewed` - Local verification: `python3 -m py_compile /tmp/callout_fetch/contracts/callout_reputation_court.py` and `python3 /tmp/callout_fetch/tests/test_callout_reputation_court.py` both completed successfully; the test mocks AI/equivalence review as documented.
- `accessible_limited` - X post `https://x.com/justbrunoc/status/2060366794972381623?s=20`: Sorsa or equivalent X post fetcher was not available in this tool context, so I did not rely on the post content.
