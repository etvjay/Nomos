# EXP-CONV-004 — Claim Verification SEMANTIC Convergence (Partner A vs Partner B)

Primitive: claim-verification v0.1.0
Convergence mode: SEMANTIC
Authority fingerprint: sha256:f0be8bab680a32698c1dbf36971ce10802911af0451f4216de84f92fddf587f2

## Question

Does an independently written GenLayer implementation of claim-verification v0.1,
produced from the repository contract alone, converge with Partner A's build inside
the bounded decision relation declared by `CAPABILITY.json`?

## Lanes

- **Lane A** (canonical): `primitives/claim-verification/implementations/genlayer/claim_verification.py`
  — recorded in RECEIPT-CONV-001-A (direct 13/13, integration 1/1).
- **Lane B** (independent): `convergence/experiments/EXP-CONV-004/lane-b/claim_verification_b.py`
  — different storage field name (`verdicts`), different validation order, different
  prompt phrasing, different internal helper structure; same deterministic
  preconditions, size limits, status/reason vocabulary, mandatory pairing, and
  equivalence rule (consensus binds {status, reason_code} only).

## Method

1. Replay all 4 canonical vectors against Lane B in direct mode with mocked
   deterministic validator output per vector expectation.
2. Assert equivalence fields {status, reason_code} match the canonical expectations.
3. Exercise adversarial surface: duplicate id rejection, malformed JSON rejected
   before LLM work, status/reason mismatch not accepted, UNDETERMINED is distinct
   from VERIFIED, decision binds claim_id + evidence_digest.
4. Integration: Lane A verified under real consensus on GLSim localnet
   (sim_installMocks) — see RECEIPT-CONV-001-A.

## Result

PASS. Lane B converged with Lane A on all canonical vectors and adversarial
assertions: 9/9 direct tests passed
(`python -m pytest convergence/experiments/EXP-CONV-004/ -v`).

## Evidence

- `convergence/experiments/EXP-CONV-004/lane-b/` — independent build + tests
- `convergence/receipts/RECEIPT-CONV-004-B.json`

## Known gaps

- Validator LLM mocked deterministically; no live provider key in either lane.
- genvm-lint not run on Lane B file.
