#!/usr/bin/env python3
"""Nomos constitutional repository linter."""

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
    "CONVERGENCE.md",
    "PRIMITIVE_QUALIFICATION.md",
    "nomos.manifest.json",
    "environments/README.md",
    "environments/genlayer/PROFILE.md",
    "conformance/README.md",
    "experiments/README.md",
    "templates/PRIMITIVE_SPEC.md",
    "templates/WORK_CONTRACT.json",
    "templates/CONVERGENCE_RECEIPT.json",
    "tools/nomos_converge.py",
]

EXPECTED_PRIMITIVES = {
    "proof-of-payable",
    "claim-verification",
    "policy-envelope",
    "workflow-authorization",
    "mandate-allocation",
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

ALLOWED_QUALIFICATION = {
    "QUALIFIED",
    "QUALIFIED_EXTENSION",
    "SCOPE_PROVISIONAL",
}

ALLOWED_CONVERGENCE = {"EXACT", "SEMANTIC"}

JUDGMENT_EXPECTED = {
    "claim-verification",
    "workflow-authorization",
    "mandate-allocation",
    "daa",
    "financial-contract",
    "gaia",
}

DETERMINISTIC_EXPECTED = {
    "policy-envelope",
    "proof-of-payable",
    "claim-encumbrance",
    "capital-commitment",
    "dal",
}


def fail(errors: list[str]) -> int:
    for error in errors:
        print(f"NOMOS-LINT FAIL: {error}")
    return 1


def has_executable_content(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    ignored = {"README.md", ".gitkeep"}
    return any(p.is_file() and p.name not in ignored for p in path.rglob("*"))


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
    if manifest.get("convergenceProtocol") != "CONVERGENCE.md":
        errors.append("convergenceProtocol must be CONVERGENCE.md")
    if manifest.get("mandatoryReferenceEnvironment") != "genlayer":
        errors.append("mandatoryReferenceEnvironment must be 'genlayer'")
    if manifest.get("referenceJudgmentSubstrate") != "genlayer":
        errors.append("referenceJudgmentSubstrate must remain 'genlayer' unless constitutionally changed")

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
        qualification = primitive.get("qualification")
        path = primitive.get("canonicalPath")
        judgment = primitive.get("judgmentBearing")
        genlayer_required = primitive.get("genlayerRequired")

        if status not in ALLOWED_STATUS:
            errors.append(f"{pid}: invalid status {status!r}")
        if qualification not in ALLOWED_QUALIFICATION:
            errors.append(f"{pid}: invalid or missing qualification {qualification!r}")
        if genlayer_required is not True:
            errors.append(f"{pid}: every Nomos primitive must set genlayerRequired=true")

        if qualification == "SCOPE_PROVISIONAL" and status in {
            "IMPLEMENTING",
            "CONFORMANT",
            "RELEASED",
        }:
            errors.append(
                f"{pid}: SCOPE_PROVISIONAL primitives may not advance to {status}; narrow and re-qualify the public state model first"
            )

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

        if status in {"IMPLEMENTING", "CONFORMANT", "RELEASED"} and path:
            capsule = ROOT / path
            capability_path = capsule / "CAPABILITY.json"
            if not capability_path.exists():
                errors.append(f"{pid}: {status} requires {path}/CAPABILITY.json")
            else:
                try:
                    capability = json.loads(capability_path.read_text())
                except Exception as exc:
                    errors.append(f"{pid}: invalid CAPABILITY.json: {exc}")
                    capability = {}
                if capability.get("primitiveId") != pid:
                    errors.append(f"{pid}: CAPABILITY primitiveId must equal registry id")
                if capability.get("status") != status:
                    errors.append(f"{pid}: CAPABILITY status must equal manifest status")
                if capability.get("capabilityVersion") != primitive.get("capabilityVersion"):
                    errors.append(f"{pid}: manifest capabilityVersion must match CAPABILITY.json")
                expected_mode = "SEMANTIC" if judgment else "EXACT"
                if primitive.get("convergenceMode") != expected_mode:
                    errors.append(f"{pid}: manifest convergenceMode must be {expected_mode}")
                if capability.get("convergenceMode") != expected_mode:
                    errors.append(f"{pid}: CAPABILITY convergenceMode must be {expected_mode}")
                if capability.get("convergenceMode") not in ALLOWED_CONVERGENCE:
                    errors.append(f"{pid}: invalid convergence mode")

            genlayer = capsule / "implementations" / "genlayer"
            if not genlayer.exists():
                errors.append(f"{pid}: {status} requires {path}/implementations/genlayer/")
            elif not (genlayer / "README.md").exists():
                errors.append(f"{pid}: GenLayer implementation requires adjacent README.md")
            elif not has_executable_content(genlayer):
                errors.append(f"{pid}: {status} requires executable GenLayer implementation content")

        if status in {"CONFORMANT", "RELEASED"} and path:
            receipt_dir = ROOT / path / "receipts"
            if not receipt_dir.exists() or not any(receipt_dir.iterdir()):
                errors.append(f"{pid}: {status} requires at least one release/conformance receipt")

    if errors:
        return fail(errors)

    print("NOMOS-LINT PASS: constitutional, capability, convergence and GenLayer contracts are consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
