#!/usr/bin/env python3
"""EXACT convergence differential check.

Deploys two independent implementations of a deterministic primitive and
replays identical canonical action sequences against both. For every vector
and every action, the observable economic state must be byte-identical
between the two implementations, and both must reject the same transitions.

Probing is data-driven per primitive: the vectors file may declare a
"probes" section listing single-record views (keyed by one id) and aggregate
views (keyed by a tuple of ids) to collect for every key that appears in the
actions. Without a probes section, claim-encumbrance defaults are used.

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

CE_DEFAULT_PROBES = {
    "single": {
        "op": "get_encumbrance",
        "sources": {"reserve": [0], "get_encumbrance": [0]},
    },
    "aggregates": [
        {
            "op": "financeable_amount",
            "sources": {"set_financeable_amount": [0], "reserve": [1]},
        },
        {
            "op": "active_encumbrances",
            "sources": {"set_financeable_amount": [0], "reserve": [1]},
        },
    ],
}


def _probes_for(vectors: dict) -> dict:
    return vectors.get("probes", CE_DEFAULT_PROBES)


def _collect_keys(actions: list[dict], spec: dict) -> list[tuple]:
    """Collect unique keys (id or id-tuple) from the actions for a probe."""
    keys: set[tuple] = set()
    for action in actions:
        op = action["op"]
        args = action.get("args", [])
        if op in spec["sources"]:
            idxs = spec["sources"][op]
            if all(i < len(args) for i in idxs):
                key = tuple(args[i] for i in idxs)
                if all(key):
                    keys.add(key)
    return sorted(keys)


def _run_vector(vm, contract, vector: dict) -> dict:
    outcomes = []
    for action in vector.get("actions", []):
        op = action["op"]
        args = action.get("args", [])
        try:
            result = getattr(contract, op)(*args)
            outcome = {"rejected": False, "result": result}
        except Exception as exc:
            outcome = {"rejected": True, "error": str(exc)}
        outcomes.append(outcome)
    return {"outcomes": outcomes}


def _collect_state(vm, contract, vector: dict, probes: dict) -> dict:
    """Run the vector and capture full observable state per probe config."""
    actions = vector.get("actions", [])
    state = {"outcomes": []}
    state["outcomes"] = _run_vector(vm, contract, vector)["outcomes"]

    if "single" in probes:
        spec = probes["single"]
        op = spec["op"]
        state["single"] = {}
        for key in _collect_keys(actions, spec):
            state["single"][key[0]] = getattr(contract, op)(*key)

    for agg in probes.get("aggregates", []):
        op = agg["op"]
        if op not in state:
            state[op] = {}
        for key in _collect_keys(actions, agg):
            state[op][key] = getattr(contract, op)(*key)
    return state


def _compare_state(a: dict, b: dict, vid: str, probes: dict) -> list[str]:
    failures = []
    for i, (oa, ob) in enumerate(zip(a["outcomes"], b["outcomes"])):
        if oa["rejected"] != ob["rejected"]:
            failures.append(f"{vid}#{i}: rejection differs A={oa['rejected']} B={ob['rejected']}")
            continue
        if not oa["rejected"] and oa["result"] != ob["result"]:
            failures.append(
                f"{vid}#{i}: result differs\n  A={oa['result']!r}\n  B={ob['result']!r}"
            )
    if "single" in probes and a.get("single") != b.get("single"):
        failures.append(f"{vid}: single-record state differs\n  A={a.get('single')}\n  B={b.get('single')}")
    for agg in probes.get("aggregates", []):
        op = agg["op"]
        if a.get(op) != b.get(op):
            failures.append(f"{vid}: {op} state differs\n  A={a.get(op)}\n  B={b.get(op)}")
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
    probes = _probes_for(vectors)
    failures = []
    passed = 0

    for vector in vector_list:
        vid = vector.get("id", "?")
        vm_a = VMContext()
        vm_a.sender = create_address("alice")
        with vm_a.activate():
            contract_a = deploy_contract(ca, vm_a)
            state_a = _collect_state(vm_a, contract_a, vector, probes)
        vm_b = VMContext()
        vm_b.sender = create_address("alice")
        with vm_b.activate():
            contract_b = deploy_contract(cb, vm_b)
            state_b = _collect_state(vm_b, contract_b, vector, probes)
        diffs = _compare_state(state_a, state_b, vid, probes)
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
