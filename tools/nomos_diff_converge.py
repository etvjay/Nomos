#!/usr/bin/env python3
"""EXACT convergence differential check for EXP-CONV-001.

Deploys two independent implementations of a deterministic primitive and
replays identical canonical action sequences against both. For every vector
and every action, the observable economic state (get_encumbrance for all
reservation ids, active_encumbrances and financeable_amount for all claim ids)
must be byte-identical between the two implementations, and both must reject
the same transitions.

Usage:
    python tools/nomos_diff_converge.py <contractA.py> <contractB.py> [--vectors <vectors.json>] [--base <root>]

Exit 0 = EXACT convergence confirmed for all vectors.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from gltest.direct.vm import VMContext
from gltest.direct.loader import deploy_contract, create_address


def _collect_state(vm, contract, vector: dict) -> dict:
    """Run the vector against one contract and capture full observable state."""
    reservation_ids = set()
    claim_ids = set()
    outcomes = []
    for action in vector.get("actions", []):
        op = action["op"]
        args = action.get("args", [])
        expect = action.get("expect")
        for arg in args:
            if op in ("reserve",) and args.index(arg) == 0:
                reservation_ids.add(arg)
            elif op == "get_encumbrance":
                reservation_ids.add(args[0])
        if op == "set_financeable_amount":
            claim_ids.add(args[0])
        if op == "reserve":
            claim_ids.add(args[1])
        try:
            result = getattr(contract, op)(*args)
            outcome = {"rejected": False, "result": result}
        except Exception as exc:
            outcome = {"rejected": True, "error": str(exc)}
        outcomes.append(outcome)

    state = {"outcomes": outcomes, "reservations": {}, "claims": {}}
    for rid in sorted(reservation_ids):
        if rid:
            state["reservations"][rid] = contract.get_encumbrance(rid)
    for cid in sorted(claim_ids):
        if cid:
            state["claims"][cid] = {
                "financeable": contract.financeable_amount(cid),
                "active": contract.active_encumbrances(cid),
            }
    return state


def _compare_state(a: dict, b: dict, vid: str) -> list[str]:
    failures = []
    for i, (oa, ob) in enumerate(zip(a["outcomes"], b["outcomes"])):
        if oa["rejected"] != ob["rejected"]:
            failures.append(f"{vid}#{i}: rejection differs A={oa['rejected']} B={ob['rejected']}")
            continue
        if not oa["rejected"] and oa["result"] != ob["result"]:
            failures.append(
                f"{vid}#{i}: result differs\n  A={oa['result']!r}\n  B={ob['result']!r}"
            )
    if a["reservations"] != b["reservations"]:
        failures.append(f"{vid}: reservation state differs\n  A={a['reservations']}\n  B={b['reservations']}")
    if a["claims"] != b["claims"]:
        failures.append(f"{vid}: claim state differs\n  A={a['claims']}\n  B={b['claims']}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("contract_a")
    parser.add_argument("contract_b")
    parser.add_argument("--vectors", default="primitives/claim-encumbrance/vectors/v0.1.json")
    parser.add_argument("--base", default=".")
    args = parser.parse_args()

    base = Path(args.base).resolve()
    ca = Path(args.contract_a)
    cb = Path(args.contract_b)
    ca = ca if ca.is_absolute() else base / ca
    cb = cb if cb.is_absolute() else base / cb
    vp = Path(args.vectors)
    vp = vp if vp.is_absolute() else base / vp

    vectors = json.loads(vp.read_text())
    vector_list = vectors.get("vectors", [])
    failures = []
    passed = 0

    for vector in vector_list:
        vid = vector.get("id", "?")
        vm_a = VMContext()
        vm_a.sender = create_address("alice")
        with vm_a.activate():
            contract_a = deploy_contract(ca, vm_a)
            state_a = _collect_state(vm_a, contract_a, vector)
        vm_b = VMContext()
        vm_b.sender = create_address("alice")
        with vm_b.activate():
            contract_b = deploy_contract(cb, vm_b)
            state_b = _collect_state(vm_b, contract_b, vector)
        diffs = _compare_state(state_a, state_b, vid)
        if diffs:
            failures.extend(diffs)
            print(f"DIFF {vid}")
            for d in diffs:
                print(f"     {d}")
        else:
            passed += 1
            print(f"EXACT {vid}")

    print(f"\n{passed}/{len(vector_list)} vectors EXACT-convergent")
    if failures:
        print(f"{len(failures)} differential failures")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())