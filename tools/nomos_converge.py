#!/usr/bin/env python3
"""Nomos repository-mediated convergence checks.

Commands:
  check
  fingerprint <primitive-id>
  verify-receipt <path>
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "nomos.manifest.json"
ALLOWED_EVIDENCE = {"PASS", "FAIL", "NOT_IMPLEMENTED", "BLOCKED"}
ALLOWED_CONVERGENCE = {"EXACT", "SEMANTIC"}


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def _primitive(pid: str) -> dict:
    for item in _manifest().get("primitives", []):
        if item.get("id") == pid:
            return item
    raise SystemExit(f"unknown primitive: {pid}")


def _authority_files(pid: str) -> list[Path]:
    primitive = _primitive(pid)
    base = ROOT / primitive["canonicalPath"]
    files: list[Path] = []
    for name in ["SPEC.md", "INVARIANTS.md", "THREAT_MODEL.md", "DECISION_BOUNDARY.md", "CAPABILITY.json"]:
        path = base / name
        if path.exists():
            files.append(path)
    vectors = base / "vectors"
    if vectors.exists():
        files.extend(sorted(p for p in vectors.rglob("*") if p.is_file()))
    return sorted(files, key=lambda p: p.relative_to(ROOT).as_posix())


def fingerprint(pid: str) -> str:
    h = hashlib.sha256()
    files = _authority_files(pid)
    if not files:
        raise SystemExit(f"{pid}: no authority files found")
    for path in files:
        rel = path.relative_to(ROOT).as_posix().encode()
        data = path.read_bytes()
        h.update(len(rel).to_bytes(4, "big"))
        h.update(rel)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return f"sha256:{h.hexdigest()}"


def check() -> int:
    errors: list[str] = []
    required_root = [
        ROOT / "CONVERGENCE.md",
        ROOT / "templates" / "WORK_CONTRACT.json",
        ROOT / "templates" / "CONVERGENCE_RECEIPT.json",
    ]
    for path in required_root:
        if not path.exists():
            errors.append(f"missing convergence artifact: {path.relative_to(ROOT)}")

    manifest = _manifest()
    for primitive in manifest.get("primitives", []):
        pid = primitive.get("id")
        status = primitive.get("status")
        canonical = primitive.get("canonicalPath")
        if not pid or not canonical:
            continue
        base = ROOT / canonical
        cap_path = base / "CAPABILITY.json"

        if status in {"IMPLEMENTING", "CONFORMANT", "RELEASED"} and not cap_path.exists():
            errors.append(f"{pid}: {status} requires CAPABILITY.json")
            continue

        if cap_path.exists():
            try:
                cap = json.loads(cap_path.read_text())
            except Exception as exc:
                errors.append(f"{pid}: invalid CAPABILITY.json: {exc}")
                continue

            if cap.get("primitiveId") != pid:
                errors.append(f"{pid}: CAPABILITY primitiveId mismatch")
            if cap.get("status") != status:
                errors.append(f"{pid}: CAPABILITY status {cap.get('status')!r} != manifest status {status!r}")
            mode = cap.get("convergenceMode")
            if mode not in ALLOWED_CONVERGENCE:
                errors.append(f"{pid}: invalid convergenceMode {mode!r}")
            expected_mode = "SEMANTIC" if primitive.get("judgmentBearing") else "EXACT"
            if mode != expected_mode:
                errors.append(f"{pid}: expected convergenceMode {expected_mode}, got {mode!r}")
            if not cap.get("capabilityVersion"):
                errors.append(f"{pid}: capabilityVersion required")
            for vector in cap.get("vectors", []):
                if not (ROOT / vector).exists():
                    errors.append(f"{pid}: capability references missing vector {vector}")
            impl = cap.get("implementation", {}).get("path")
            if status in {"IMPLEMENTING", "CONFORMANT", "RELEASED"} and impl and not (ROOT / impl).exists():
                errors.append(f"{pid}: capability references missing implementation {impl}")

    if errors:
        for error in errors:
            print(f"NOMOS-CONVERGE FAIL: {error}")
        return 1

    print("NOMOS-CONVERGE PASS: portable capability and convergence contracts are internally consistent")
    return 0


def verify_receipt(path_str: str) -> int:
    path = Path(path_str)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        print(f"NOMOS-CONVERGE FAIL: receipt not found: {path}")
        return 1

    try:
        receipt = json.loads(path.read_text())
    except Exception as exc:
        print(f"NOMOS-CONVERGE FAIL: invalid receipt JSON: {exc}")
        return 1

    errors: list[str] = []
    pid = receipt.get("primitiveId")
    if not pid:
        errors.append("primitiveId required")
    else:
        try:
            current = fingerprint(pid)
            if receipt.get("authorityFingerprint") != current:
                errors.append(
                    f"authority fingerprint mismatch: receipt={receipt.get('authorityFingerprint')!r} current={current!r}"
                )
        except SystemExit as exc:
            errors.append(str(exc))

    if receipt.get("convergenceMode") not in ALLOWED_CONVERGENCE:
        errors.append("convergenceMode must be EXACT or SEMANTIC")
    for field in ["receiptId", "workId", "baseCommit", "resultCommit", "capabilityVersion"]:
        if not receipt.get(field):
            errors.append(f"{field} required")
    for gate in receipt.get("gates", []):
        if gate.get("state") not in ALLOWED_EVIDENCE:
            errors.append(f"gate {gate.get('id')!r}: invalid evidence state {gate.get('state')!r}")
        if gate.get("state") == "PASS" and not gate.get("evidence"):
            errors.append(f"gate {gate.get('id')!r}: PASS requires evidence")

    if errors:
        for error in errors:
            print(f"NOMOS-CONVERGE FAIL: {error}")
        return 1

    print(f"NOMOS-CONVERGE PASS: receipt {receipt.get('receiptId')} matches current authority target")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    fp = sub.add_parser("fingerprint")
    fp.add_argument("primitive_id")
    vr = sub.add_parser("verify-receipt")
    vr.add_argument("path")
    args = parser.parse_args()

    if args.command == "check":
        return check()
    if args.command == "fingerprint":
        print(fingerprint(args.primitive_id))
        return 0
    if args.command == "verify-receipt":
        return verify_receipt(args.path)
    return 2


if __name__ == "__main__":
    sys.exit(main())
