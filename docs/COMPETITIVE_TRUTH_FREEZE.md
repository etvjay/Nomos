# Competitive Truth Freeze — Nomos Showcase (Research Foundry + EBI)

**Decision to inform:** How to position Nomos Intelligent Accounts / PPA showcase without overclaiming spend-limit novelty, and where live Bradbury adjudication creates a defensible delta.

**Method:** Research Foundry (source-verified) + Evaluated Build Instantiation (truth freeze, requirement classes, evidence states). Sources accessed 2026-08-27.

## Finding: spend gates are commodity

Per-tx cap, daily cap, allowlist, expiry, delegation, and conditional trigger are **not** unique to Nomos.

| Capability | ERC-7710 (Delegation Framework) | ERC-4337 session keys | Safe + Zodiac | Lit PKP + Lit Actions | Chainlink Automation + Functions | Nomos PPA (Bradbury `0xa0a78...`) |
|---|---|---|---|---|---|---|
| allowlist / allowedTargets | caveat `allowedTargets` in `permissionContext` | `allowed contracts/methods` in session key | `ScopeGuard` scopes `addresses + selectors` | `Lit Action` checks condition before `signEcdsa` | `checkUpkeep` offchain check | `rules.allowlist` + `_deny(POLICY_DENYLIST)` |
| perTx limit | caveat `valueLte` / `nativeTokenLimit` | `spending limit per tx` | `SpendingLimit` module per token | JS condition `amount <= cap` | custom logic in upkeep | `per_tx_limit` gate + `DELEGATE_PER_TX_LIMIT` |
| daily/period limit | caveat with `period` | `spending limit per period` | `daily spending limits per token per time window` | timer + state | upkeep window | `daily_limit` rolling 86400s `_roll_daily_window` |
| delegation + expiry | `redeemDelegations(permissionContexts, modes, executionCalldatas)` + EIP-712 + revocation | session key expiry, `exp` | module signer with limit | `Mint-Grant-Burn` PKP → Action grant | n/a | `delegate(principal, perTx, daily, expires)` + narrowing vs account rules |
| conditional `if X then pay` | caveat + external check then redeem | session policy + bundler | guard + offchain bot | `fetch()` + `if (cond) sign()` + Event Listener (webhook / onchain event / interval) | `checkUpkeep → performUpkeep` + Functions `fetch API` | `gl.nondet.web.render + LLM → validator quorum` |

