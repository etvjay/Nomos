# Programmable Payment Account v0.1 - Conformance Record

Status: CONFORMANT (claimed 2026-10-11)
Capability version: 0.1.0
Authority fingerprint: sha256:24f00f6ecba7a3bbb0638c2eb46aee812b3a88471333b05a5099bd6e5f4e074a
Convergence mode: EXACT
Qualification: QUALIFIED_EXTENSION (composition product; re-qualified 2026-10-11; see PRIMITIVE_QUALIFICATION.md)

## Conformance evidence

Per CONSTITUTION Article XI, applicable categories and their evidence:

| Category | Evidence | Result |
|---|---|---|
| Canonical state-transition vectors | `vectors/v0.1.json` (15 vectors) via `tools/nomos_run_vectors.py` | PASS 15/15 |
| Deterministic invariant tests | DENY burns no id and moves no funds; non-DENIED terminal consumes id once (replay rejected); `available = balance - committed` gate; rolling 86400s daily window; fail-closed attestation gate with canonical denial vocabulary; fixed attestation schema rejects unknown fields (no PII) | PASS |
| Direct GenVM tests | Vector runner (direct mode); `tests/test_ppa_attestations.py` 13/13 direct (incl. provider-outage-as-absence, denied-id retryability, balance conservation across mixed outcomes) | PASS |
| Independent-build convergence | `convergence-lanes/ppa/your_build.py` (fresh-context subagent, spec+vectors only; reference implementation never read) 15/15; `convergence/receipts/RECEIPT-CONV-PPA-B.json` | PASS |
| Adversarial experiments | Payment-id replay, denied-id retry abuse, stale/expired/revoked attestations, subject substitution, unauthorized issuer, policy-version drift, schema loosening (PII), provider outage mistaken for approval — vector + direct coverage | PASS (vector/direct-scope) |
| Integration tests | GLSim consensus path: `gltest tests/test_ppa_flows.py` 6/6 (settle, per-tx deny+retry, allowlist deny, insufficient commitment, invoice cycle, dispute refund) and `gltest tests/test_ppa_attestations.py` 13/13 | PASS |
| Deployment/runtime evidence | `convergence/deployment/ppa-bradbury.json` + live-verified `create→deposit→send→settle` on Bradbury (chain 4221) | PASS (record) |

## Known limitations

- v0.1 embeds composed primitive semantics in-account; cross-contract extraction (calling deployed primitives directly) is the v0.2 step.
- Delegation paths exist in the contract but are not exercised by v0.1 canonical vectors (documented in the convergence lane report).
- Attestations are owner-registered technical compliance evidence only — NOT legal KYC/AML.
- `JUDGMENT_BOUNDARY = NONE` for every money path.

## Reproduction

```bash
python3 tools/nomos_lint.py
python3 tools/nomos_converge.py check
python3 tools/nomos_run_vectors.py primitives/ppa/implementations/genlayer/ppa.py --vectors primitives/ppa/vectors/v0.1.json
python3 -m pytest primitives/ppa/implementations/genlayer/tests/test_ppa_attestations.py -v
python3 convergence-lanes/ppa/your_build.py primitives/ppa/vectors/v0.1.json
gltest primitives/ppa/implementations/genlayer/tests/test_ppa_flows.py -q
genvm-lint check primitives/ppa/implementations/genlayer/ppa.py
```