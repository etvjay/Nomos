# Claim Verification — GenLayer Implementation

Status: IMPLEMENTING
Version: 0.1.0

## Purpose

`claim_verification.py` is the first executable Nomos reference primitive. It turns caller-supplied financial claim evidence into one immutable, consensus-backed classification.

## Public API

### `verify_claim(...) -> str`

Inputs:

- `verification_id`: unique immutable verification record identifier.
- `claim_id`: stable identity of the underlying economic claim.
- `evidence_digest`: application-supplied digest binding the result to an exact evidence snapshot.
- `claim_json`: canonical claim payload as JSON object.
- `evidence_json`: evidence bundle as JSON object or array.

Canonical result fields:

```json
{
  "verification_id": "V1",
  "claim_id": "C123",
  "evidence_digest": "sha256:...",
  "status": "VERIFIED | CONFLICTED | INSUFFICIENT | UNDETERMINED",
  "reason_code": "EVIDENCE_SUPPORTS_CLAIM | MATERIAL_CONFLICT | MISSING_ESSENTIAL_EVIDENCE | EVIDENCE_AMBIGUOUS",
  "requested_by": "0x..."
}
```

### `get_verification(verification_id) -> str`
Returns the immutable canonical JSON decision or empty string when absent.

### `has_verification(verification_id) -> bool`
Checks whether a verification record exists.

## Consensus design

The Intelligent Contract uses `gl.nondet.exec_prompt(..., response_format="json")` inside `gl.vm.run_nondet_unsafe`.

Leader and validators independently classify the same claim/evidence bundle. Consensus compares only the canonical financial decision fields:

```text
status
reason_code
```

Free-form `analysis` is deliberately excluded from canonical storage and equivalence because wording may legitimately vary between validators.

## Deterministic preconditions

Before non-deterministic evaluation, the contract rejects:

- missing verification identity;
- missing claim identity;
- missing evidence digest;
- duplicate verification identity;
- malformed claim/evidence JSON;
- unsupported top-level JSON shapes;
- payloads over configured byte limits.

## Explicit non-goals

v0.1 does not:

- fetch remote evidence;
- verify the caller-supplied digest cryptographically;
- perform borrower credit scoring;
- rank financing opportunities;
- allocate authority or capital;
- reserve, encumber, or settle value.

Remote evidence adapters and provenance verification should compose around this primitive rather than being silently embedded into its first release.

## Run verification

```bash
pip install -r requirements-genlayer.txt

genvm-lint check primitives/claim-verification/implementations/genlayer/claim_verification.py
pytest primitives/claim-verification/implementations/genlayer/tests/ -v
```

## Definition of conformance

This implementation remains `IMPLEMENTING` until lint, direct tests, canonical vectors, adversarial/equivalence tests, integration tests and deployment evidence have produced receipts. Presence of executable code alone is not a conformance claim.
