# Capital Commitment - GenLayer Implementation

Canonical deterministic implementation of the Capital Commitment primitive
(capabilityVersion 0.1.0, convergenceMode EXACT).

Status: SPECIFIED. Implementations were independently reproduced by Partners
B and C in EXP-CONV-003 and are byte-identical in observable economic state
(16/16 vectors EXACT-convergent).

Run canonical vectors:

    python tools/nomos_run_vectors.py primitives/capital-commitment/implementations/genlayer/capital_commitment.py --vectors primitives/capital-commitment/vectors/v0.1.json

Lint:

    genvm-lint check primitives/capital-commitment/implementations/genlayer/capital_commitment.py
