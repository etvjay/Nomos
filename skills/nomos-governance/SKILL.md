# Nomos Governance Skill

Use this skill whenever creating, modifying, reviewing, porting, testing, documenting, or exposing a Nomos primitive.

## Objective

Preserve canonical economic semantics while allowing environment-specific implementation.

## Mandatory read order

1. `CONSTITUTION.md`
2. `GOVERNANCE.md`
3. `AGENTS.md`
4. `nomos.manifest.json`
5. target primitive `SPEC.md`, `INVARIANTS.md`, `THREAT_MODEL.md`, `DECISION_BOUNDARY.md`
6. target environment `PROFILE.md`
7. relevant Research Foundry and Experiment Foundry records

If any required mature-stage file is missing, stop the implementation claim and report `NOT_IMPLEMENTED` or return the primitive to the appropriate earlier lifecycle state.

## Procedure

### 1. Identify the semantic object

Write one sentence answering: what economic/coordination object or guarantee exists after this primitive acts?

Reject implementation-language definitions.

### 2. Identify boundaries

Explicitly separate:

`Evidence / Policy / Standing Authority / Allocation / Agreement / Encumbrance / Commitment / Replay Authority / Settlement / Rectification`.

Do not let the target primitive implicitly acquire another category's authority.

### 3. Classify every rule

Each rule is one of:

- `DETERMINISTIC_INVARIANT`
- `JUDGMENT_REQUIRED`
- `ENVIRONMENT_MECHANISM`
- `EXTERNAL_ASSUMPTION`
- `UNSUPPORTED`

If a rule can be deterministic without changing its meaning, keep it deterministic.

### 4. For judgment-bearing primitives

Specify:

- exact question;
- admissible evidence;
- deterministic preconditions;
- structured output;
- equivalence/consensus condition;
- `UNDETERMINED` behavior;
- deterministic postconditions;
- non-overridable invariants.

For GenLayer, use the official GenLayer skill/toolchain available in the working environment for contract authoring, GenVM linting, direct tests, integration tests, documentation verification and deployment/CLI checks. GenLayer is the reference judgment substrate, not the canonical definition of the primitive.

### 5. Research prior art

Use Research Foundry before claiming novelty. Separate semantic prior art from implementation machinery. Record standards as adapters or precedents unless they actually subsume the primitive.

### 6. Implement through an environment profile

Never code directly from the abstract idea. The path is:

`Canonical Spec → Environment Profile → Implementation`.

If an environment cannot preserve an invariant, mark it `UNSUPPORTED`.

### 7. Verify

Run in this order:

1. local/unit/property tests;
2. canonical conformance vectors;
3. environment integration tests;
4. adversarial tests;
5. Experiment Foundry benchmark where a research claim exists;
6. `python tools/nomos_lint.py`;
7. release receipt if making a release/capability claim.

### 8. Document reusable surfaces

Every reusable module must have adjacent usage documentation for frontend, SDK, agent, service or another primitive consumers. Never make consumers guess what exists.

### 9. Report exact status

Only report `PASS`, `FAIL`, `NOT_IMPLEMENTED`, or `BLOCKED` for evidence outcomes. Keep lifecycle status synchronized with `nomos.manifest.json`.

## Review rejection conditions

Reject a change if any of these are true:

- VM convenience changes primitive meaning;
- AI is used for deterministic accounting/replay/capacity without necessity;
- judgment directly executes unrestricted value movement;
- identity and evidence version are conflated;
- failure creates implicit authority;
- historical truth is rewritten for recovery;
- capability is exposed without implementation evidence;
- cross-environment conformance is achieved by weakening the canonical invariant;
- claimed standard compatibility has no adapter/test evidence;
- implementation lacks consumer-facing usage documentation for reusable modules.

## Completion statement

A valid completion report names:

- primitive/version;
- environment/profile;
- semantic/invariant changes (or `NONE`);
- tests and vectors run;
- adversarial result;
- known limitations;
- receipt/commit/deployment identifiers.
