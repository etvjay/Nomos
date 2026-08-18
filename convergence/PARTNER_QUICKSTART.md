# Partner / Agent Quickstart

This is the minimum path for a new partner, coding agent, or external repository to reproduce and extend a Nomos primitive without prior conversation context.

## 1. Choose a primitive and commit

Pin the Nomos commit you are building against. Do not build against an unspecified moving branch when claiming convergence.

## 2. Read only the canonical contract first

For `claim-verification`, read:

```text
CONSTITUTION.md
CONVERGENCE.md
primitives/claim-verification/SPEC.md
primitives/claim-verification/INVARIANTS.md
primitives/claim-verification/THREAT_MODEL.md
primitives/claim-verification/DECISION_BOUNDARY.md
primitives/claim-verification/CAPABILITY.json
```

You should not need another contributor's chat history or private notes.

## 3. Fingerprint the semantic target

```bash
python tools/nomos_converge.py fingerprint claim-verification
```

Record this in your Work Contract. If another builder has a different fingerprint, you are not implementing the same semantic target yet.

## 4. Create a Work Contract

Copy:

```text
templates/WORK_CONTRACT.json
```

into:

```text
convergence/work/<work-id>.json
```

Pin:

- base commit;
- target primitive;
- allowed paths;
- authority fingerprint;
- capability version;
- dependencies;
- exact acceptance commands.

## 5. Implement independently

Implementation code may differ. Public semantics may not.

For deterministic primitives, canonical behavior converges under `EXACT` mode.

For judgment-bearing primitives, canonical behavior converges under `SEMANTIC` mode: the bounded financial decision relation must match even when model prose or internal execution differs.

## 6. Run local convergence gates

```bash
python tools/nomos_lint.py
python tools/nomos_converge.py check
```

Then run the primitive's `CAPABILITY.json.reproduce` commands.

For Claim Verification v0.1 this includes direct tests and GenVM lint.

## 7. Produce a Convergence Receipt

Copy:

```text
templates/CONVERGENCE_RECEIPT.json
```

Record only observed proof. `PASS` requires evidence. Missing runtime proof stays `NOT_IMPLEMENTED` or `BLOCKED`.

Verify the receipt against current canonical authority:

```bash
python tools/nomos_converge.py verify-receipt convergence/receipts/<receipt>.json
```

## 8. Build on top through CAPABILITY.json

Downstream applications and primitives should consume the public methods, statuses, errors, state ownership and composition information declared in `CAPABILITY.json` rather than undocumented implementation internals.

This makes the implementation replaceable while keeping the financial guarantee stable.

## 9. When you need to change the public surface

Do not silently modify it. Treat it as a `CAPABILITY` change:

1. version the capability;
2. record compatibility impact;
3. update vectors and downstream examples;
4. recompute the authority fingerprint;
5. issue a new Work Contract for downstream migration.

## Target property

A successful handoff should allow a new builder to answer, from repository artifacts alone:

```text
What primitive am I implementing?
What guarantees must remain true?
What can callers rely on?
What is intentionally unsupported?
How do I reproduce the proof?
What exact semantic version/fingerprint did I build against?
How do I extend it without breaking existing consumers?
```

If any of those require private agent memory, the handoff is incomplete.
