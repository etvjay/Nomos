#!/usr/bin/env python3
"""Nomos canonical vector runner.

Deploys a GenLayer implementation in direct mode and replays a primitive's
canonical vectors against it, asserting each action's expected outcome and
the resulting observable state.

Usage:
    python tools/nomos_run_vectors.py <contract.py> [--vectors <vectors.json>]

Exit code 0 means every vector passed; 1 means at least one failed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from gltest.direct.vm import VMContext
    from gltest.direct.loader import deploy_contract, create_address
except ImportError as exc:  # pragma: no cover
    print(f"missing gltest dependency: {exc}")
    sys.exit(2)


def _coerce(value: object) -> str:
    return value if isinstance(value, str) else json.dumps(value)


def _run_vector(vm, contract, vector: dict) -> list[str]:
    failures: list[str] = []
    for i, action in enumerate(vector.get("actions", [])):
        op = action["op"]
        args = action.get("args", [])
        expect = action.get("expect")
        step = f"{vector.get('id')}#{i} {op}({', '.join(args)})"

        if expect == "ok":
            try:
                getattr(contract, op)(*args)
            except Exception as exc:
                failures.append(f"{step}: expected ok, raised {type(exc).__name__}: {exc}")
            continue

        if expect == "reject":
            try:
                getattr(contract, op)(*args)
                failures.append(f"{step}: expected reject, but call succeeded")
            except Exception:
                pass
            continue

        try:
            result = getattr(contract, op)(*args)
        except Exception as exc:
            failures.append(f"{step}: view raised {type(exc).__name__}: {exc}")
            continue

        if isinstance(expect, dict):
            try:
                parsed = json.loads(result) if isinstance(result, str) else dict(result)
            except Exception:
                failures.append(f"{step}: expected object, got unparseable {result!r}")
                continue
            mismatches = []
            for key, val in expect.items():
                if _coerce(parsed.get(key)) != _coerce(val):
                    mismatches.append(f"{key}={_coerce(parsed.get(key))}!={_coerce(val)}")
            if mismatches:
                failures.append(f"{step}: {', '.join(mismatches)}")
            continue

        if _coerce(result) != _coerce(expect):
            failures.append(f"{step}: expected {_coerce(expect)!r}, got {_coerce(result)!r}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("contract", help="path to the GenLayer implementation .py")
    parser.add_argument(
        "--vectors",
        default="primitives/claim-encumbrance/vectors/v0.1.json",
        help="path to canonical vectors JSON",
    )
    parser.add_argument("--base", default=".", help="repo root for relative paths")
    args = parser.parse_args()

    base = Path(args.base).resolve()
    contract_path = Path(args.contract)
    if not contract_path.is_absolute():
        contract_path = base / contract_path
    vectors_path = Path(args.vectors)
    if not vectors_path.is_absolute():
        vectors_path = base / vectors_path

    if not contract_path.exists():
        print(f"contract not found: {contract_path}")
        return 2
    if not vectors_path.exists():
        print(f"vectors not found: {vectors_path}")
        return 2

    vectors = json.loads(vectors_path.read_text())
    primitive = vectors.get("primitive", "unknown")
    vector_list = vectors.get("vectors", [])
    if not vector_list:
        print(f"{primitive}: no vectors in {vectors_path}")
        return 2

    passed = 0
    total_failures: list[str] = []
    for vector in vector_list:
        vm = VMContext()
        vm.sender = create_address("alice")
        with vm.activate():
            contract = deploy_contract(contract_path, vm)
            failures = _run_vector(vm, contract, vector)
        vid = vector.get("id", "?")
        if failures:
            print(f"FAIL {primitive}/{vid}")
            for f in failures:
                print(f"     {f}")
            total_failures.extend(failures)
        else:
            passed += 1
            print(f"PASS {primitive}/{vid}")

    print(f"\n{passed}/{len(vector_list)} vectors passed for {primitive}")
    if total_failures:
        print(f"{len(total_failures)} assertion failures")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())