Sources: [EIP-7710](https://eips.ethereum.org/EIPS/eip-7710), [MetaMask SMT Kit ERC-7710](https://docs.metamask.io/smart-accounts-kit/reference/erc7710/wallet-client/), [ERC-4337 spending limits](https://silencelaboratories.com/blog/account-abstraction-wallets-smart-accounts-erc-4337-and-where-mpc-fits) [Cobo AA guide](https://www.cobo.com/post/account-abstraction-wallet), [Zodiac ScopeGuard](https://github.com/gnosisguild/zodiac-guard-scope), [abstracted-limit Safe](https://github.com/cupOJoseph/abstracted-limit), [Lit PKP programming](https://spark.litprotocol.com/programming-bitcoin) [Lit Actions](https://spark.litprotocol.com/working-with-lit-actions) [Lit Event Listener](https://spark.litprotocol.com/lit-event-listener-sdk), [Chainlink Automation](https://chain.link/blog/chainlink-automation-open-beta-is-live) [Programmable Payments](https://chain.link/article/programmable-payments), [Nomos ppa.py:214-236](primitives/ppa/implementations/genlayer/ppa.py), [GENLAYER_TRUTH_FREEZE.md](GENLAYER_TRUTH_FREEZE.md)

**Implication:** Claiming `we invented spend limits` is `E0 assertion → FAILED` under EBI pressure. Evaluator pressure class is `INFERRED_EVALUATOR_PRESSURE` (judge checks EIP/Safe docs), not `PUBLISHED_HARD`.

## Defensible delta (account-relevant, not marketing)

### 1. Adjudication as part of the account transaction vs automation as external service
Chainlink/Lit check `price > X` or `status == ok` deterministically, or run one TEE/operator judgment. GenLayer puts **natural-language agreement adjudication** inside the account's own execution: `gl.nondet.web.render + LLM` → leaders propose verdict → validators independently evaluate → **Equivalence Principle** (`strict / comparative / non-comparative / custom`) decides `accepted / rejected / undetermined`. Result is consensus on Bradbury, not an oracle report ingested by the account. See `GENLAYER_TRUTH_FREEZE.md:28-42` (Optimistic Democracy, Equivalence).

Account consequence: the account stores `DETERMINISTIC POSTCONDITIONS` strictly separate from `INTELLIGENT QUESTION + STRUCTURED DECISION + UNDETERMINED PATH` (see `AGENTS.md` GenLayer rule). The commodity path needs trust in one operator/TEE for the language judgment; the Intelligent Account needs quorum.

### 2. Financial object completeness as account state
7710/4337/Safe revert on failure. PPA retains **`DENIED` as state**: `_deny()` records `DENIED: POLICY_PER_TX_LIMIT` etc, burns nothing, **id stays retryable after rule change**, and never consumes encumbrance. Daily `spent + window_start` and `balance - committed = available` are first-class fields with rolling window and refund-compensation path (`Gaia`: `REFUNDED` is compensating entry, history never rewritten). This is the `EXACT` primitive stack (10/11 CONFORMANT) embedded as one `gl.Contract` with `TreeMap` accounts/payments/invoices/disputes — not a Safe with three deployed guards + offchain signer.

### 3. One-contract bounded treasury (zero-imprint)
Safe: 2/2 + SpendGuard + ScopeGuard + external signer infra. 4337: bundler + paymaster + session store. PPA: one deployed contract (`0xa0a78...`, functional verification `3000→1200→1800` in `convergence/deployment/ppa-bradbury.json`). Frontend calls it directly without bridging to a second network for the judgment.

### 4. Boundary is explicit, not hidden
Every PPA method declares `JUDGMENT_BOUNDARY = NONE` for v0.1 (deterministic). The showcase separates `judgment proposes; determinism disposes`. Commodity demos hide the judgment boundary inside a bot.

## Showcase story fix

Old story (weak): `App1 = send with limits` (everyone does this → evaluator: "so what?").

New story (EBI pressure: judge asks "why not just use 7710/Safe?") — lead with delta:

**Act 1 — Control (App1: Send with Rules) — `what everyone can do, shown live as baseline`**
One live `ops` account `allowlist=[VendorA,VendorB] perTx=200 daily=500`:
- Tx1 150 → VendorA → `SETTLED` hash + `balance 850 daily 150`
- Tx2 250 → VendorA → `DENIED: POLICY_PER_TX_LIMIT` stored, balance unchanged
- Tx3 50 → VendorC → `DENIED: POLICY_DENYLIST`
Single timeline, real hashes, explorer links. Establishes "we also do limits, but note DENIED stays auditable and idempotent."

**Act 2 — Delta (App2: Adjudicate then Pay) — `what commodity does with extra trust`**
Same `ops` account, different condition: *not* `price > X`, but `does this vendor PDF + public SLA page satisfy clause 4.2 (natural language) ?` → needs LLM judgment. Commodity: Lit Action or Chainlink Function runs one judge/TEE you trust. Ours: same account method triggers GenLayer quorum → `accepted / rejected / undetermined` → only then `policy → encumbrance → settle`. Show `UNDETERMINED = no pay, safe` vs single-operator trust.

**Act 3 — Composition (App3: Invoice) — `judgment-gated encumbrance`**
`claim_verification.verify_claim` → `VERIFIED` vs `CONFLICTED/INSUFFICIENT` branching → only `VERIFIED` unlocks `claim_encumbrance.reserve` → settle. Mirrors `examples/verified-receivable` already proven; shows full stack without claiming invoice is novel.

Reframe copy on the single shell to open with: `Anyone can enforce limits. The difference is who judges the condition that allows the spend — one operator you trust, or validator quorum inside the account transaction.`

## Evidence states

- App1 gates on Bradbury: `TESTNET_PASS` (functional verification 2026-08-23 `LIFE-ACC`)
- App2 adjudication on Bradbury with real models: `SIMULATED_PASS` today (`GLSim` + `mock_llm`), `TESTNET_PASS` required before claiming `PUBLIC_EVALUATOR_PASS`. Labeled `INFERRED` until live quorum run (Goldsky/Studio style with GPT-OSS/Qwen/Claude).
- Invoice composition gate: `LOCAL_PASS` (`test_verified_receivable.py`), `SIMULATED_PASS` in harness.

## Requirements (EBI classes)

- `PUBLISHED_HARD`: Bradbury chainId 4221 reachable, wallet signing, PPA ABI present — `TESTNET_PASS` needed to claim live.
- `INFERRED_EVALUATOR_PRESSURE`: differentiation vs 7710/Safe/Chainlink/Lit must cite sources, not assert novelty.
- `UNPUBLISHED_UNKNOWN`: gas cost of adjudicated account tx on Bradbury mainnet economics — not claimed.

## Next build step

Update `apps/showcase` shell copy + nav to reflect Act1/Act2/Act3 framing, then wire App1 live (3-tx baseline) with receipt `apps/showcase/.receipts/LIVE-APP1-001.json`.
