# EXP-CONV-003 - Independent Primitive Reproduction (Capital Commitment)

**Purpose:** Demonstrate that two independent builders (Partners B and C), given the
same canonical authority for a second deterministic primitive, produce the same
observable economic state and reject the same invalid transitions.

**Primitive:** capital-commitment (deterministic, judgmentBearing=false, EXACT convergence).

**Authority pinned at base commit:** `55d9eed0`
- SPEC.md, INVARIANTS.md, THREAT_MODEL.md, DECISION_BOUNDARY.md
- CAPABILITY.json (capabilityVersion 0.1.0, convergenceMode EXACT)
- vectors/v0.1.json (canonical action vectors)
- authorityFingerprint: `sha256:e327e8c0b74bd84d3535ede7d30f562b6b03f22864332ca16f7ae11cf3e0600b`

**Protocol**
1. Partner B and Partner C each receive the authority package ONLY (no other
   builder's implementation, no chat history).
2. Each independently produces implementations/genlayer/capital_commitment.py.
3. Both implementations are validated against the SAME canonical vectors via
   `tools/nomos_run_vectors.py`.
4. For each vector, observable state (equivalenceFields) must be byte-identical
   between B and C, and both must reject the same invalid transitions.

**Gates**
- `python tools/nomos_lint.py`
- `python tools/nomos_converge.py check`
- `python tools/nomos_run_vectors.py <impl> --vectors <cc vectors>` - all vectors PASS for both lanes
- `genvm-lint check <impl>` - PASS for both lanes

**Result:** see convergence/receipts/WORK-CONV-003-B.json and WORK-CONV-003-C.json.
