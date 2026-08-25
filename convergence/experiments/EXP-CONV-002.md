# EXP-CONV-002 - Blind Downstream Composition

**Purpose:** Demonstrate that a downstream builder (Partner D) can compose a tiny
application from canonical CAPABILITYs alone, without access to implementation
internals, and that the composed behavior is coherent with the upstream contracts.

**Inputs to Partner D:**
- claim-verification CAPABILITY.json (SEMANTIC)
- claim-encumbrance CAPABILITY.json (EXACT)
- canonical types + SDK helpers
- composition documentation (CONVERGENCE.md / PARTNER_QUICKSTART.md)

**App:** Verified receivable -> Claim Verification -> if VERIFIED -> Claim
Encumbrance.reserve(...) -> financeable balance changes.

**Gates**
- `python tools/nomos_lint.py`
- `python tools/nomos_converge.py check`
- `pytest examples/verified-receivable/tests/ -v`

**Result:** see convergence/receipts/WORK-CONV-001-D.json.