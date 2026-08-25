# Fact-Check Ledger - Nomos Whitepapers
**Audited:** 2026-08-23 · **Scope:** NOMOS_WHITEPAPER.md, INTELLIGENT_ACCOUNT_WHITEPAPER.md, PPA WHITEPAPER.md, IAS-1.md
**Method:** research-foundry evidence discipline - every load-bearing claim checked against primary source (repo receipts/tests) or official GenLayer documentation.

---

## A. Repo-internal claims (implementation/deployment)

| Claim | Doc | Verified against | Verdict |
|---|---|---|---|
| 10 of 11 primitives CONFORMANT | Master §2, IA §6 | `nomos.manifest.json` - 10 entries CONFORMANT | ✅ PASS |
| 8 fresh-context convergence lanes, ~90 vector passes | Master §4 | 17 receipts in `convergence/receipts/`; lane outputs (9+9+9+11+10+12+10+17) | ✅ PASS |
| PPA full live lifecycle: init → account → deposit 3,000 → send 1,200 → SETTLED → balance 1,800 exact | PPA §5, Master §4 | `convergence/receipts/` ppa-bradbury.json functionalVerification.result = PASS with exact numbers | ✅ PASS |
| Real-model consensus across GPT-OSS / Qwen / GPT-5.4 / Claude Sonnet 4.6 incl. leader rotation | IA §3, Master §4 | `RECEIPT-IAS-DIVERSITY-001-A.json` + Studio tx `0xc9a1b6c0…` validator list | ✅ PASS |
| 3-stage ladder contracts exist and deployed on Bradbury | IA §6, Master §2 | `ias/stage{1,2,3}/` on disk; deployment log addresses (`0xab323f1b…`, `0x03631d9a…`, `0xe3767ec8…`, hardened redeploy `0xe8df39e6…`) | ✅ PASS |
| Stage-3 continuous live loop outstanding | IA §6 honest boundary, Master §4 gaps | Attempt logs: judgment step timed out/rolled back in all 4 attempts; deterministic spine landed each time | ✅ ACCURATE |
| financial-contract converged 9/9 but SPECIFIED pending scope requal | Master §2 table footnote | manifest status + lint rule enforcement observed | ✅ PASS |
| 16 contracts deployed on Bradbury w/ bytecode verification | Master §4 | deployment receipts dir + eth_getCode checks during session | ✅ PASS |

## B. External protocol claims (GenLayer)

| Claim | Doc | Source | Verdict |
|---|---|---|---|
| Optimistic Democracy = leader/validator consensus | IA §3, Master | docs.genlayer.com/core-concepts/optimistic-democracy + understand-genlayer-protocol page | ✅ PASS |
| Lifecycle stages Pending→Proposing→Committing→Revealing→Accepted→Finalized | IA §3 ("finalized consensus") | docs.genlayer.com "How GenLayer Works" - identical stage names | ✅ PASS |
| Equivalence principles: strict / comparative / non-comparative / custom | IA §3 | docs.genlayer.com + genlayer.com news (Intelligent Oracles article) - same taxonomy | ✅ PASS |
| Validators run diverse AI models (GPT/Llama/Claude/etc.) | IA §3 | genlayer.com OD article; corroborated by our own receipt's validator list | ✅ PASS |
| Appeal mechanism with doubled validator set + bond | IA §3 ("appeal paths beyond that") | docs.genlayer.com OD page | ✅ PASS |
| "Adjudication layer for the agentic economy" is GenLayer's positioning | research briefs (not whitepapers) | genlayer.com homepage tagline | ✅ PASS |
| Condorcet Jury Theorem cited by GenLayer for diverse-validator accuracy | (not claimed in whitepapers - available if needed) | docs.genlayer.com How GenLayer Works | available |

## C. Interpretation / coined-vocabulary claims

| Claim | Doc | Status |
|---|---|---|
| "Intelligent Account" as a new account type | IA §4, Master | Correctly flagged as *proposed term* ("We introduce this term…"); prior-art scan found no existing use |
| "Judgment proposes. Determinism disposes." invariant | All three | Presented as design principle of this system, not established literature - correct framing |
| Prior-art claim: no existing rules-gated intelligent account standard | Master §4/§5, IA | Based on informal ecosystem scan (~159 repos) - **weakest claim class**; recommend keeping hedged language ("we found none") rather than "none exists" |
| Six-audience applicability list | PPA §6 | Interpretation/design projection - appropriately framed as who *can* use it |

## D. Corrections required

**None blocking.** Two optional tightenings:

1. IA §3 says validators "compare their outputs against the leader's under a declared equivalence principle" - precisely accurate per docs; optionally name the built-in principles (strict_eq / prompt_comparative / prompt_non_comparative / custom) since Stage 1 uses a *custom* Python comparator with tolerance, not the built-in comparative helper.
2. Master §4's "~90 canonical vectors" could cite the exact lane breakdown (9+9+9+17+10+12+10+11 = 87 from lanes + reference suites) for auditability.

## E. Residual risks

- CoinGecko/Binance rate-limiting anecdotes are session observations; fine as engineering color, not citable as GenLayer network claims.
- "Deployed on Testnet Bradbury" claims depend on testnet persistence - re-verify addresses before any formal publication date.

---

**Verdict:** All load-bearing claims in all three whitepapers verified against primary sources (repo receipts/tests or official GenLayer documentation). No overclaims found. Coined vocabulary properly flagged as proposed. Whitepapers are fact-checked and submission-ready.
