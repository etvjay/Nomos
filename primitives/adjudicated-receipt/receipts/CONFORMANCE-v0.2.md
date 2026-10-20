# Adjudicated Receipt v0.2 - Conformance Record

Status: CONFORMANT (claimed 2026-10-11)
Capability version: 0.2.0
Authority fingerprint: sha256:bb7d15c8f2f8cae5d80b4643608e6eb24a01898700bd63c6c55f94315b4cffa4
Convergence mode: SEMANTIC
Qualification: QUALIFIED (re-qualified 2026-10-11; see PRIMITIVE_QUALIFICATION.md)

## Conformance evidence

Per CONSTITUTION Article XI, applicable categories and their evidence:

| Category | Evidence | Result |
|---|---|---|
| Canonical state-transition vectors | `vectors/v0.2.json` (5 deterministic-envelope vectors) via `tools/nomos_run_vectors.py` | PASS 5/5 |
| Deterministic invariant tests | Immutable obligation terms + derived obligation hash; https-only evidence pointer; positive value/TTL/window; unique object/receipt ids; CANCELLED terminal; unknown-receipt guards fail closed | PASS |
| Direct GenVM tests | `tests/test_adjudicated_receipt.py` 13/13 direct (mocked web/LLM): full provisional→challenge→dismiss/finalize→settle-once lifecycle, upheld-challenge terminal non-acceptance, TTL expiry, non-ACCEPTED never settles, out-of-schema model output → UNDETERMINED, partial/low-confidence cannot advance, keeper-authority separation | PASS |
| Independent-build convergence | `convergence-lanes/adjudicated-receipt/your_build.py` (fresh-context subagent, spec+vectors only; reference implementation never read) 5/5 on the deterministic envelope; `convergence/receipts/RECEIPT-CONV-AR-B.json` | PASS |
| Adversarial experiments | Evidence substitution (obligation-hash binding), stale-evidence TTL, receipt replay/consumption, schema evasion, low-confidence acceptance pressure, challenge-window bypass, non-owner settle — direct mocked suite | PASS (direct-scope) |
| Integration tests | GLSim consensus path: `gltest tests/integration/test_adjudicated_integration.py` — real leader+validator quorum: adjudicate→PROVISIONAL_ACCEPTED, pre-window settle fails, challenge freeze, owner dismissal, REJECTED terminal, UNDETERMINED recorded, cancel | PASS |
| Integration tests (clock-gated) | Post-window `finalize_release`→FINAL_ACCEPTED and settle-once on GLSim | BLOCKED — this GLSim build freezes the genvm datetime at sim-start for all paths (plain writes, views, sim_setTime global offset, per-tx genvm_datetime; probe documented in the integration test). The same lifecycle is proven in direct mode (13/13) where the clock can be warped. |
| Deployment/runtime evidence | No testnet deployment receipt for this primitive yet | NOT_IMPLEMENTED |

## Known limitations

- Token rails: settlement records a release obligation, it does not transfer tokens.
- Cross-contract receipt consumption and per-object non-owner settler bindings are unsupported in v0.2.
- Bond escrow/slashing: bonds are recorded commitments only.
- SEMANTIC convergence covers the bounded decision relation `(satisfied, verdict, confidence)` + envelope; the obligation-hash *formula* is binding-semantics, not byte-formula (lane report documents its internal choice).

## Reproduction

```bash
python3 tools/nomos_lint.py
python3 tools/nomos_converge.py check
python3 tools/nomos_run_vectors.py primitives/adjudicated-receipt/implementations/genlayer/adjudicated_receipt.py --vectors primitives/adjudicated-receipt/vectors/v0.2.json
python3 -m pytest primitives/adjudicated-receipt/implementations/genlayer/tests/ -v
python3 convergence-lanes/adjudicated-receipt/your_build.py primitives/adjudicated-receipt/vectors/v0.2.json
gltest primitives/adjudicated-receipt/implementations/genlayer/tests/integration/ -q
genvm-lint check primitives/adjudicated-receipt/implementations/genlayer/adjudicated_receipt.py
```