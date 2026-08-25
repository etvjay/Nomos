# EXP-CONV-001 - Independent Primitive Reproduction

**Purpose:** Demonstrate that two independent builders (Partners B and C), given the
same canonical authority for a deterministic primitive, produce the same observable
economic state and reject the same invalid transitions.

**Primitive:** claim-encumbrance (deterministic, judgmentBearing=false, EXACT convergence).

**Authority pinned at base commit:** `17a4def`
- SPEC.md, INVARIANTS.md, THREAT_MODEL.md, DECISION_BOUNDARY.md
- CAPABILITY.json (capabilityVersion 0.1.0, convergenceMode EXACT)
- vectors/v0.1.json (canonical action vectors)
- authorityFingerprint: `sha256:7cfcbfeac1612804a635a1f9874a1584b62c2e21d542d6154497262ecd23ca10`

**Protocol**
1. Partner B and Partner C each receive the authority package ONLY (no other
   builder's implementation, no chat history).
2. Each independently produces implementations/genlayer/claim_encumbrance.py.
3. Both implementations are validated against the SAME canonical vectors via
   `tools/nomos_run_vectors.py`.
4. For each vector, observable state (equivalenceFields) must be byte-identical
   between B and C, and both must reject the same invalid transitions.

**Gates**
- `python tools/nomos_lint.py`
- `python tools/nomos_converge.py check`
- `python tools/nomos_run_vectors.py <impl>` - all vectors PASS for both lanes
- `genvm-lint check <impl>` - PASS for both lanes

**Result:** see convergence/receipts/WORK-CONV-001-B.json and WORK-CONV-001-C.json.