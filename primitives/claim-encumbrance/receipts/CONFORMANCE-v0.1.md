# Claim Encumbrance v0.1 - Conformance Record

Status: CONFORMANT (claimed 2026-08-23)
Capability version: 0.1.0
Authority fingerprint: sha256:7cfcbfeac1612804a635a1f9874a1584b62c2e21d542d6154497262ecd23ca10
Convergence mode: EXACT

## Conformance evidence

Per CONSTITUTION Article XI, applicable categories and their evidence:

| Category | Evidence | Result |
|---|---|---|
| Canonical state-transition vectors | `vectors/v0.1.json` (16 vectors) via `tools/nomos_run_vectors.py` | PASS 16/16 |
| Deterministic invariant tests | Vectors include capacity overcommit rejection, duplicate-id rejection, immutable financeable amount, capacity restoration after release/settle, unknown-claim rejection | PASS |
| Direct GenVM tests | Vector runner executes the contract in GenLayer direct mode (GenVM) | PASS |
| Independent-build convergence | EXP-CONV-001: lane B vs canonical, byte-identical observable state on all vectors; RECEIPT-CONV-001-DIFF | PASS |
| Adversarial experiments | Replay (duplicate reservation id), stale/unknown claim references, concurrent overcommit attempts, partial-execution impossibility - covered as vector rejections | PASS (vector-scope) |
| Integration tests | NOT_IMPLEMENTED - no GLSim integration test for this primitive yet | NOT_IMPLEMENTED |
| Deployment/runtime evidence | NOT_IMPLEMENTED - no deployment receipt yet | NOT_IMPLEMENTED |

## Known limitations

- No live-network integration or deployment receipt; conformance is direct-mode + convergence based.
- genvm-lint gate not re-run in this session's reproduction.

## Reproduction

```bash
python tools/nomos_lint.py
python tools/nomos_converge.py check
python tools/nomos_run_vectors.py primitives/claim-encumbrance/implementations/genlayer/claim_encumbrance.py --vectors primitives/claim-encumbrance/vectors/v0.1.json
```
