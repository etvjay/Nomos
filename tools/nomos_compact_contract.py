#!/usr/bin/env python3
"""Deterministic compact deployment artifact for a GenLayer contract.

The readable implementation stays canonical. Bradbury currently rejects the
readable native-GEN custody source because its deploy estimate is above the
node's transaction gas acceptance ceiling. This tool emits a semantics-
preserving compact artifact that is small enough to deploy.

Pinned dependency: python-minifier==3.4.0.

Usage:
    python tools/nomos_compact_contract.py SOURCE OUTPUT
"""

import argparse
import hashlib
import sys

import python_minifier

HEADER = (
    '# {\n'
    '#   "Seq": [\n'
    '#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }\n'
    '#   ]\n'
    '# }\n'
)


def compact(source: str) -> str:
    body = python_minifier.minify(
        source,
        remove_annotations=False,
        remove_pass=True,
        remove_literal_statements=True,
        combine_imports=True,
        rename_locals=True,
        rename_globals=False,
    )
    if not body.endswith("\n"):
        body += "\n"
    return HEADER + body


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output")
    args = parser.parse_args()
    with open(args.source, "r", encoding="utf-8") as handle:
        source = handle.read()
    artifact = compact(source)
    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(artifact)
    print(f"source  {sha256_text(source)}  {len(source.encode('utf-8'))} bytes")
    print(f"compact {sha256_text(artifact)}  {len(artifact.encode('utf-8'))} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
