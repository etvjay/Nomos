# GenLayer integration boundary

This package defines the boundary between GenLayer Intelligent Contract
adjudication and Nomos account consequences. It is part of the Intelligent
Account composition; it is not a new financial primitive.

## Contract

GenLayer performs the judgment-bearing operation through an Intelligent
Contract and validator acceptance under its declared Equivalence Principle.
The resulting receipt is a structured record, not free-form model output.

The receipt must bind:

- `decision_id`;
- source contract;
- question and evidence hashes;
- `ACCEPTED`, `REJECTED`, or `UNDETERMINED` status;
- equivalence/validation mode;
- policy version;
- creation and expiry times.

Nomos then performs deterministic checks before a receipt can create an
Intelligent Account proposal. Only `ACCEPTED` can become actionable. A
`REJECTED` or `UNDETERMINED` decision is recorded but cannot authorize a
financial state change. Expired, malformed, mismatched, or replayed receipts
fail closed.

## Account path

```text
GenLayer web/LLM operation
  -> validator evaluation / Equivalence Principle
  -> adjudication receipt
  -> receipt binding and expiry checks
  -> Intelligent Account proposal
  -> authority, policy, capital, replay, and claim gates
  -> settlement, denial, or rectification
```

Human and autonomous proposals use the same financial gates. Autonomy changes
who triggers proposal execution, not the authority available to the action.

## Primitive roles

The judgment-bearing boundary belongs to Claim Verification and the
Intelligent Account judgment interface. Proof of Payable, Policy Envelope,
Capital Commitment, Claim Encumbrance, authority allocation, authorization
lanes, Workflow Authorization, Gaia, and deterministic Financial Contract
transitions consume accepted bounded results or execute deterministic state
transitions. They do not add unnecessary LLM judgment.

## Evidence boundary

A receipt proves that a structured GenLayer decision was accepted under the
runtime's consensus path. It does not prove that an external source was true,
that an issuer is legally compliant, or that a downstream token transfer
occurred. Those require separate evidence.

## Local verification

```bash
python -m pytest ias/tests/test_genlayer_integration.py -q
```

The module is a deterministic validation helper. It does not claim live
GenLayer consensus by itself; live consensus evidence remains in the
GenLayer/Bradbury receipts and integration tests.
