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


SUPPORTED_ACTION_KEY = "actions"
# Historical/alternative keys seen in the wild. Named explicitly so the error
# can say what to do instead of failing opaquely.
MISNAMED_KEYS = {"steps": "executable action sequence"}


def _coerce(value: object) -> str:
    return value if isinstance(value, str) else json.dumps(value)


def _schema_failures(vector: dict) -> list[str]:
    """Refuse any vector the runner cannot actually execute.

    A vector with no executable sequence used to iterate zero times, produce
    zero failures, and be reported PASS. That made an unexecuted vector
    indistinguishable from a passing one, which invalidates the evidence layer
    for every primitive that relies on this runner. See
    WORK-VECTOR-RUNNER-HARDEN-2026-10-17.
    """
    vid = vector.get("id", "<no id>")
    failures = []
    if not isinstance(vector, dict):
        return [f"{vid}: vector is not an object"]

    seq = vector.get(SUPPORTED_ACTION_KEY)
    if seq is None:
        declared = sorted(k for k in vector.keys() if k not in ("id", "description"))
        for key, meaning in MISNAMED_KEYS.items():
            if key in vector:
                failures.append(
                    f"{vid}: unsupported vector key '{key}' ({meaning}); "
                    f"this runner executes '{SUPPORTED_ACTION_KEY}' only — "
                    f"migrate '{key}' to '{SUPPORTED_ACTION_KEY}' or record the "
                    f"corpus as not executable by this runner"
                )
                return failures
        failures.append(
            f"{vid}: no '{SUPPORTED_ACTION_KEY}' key — nothing to execute. "
            f"Declared keys: {declared or ['<none>']}. "
            f"A vector without an executable sequence cannot be reported PASS."
        )
        return failures

    if not isinstance(seq, list):
        failures.append(f"{vid}: '{SUPPORTED_ACTION_KEY}' must be a list, got {type(seq).__name__}")
        return failures
    if not seq:
        failures.append(f"{vid}: '{SUPPORTED_ACTION_KEY}' is empty — an empty executable sequence cannot be reported PASS")
        return failures
    for i, action in enumerate(seq):
        if not isinstance(action, dict) or "op" not in action:
            failures.append(f"{vid}#{i}: action is missing 'op'")
    return failures


def _run_vector(vm, contract, vector: dict) -> list[str]:
    failures: list[str] = _schema_failures(vector)
    if failures:
        return failures
    for i, action in enumerate(vector[SUPPORTED_ACTION_KEY]):
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