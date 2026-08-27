# Showcase Apps Spec — Nomos on GenLayer

One frontend, three sequential apps. One design system, three views.

## Product contract (settled)

**Goal:** Make Nomos legible in 30 seconds via usable apps, not walls of docs.

**Audience:** First users = OpenRails / GenLayer builders / agent-commerce teams. Not retail DeFi.

**Stack:** Vite + TypeScript + genlayer-js + viem (Bradbury 4221). No backend, no Stripe — patterns onchain only (per constraint). Static hosting (gh-pages / ipfs). Wallet via MetaMask-compatible (GenLayer testnet).

**Design:** One shell, editorial dark, single visual center. Top nav: `[ Send · Watch · Invoice ]`. Same account context across apps. No dashboard sprawl.

**GenLayer binding:**
- PPA at `0xe4d3f0b1119f940c5e98bc3899a595a92c988f7a` (receipt `convergence/deployment/ppa-bradbury.json`)
- Other primitives via `convergence/deployment/*-bradbury.json` (11 + PPA)
- IAS Stage1/2/3 at `convergence/deployment/ias-*` (when needed for App2)
- All writes via `genlayer-js` + `waitForTransactionReceipt` polling workaround (known rate limits)

## Information architecture

```
[Header: Nomos · Bradbury · Wallet ]
[Nav: Send with Rules | Watch & Pay | Invoice to Cash ]
[Main: single app view - one center card + activity log ]
[Footer: docs / receipts / evidence levels ]
```

No separate marketing landing. The app IS the explanation. README links to it.

## App 1 — Send with Rules (PPA) — Act 1: Control

**Job:** Baseline everyone can do, shown live to establish the commodity, then reveal our audit delta.

Live timeline on one `ops` account `allowlist=[VendorA,VendorB] perTx=200 daily=500`:
1. Connect wallet → `ppa.create_account(ops, rules)` or select existing
2. Deposit 1000 → `get_account` readback `balance 1000`
3. Send 150 → VendorA → `policy ✓ encumbrance ✓ claim ✓ settle ✓` + hash, `balance 850 daily 150`
4. Send 250 → VendorA → `DENIED: POLICY_PER_TX_LIMIT` stored, balance unchanged, id retryable
5. Send 50 → VendorC → `DENIED: POLICY_DENYLIST`

UX trace: `Rules → Reserve → Pay` but DENIED is stored (not revert) — the only delta worth showing here. Evidence: 3 hashes, explorer links, `BALANCE_BEFORE→AFTER` in receipt.

## App 2 — Adjudicate then Pay (Intelligent Account) — Act 2: Delta

**Job:** The case commodity handles with extra trust — natural-language agreement adjudication inside the same account transaction.

Not `price > X`. Use clause evidence:
- Condition: `does this vendor PDF + public SLA page satisfy clause 4.2 (natural language) ?`
- Commodity: Lit Action or Chainlink Function runs one TEE/operator judgment you trust
- Ours: same account method `gl.nondet.web.render + LLM` → leaders propose → validators compare via **Equivalence Principle** → `accepted / rejected / undetermined` on Bradbury → only then `policy → encumbrance → settle` through the same PPA pipeline

Show `UNDETERMINED = safe, no pay` and put validator votes in the trace. Failure is a feature: single-operator risk vs quorum risk.

Failure modes explicit: `UNDETERMINED`, `stale`, `rate limit`, `consensus cost`. Reuse `ias/stage1-monitor/ias_stage1.py` for v1.

## App 3 — Invoice to Cash — Act 3: Composition

**Job:** Full stack without claiming invoice is novel.

Flow:
1. Create invoice claim: `{ number, amount, asset, obligor, beneficiary }`
2. `claim-verification.verify_claim` → `VERIFIED | CONFLICTED | INSUFFICIENT | UNDETERMINED`
3. Only `VERIFIED` unlocks `claim-encumbrance.set_financeable_amount` + `reserve`
4. Settle via same gated `send`

Reuses `examples/verified-receivable` — promote it from dir to live view.

## Sequential build order

1. Shell + App1 (proves PPA, fastest live verification)
2. App2 (proves adjudication, depends on shell)
3. App3 (reuses verified-receivable, minimal new contracts)

## Out of scope v1

- Real swap / liquidity / Stripe rails (explicitly out)
- New onchain primitives (reuse existing 11)
- Cross-contract extraction v0.2 (deferred)
- 15 role profiles UI (keep to 3 views)

## Acceptance

- [ ] `npm run build` passes
- [ ] App1 live on Bradbury: create → deposit → send → balance reconciles (`35000` pattern)
- [ ] App2: monitor mock → proposal → gated pay (sim or live)
- [ ] App3: VERIFIED → reserve gate enforced (same as `test_verified_receivable.py`)
- [ ] No new taxonomies introduced; one story per app, closed
- [ ] Receipts in `apps/showcase/.receipts/`

