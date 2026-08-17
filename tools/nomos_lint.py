#!/usr/bin/env python3
"""Nomos constitutional repository linter.

This intentionally checks governance structure and machine-readable truth before
language- or environment-specific test suites run.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_ROOT = [
    "README.md",
    "CONSTITUTION.md",
    "GOVERNANCE.md",
    "AGENTS.md",
    "nomos.manifest.json",
    "environments/README.md",
    "conformance/README.md",
    "experiments/README.md",
    "templates/PRIMITIVE_SPEC.md",
]

EXPECTED_PRIMITIVES = {
    "proof-of-payable",
    "claim-verification",
    "policy-envelope",
    "workflow-authorization",
    "daa",
    "claim-encumbrance",
    "capital-commitment",
    "dal",
    "financial-contract",
    "gaia",
}

ALLOWED_STATUS = {
    "DISCOVERY",
    "RESEARCHING",
    "SPECIFIED",
    "IMPLEMENTING",
    "CONFORMANT",
    "RELEASED",
    "BLOCKED",
}

JUDGMENT_EXPECTED = {
    "proof-of-payable",
    "claim-verification",
    "policy-envelope",
    "workflow-authorization",
    "daa",
    "financial-contract",
    "gaia",
}

DETERMINISTIC_EXPECTED = {
    "claim-encumbrance",
    "capital-commitment",
    "dal",
}


def fail(errors: list[str]) -> int:
    for error in errors:
        print(f"NOMOS-LINT FAIL: {error}")
    return 1


def main() -> int:
    errors: list[str] = []

    for rel in REQUIRED_ROOT:
        if not (ROOT / rel).exists():
            errors.append(f"missing required governance file: {rel}")

    manifest_path = ROOT / "nomos.manifest.json"
    if not manifest_path.exists():
        return fail(errors or ["nomos.manifest.json missing"])

    try:
        manifest = json.loads(manifest_path.read_text())
    except Exception as exc:
        return fail(errors + [f"manifest is invalid JSON: {exc}"])

    if manifest.get("constitutionalAuthority") != "CONSTITUTION.md":
        errors.append("constitutionalAuthority must be CONSTITUTION.md")

    primitives = manifest.get("primitives")
    if not isinstance(primitives, list):
        errors.append("manifest.primitives must be a list")
        return fail(errors)

    ids = [p.get("id") for p in primitives if isinstance(p, dict)]
    if len(ids) != len(set(ids)):
        errors.append("primitive IDs must be unique")

    actual = set(ids)
    missing = EXPECTED_PRIMITIVES - actual
    extra = actual - EXPECTED_PRIMITIVES
    if missing:
        errors.append(f"missing canonical primitive registry entries: {sorted(missing)}")
    if extra:
        errors.append(f"unreviewed primitive registry entries present: {sorted(extra)}")

    for primitive in primitives:
        if not isinstance(primitive, dict):
            errors.append("every primitive entry must be an object")
            continue

        pid = primitive.get("id")
        status = primitive.get("status")
        path = primitive.get("canonicalPath")
        judgment = primitive.get("judgmentBearing")

        if status not in ALLOWED_STATUS:
            errors.append(f"{pid}: invalid status {status!r}")

        if pid in JUDGMENT_EXPECTED and judgment is not True:
            errors.append(f"{pid}: expected judgmentBearing=true")
        if pid in DETERMINISTIC_EXPECTED and judgment is not False:
            errors.append(f"{pid}: expected judgmentBearing=false")

        if status in {"SPECIFIED", "IMPLEMENTING", "CONFORMANT", "RELEASED"}:
            if not path:
                errors.append(f"{pid}: mature state requires canonicalPath")
                continue
            capsule = ROOT / path
            for required in ["SPEC.md", "INVARIANTS.md", "THREAT_MODEL.md", "DECISION_BOUNDARY.md"]:
                if not (capsule / required).exists():
                    errors.append(f"{pid}: {status} requires {path}/{required}")

        if status in {"CONFORMANT", "RELEASED"}:
            receipt_dir = ROOT / path / "receipts" if path else None
            if not receipt_dir or not receipt_dir.exists() or not any(receipt_dir.iterdir()):
                errors.append(f"{pid}: {status} requires at least one release/conformance receipt")

    if manifest.get("referenceJudgmentSubstrate") != "genlayer":
        errors.append("referenceJudgmentSubstrate must remain 'genlayer' unless constitutionally changed")

    if errors:
        return fail(errors)

    print("NOMOS-LINT PASS: constitutional repository structure and manifest are consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
