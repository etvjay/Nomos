# PPA Adjudication Producer — Decision Boundary

## What it is
The judgment source in the Core / Adapter / Producer split. It turns one
external evidence question into one terminal, content-bound receipt:

    ACCEPTED | REJECTED | UNDETERMINED

## What it owns
- The question registry: https evidence URL + clause + TTL, with a
  deterministic `question_hash` over the canonical `(url, clause)` JSON.
- One nondeterministic operation per decision: `gl.nondet.web.render` of the
  evidence URL plus `gl.nondet.exec_prompt` judgment, executed under
  `gl.vm.run_nondet` with **comparative equivalence** — validators
  independently re-fetch and re-judge, and consensus requires exact agreement
  on the triple `(satisfied, verdict, confidence)`.
- `evidence_hash`: sha256 over the normalized observation envelope (url, byte
  count, bounded excerpt, decision triple, retrieval time). Content-derived;
  never a placeholder.
- The emit of the exact 10-field Adapter receipt to the bound Adapter
  (`emit(on="accepted").submit_decision_receipt`).

## What it deliberately does not own
- No balances, no deposit/withdraw, no capital or commitment authority.
- No Core address, no Core call path, no proposal/dispatch/settlement surface.
  A producer `ACCEPTED` is not money; Core independently re-gates everything.
- No claim of Adapter acceptance from inside the contract: a successful emit
  is honestly recorded as `QUEUED`; delivery is proven by Adapter-side
  readback. A raising emit is recorded as `EMIT_FAILED` and any caller may
  re-deliver via `submit_receipt` (idempotent at the Adapter by
  `decision_id` replay rejection).

## Canonicalization (fail-closed)
- `ACCEPTED` iff `(satisfied=true, verdict="delivered", confidence="high")`.
- `REJECTED` iff `(false, "not_delivered", "high")` — confident negative.
- Everything else — ambiguous, low confidence, malformed model output,
  evidence unavailable (fetch failure), failed equivalence — `UNDETERMINED`.
  Judgment can never be silent: every decision id resolves to exactly one
  terminal status before submission.

## Authority separation
The owner EOA registers the producer CONTRACT as the Adapter adjudicator.
Receipts must arrive with `msg.sender` = the producer contract address; the
owner EOA submitting a crafted receipt is `UNREGISTERED` at the Adapter.
Replay of a `decision_id` inside the producer is `REJECTED_REPLAY`.
