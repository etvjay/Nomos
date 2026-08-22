# Policy Envelope — GenLayer Implementation

Deterministic-first Intelligent Contract implementing Policy Envelope v0.1.

## Public modules/interfaces

Single contract: `PolicyEnvelope` in `policy_envelope.py`.

Write methods (deterministic):
- `create_envelope(envelope_id, policy_hash, max_amount, asset, valid_after, valid_until)` — register an ACTIVE constraint object.
- `expire_envelope(envelope_id)` — ACTIVE → EXPIRED; all later requests deny.
- `evaluate_request(envelope_id, request_id, amount, asset, actor, target, at_timestamp)` — deterministic hard-limit gate. Returns ADMIT/DENY with a reason code. Admitted requests consume envelope capacity; denials consume nothing.

Write methods (declared non-deterministic surface):
- `attach_mandate_clause(envelope_id, clause_id, clause_text)` — declare a clause requiring interpretation.
- `interpret_clause(envelope_id, clause_id, facts_json, interpretation_id)` — bounded LLM judgment over the clause + caller-supplied facts. Consensus binds `decision` ∈ {ADMIT, DENY, UNDETERMINED} only; analysis prose is non-canonical.

View methods: `get_envelope`, `get_request`, `used_amount`, `get_clause_interpretation`.

## Dominance rule

`evaluate_request` never consults interpretations. Hard limits (validity window,
asset match, per-request max, cumulative capacity) are absolute vetoes. An
interpreted ADMIT cannot widen any limit; an interpreted DENY does not block
otherwise-admissible requests. UNDETERMINED is never implicit approval.

## State ownership

Envelopes, deterministic request decisions, declared clauses and their bounded
interpretations. The contract owns no authority: it cannot delegate, allocate,
commit, encumber, or settle. Its output is admissibility information only.

## Expected errors

All rejections raise ValueError/`gl.vm.UserError` with `PolicyEnvelope:` prefix:
unknown ids, duplicates (envelope/clause/interpretation), malformed or oversized
inputs, inverted validity windows, reuse of an admitted request_id.

## Security assumptions

- Facts for interpretation are caller-supplied; no remote fetch in v0.1.
- No access control on create/expire in v0.1 — compose with Workflow Authorization
  before exposing to untrusted writers.
- The LLM surface is confined by schema validation + validator consensus on
  `decision`; it can never mutate accounting state directly.

## How to run tests

```bash
# deterministic hard-limit vectors
python tools/nomos_run_vectors.py primitives/policy-envelope/implementations/genlayer/policy_envelope.py --vectors primitives/policy-envelope/vectors/v0.1.json
# judgment-surface tests (mocked validator)
python -m pytest primitives/policy-envelope/implementations/genlayer/tests/ -v
```

## What remains unsupported

Actor/target registry enforcement, live policy-hash verification, deployment
receipts, and independent-partner convergence evidence do not exist yet.
