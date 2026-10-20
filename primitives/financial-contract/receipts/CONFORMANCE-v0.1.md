# Financial Contract v0.1 - Conformance Record

Status: CONFORMANT (claimed 2026-10-11)
Capability version: 0.1.0
Authority fingerprint: sha256:7272b49f9d8c050eefe412de60a65875209833c69e24f45dd0682f014d3fef64
Convergence mode: EXACT
Qualification: QUALIFIED (re-qualified 2026-10-11 on the narrowed obligation/cash-flow scope; see PRIMITIVE_QUALIFICATION.md)

## Conformance evidence

Per CONSTITUTION Article XI, applicable categories and their evidence:

| Category | Evidence | Result |
|---|---|---|
| Canonical state-transition vectors | `vectors/v0.1.json` (9 vectors) via `tools/nomos_run_vectors.py` | PASS 9/9 |
| Deterministic invariant tests | Conservation `outstanding = principal - total_paid`; overpayment denied not clipped; denied payments consume no id; duplicate contract/payment ids rejected; CLOSED/DEFAULTED terminal; append-only payment records | PASS |
| Direct GenVM tests | Vector runner executes the contract in GenLayer direct mode; `tests/test_fc_authority.py` 3/3 (creditor-only default, non-creditor rejected, pre-maturity rejected) | PASS |
| Independent-build convergence | `convergence-lanes/financial-contract/your_build.py` (fresh-context, spec+vectors only) 9/9; `convergence/receipts/RECEIPT-CONV-FC-B.json` | PASS |
| Adversarial experiments | Replay (duplicate payment id), overcommit/overpayment, terminal-state mutation, unauthorized default declaration, id-burn-on-deny — covered as vector rejections + direct authority tests | PASS (vector-scope) |
| Integration tests | GLSim consensus path: `tests/integration/test_live_transactions.py::test_financial_contract_live_payment_cycle` (open → pay 400 → overpay DENY → pay off → CLOSED) | PASS |
| Deployment/runtime evidence | `convergence/deployment/financial_contract-bradbury.json` (testnet deployment record) | PASS (record) |

## Known limitations

- Interest accrual, contingent clauses, covenants, restructuring remain deferred to future capability versions with declared judgment boundaries.
- Maturity timestamp gates default declaration, not payment application (documented interpretation, `convergence-lanes/financial-contract/BUILD_REPORT.md`).
- genvm-lint re-run in this session: PASS (5 methods).

## Reproduction

```bash
python3 tools/nomos_lint.py
python3 tools/nomos_converge.py check
python3 tools/nomos_run_vectors.py primitives/financial-contract/implementations/genlayer/financial_contract.py --vectors primitives/financial-contract/vectors/v0.1.json
python3 -m pytest primitives/financial-contract/implementations/genlayer/tests/ -v
python3 convergence-lanes/financial-contract/your_build.py primitives/financial-contract/vectors/v0.1.json
gltest primitives/financial-contract/implementations/genlayer/tests/integration/test_live_transactions.py -q
genvm-lint check primitives/financial-contract/implementations/genlayer/financial_contract.py
```