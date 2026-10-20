"""Regression tests for the canonical vector runner's schema enforcement.

Context: WORK-VECTOR-RUNNER-HARDEN-2026-10-17.

The runner used to iterate ``vector["actions"]``. A vector declaring any other
shape iterated zero times, produced zero failures, and was reported PASS. That
made "implemented and passing" indistinguishable from "never executed", which
invalidates the evidence layer for every primitive that relies on the runner.

These tests pin the fix: the runner must never report PASS for a vector it did
not execute.

Run:
    python -m pytest tests/tools/test_nomos_run_vectors_schema.py -q
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
RUNNER = REPO / "tools" / "nomos_run_vectors.py"
PPA = REPO / "primitives" / "ppa" / "implementations" / "ppa.py"
PPA_IMPL = REPO / "primitives" / "ppa" / "implementations" / "genlayer" / "ppa.py"


def _run(tmp_path, vectors: dict):
    """Run the real runner over a temporary corpus; return (exit_code, stdout)."""
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(vectors))
    proc = subprocess.run(
        [sys.executable, str(RUNNER), str(PPA_IMPL), "--vectors", str(path)],
        capture_output=True, text=True, cwd=str(REPO), timeout=600,
    )
    return proc.returncode, proc.stdout + proc.stderr


def _corpus(*vectors):
    return {"primitive": "schematest", "version": "1", "mode": "EXACT",
            "vectors": list(vectors)}


# --- the bug: a vector with nothing to execute must never PASS ---------------

def test_empty_actions_list_fails(tmp_path):
    code, out = _run(tmp_path, _corpus({"id": "t/empty", "actions": []}))
    assert code == 1, out
    assert "empty" in out and "cannot be reported PASS" in out


def test_missing_actions_key_fails(tmp_path):
    code, out = _run(tmp_path, _corpus(
        {"id": "t/nokey", "claim": {"a": 1}, "evidence": {"b": 2},
         "expected": {"status": "VERIFIED"}}))
    assert code == 1, out
    assert "no 'actions' key" in out
    # the error must name what was actually declared, so the fix is obvious
    assert "claim" in out and "evidence" in out


def test_steps_key_is_explicitly_rejected(tmp_path):
    """'steps' must be named explicitly, with the supported key stated."""
    code, out = _run(tmp_path, _corpus(
        {"id": "t/steps", "steps": [
            {"op": "get_account", "args": ["X"], "expect": {"balance": "impossible"}}]}))
    assert code == 1, out
    assert "steps" in out
    assert "actions" in out


def test_impossible_assertion_under_steps_cannot_pass(tmp_path):
    """The exact historical false-green: same impossible assertion, wrong key."""
    impossible = {"id": "t/vacuous", "steps": [
        {"op": "get_account", "args": ["DEFINITELY-NOT-AN-ACCOUNT"],
         "expect": {"balance": "impossible-value"}}]}
    code, out = _run(tmp_path, _corpus(impossible))
    assert code == 1, out
    assert "PASS t/t/vacuous" not in out


def test_impossible_assertion_under_actions_is_caught(tmp_path):
    """Negative control: the same assertion under the supported key must fail."""
    real = {"id": "t/real-fail", "actions": [
        {"op": "get_account", "args": ["DEFINITELY-NOT-AN-ACCOUNT"],
         "expect": {"balance": "impossible-value"}}]}
    code, out = _run(tmp_path, _corpus(real))
    assert code == 1, out
    # the read genuinely executed and its real outcome is reported
    assert "view raised" in out and "account not found" in out


def test_actions_not_a_list_fails(tmp_path):
    code, out = _run(tmp_path, _corpus({"id": "t/notlist", "actions": {"op": "x"}}))
    assert code == 1, out
    assert "must be a list" in out


def test_action_missing_op_fails(tmp_path):
    code, out = _run(tmp_path, _corpus(
        {"id": "t/noop", "actions": [{"args": ["X"], "expect": "ok"}]}))
    assert code == 1, out
    assert "missing 'op'" in out


def test_vector_not_an_object_fails(tmp_path):
    code, out = _run(tmp_path, _corpus({"id": "t/str", "actions": ["just-a-string"]}))
    assert code == 1, out


# --- and the fix must not break valid vectors --------------------------------

def test_valid_actions_vector_still_passes(tmp_path):
    """Existing valid vectors retain behaviour after hardening."""
    ok = {"id": "t/valid", "actions": [
        {"op": "initialize", "args": ["0x2bd806c97f0e00af1a1fc3328fa763a9269723c8"],
         "expect": "ok"},
        {"op": "create_account",
         "args": ["ACC1", "{\"daily_limit\":\"1000\",\"per_tx_limit\":\"500\",\"currency\":\"USDC\"}"],
         "expect": "ok"},
        {"op": "deposit", "args": ["ACC1", "500"], "expect": "ok"},
        {"op": "get_account", "args": ["ACC1"], "expect": {"balance": "500"}}]}
    code, out = _run(tmp_path, _corpus(ok))
    assert code == 0, out
    assert "1/1 vectors passed" in out


@pytest.mark.parametrize("corpus,expected", [
    ("primitives/ppa/vectors/v0.1.json", "15/15"),
    ("primitives/ppa/vectors/v0.3-origin.json", "9/9"),
])
def test_repository_corpora_still_pass(corpus, expected):
    """Regression: hardening must not change results for valid corpora."""
    proc = subprocess.run(
        [sys.executable, str(RUNNER), str(PPA_IMPL), "--vectors", corpus],
        capture_output=True, text=True, cwd=str(REPO), timeout=900,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert expected in proc.stdout


def test_every_repository_corpus_is_executable_or_explicitly_flagged():
    """No corpus anywhere in the repo may pass vacuously."""
    offenders = []
    for path in sorted((REPO / "primitives").glob("*/vectors/*.json")):
        rel = path.relative_to(REPO).as_posix()
        if "superseded" in rel:
            continue
        data = json.loads(path.read_text())
        for v in data.get("vectors", []):
            if not isinstance(v, dict) or not isinstance(v.get("actions"), list) or not v["actions"]:
                offenders.append(f"{rel}:{v.get('id', '?') if isinstance(v, dict) else '?'}")
    # claim-verification uses claim/evidence/expected and is NOT executed by this
    # runner; its declared evidence is pytest. ppa v0.2-spine is superseded.
    assert set(offenders) == {
        "primitives/claim-verification/vectors/v0.1.json:cv-verified-001",
        "primitives/claim-verification/vectors/v0.1.json:cv-conflicted-001",
        "primitives/claim-verification/vectors/v0.1.json:cv-insufficient-001",
        "primitives/claim-verification/vectors/v0.1.json:cv-undetermined-001",
        "primitives/ppa/vectors/v0.2-spine.json:ppa/spine-accepted-to-settle-001",
        "primitives/ppa/vectors/v0.2-spine.json:ppa/spine-rejected-no-exec-002",
    }, f"unexpected executable-shape change: {offenders}"
