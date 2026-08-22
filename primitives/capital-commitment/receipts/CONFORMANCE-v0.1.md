# Capital Commitment v0.1 — Conformance Record

Status: CONFORMANT (claimed 2026-08-23)
Capability version: 0.1.0
Authority fingerprint: sha256:e327e8c0b74bd84d3535ede7d30f562b6b03f22864332ca16f7ae11cf3e0600b
Convergence mode: EXACT

## Conformance evidence

Per CONSTITUTION Article XI, applicable categories and their evidence:

| Category | Evidence | Result |
|---|---|---|
| Canonical state-transition vectors | `vectors/v0.1.json` (16 vectors) via `tools/nomos_run_vectors.py` | PASS 16/16 |
| Deterministic invariant tests | Vectors include backing-capacity limits, double-withdrawal prevention (active commitments cannot be reallocated), expiry/release restores capacity exactly once, duplicate-id rejection, unknown pool/asset rejection | PASS |
| Direct GenVM tests | Vector runner executes the contract in GenLayer direct mode (GenVM) | PASS |
| Independent-build convergence | EXP-CONV-003: lane B and lane C independently built from authority package only; all vectors byte-identical; RECEIPT-CONV-003-DIFF | PASS |
| Adversarial experiments | Overcommit, replay-by-id, expiry double-restore, cross-pool confusion covered as vector rejections | PASS (vector-scope) |
| Integration tests | NOT_IMPLEMENTED — no GLSim integration test for this primitive yet | NOT_IMPLEMENTED |
| Deployment/runtime evidence | NOT_IMPLEMENTED — no deployment receipt yet | NOT_IMPLEMENTED |

## Known limitations

- No live-network integration or deployment receipt; conformance is direct-mode + convergence based.
- genvm-lint gate not re-run in this session's reproduction.

## Reproduction

```bash
python tools/nomos_lint.py
python tools/nomos_converge.py check
python tools/nomos_run_vectors.py primitives/capital-commitment/implementations/genlayer/capital_commitment.py --vectors primitives/capital-commitment/vectors/v0.1.json
```
