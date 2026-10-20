"""Guards for MODULARIZED_OUT_PRESSURE_SPEC classification.

Context: WORK-PRESSURE-MODULARIZED-SPEC-2026-10-17.

Six adversarial tests in test_pressure_direct.py target PPA methods that were
gas-modularized out of the core. They are skipped with an explicit reason while
their assertions are preserved verbatim as specification.

Two things must stay true:

1. A skipped test is never a pass. It is classified, it still carries its
   assertions, and its reason names the mandatory property for when the
   extension returns.
2. Skip markers cannot silently accumulate. Any NON-skipped test that calls a
   method which exists in no primitive implementation fails here, so a future
   test written against a removed method is caught at classification time
   rather than becoming another red suite.

Run:
    python -m pytest tests/pressure/test_pressure_surface_guard.py -q
"""
import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PRESSURE = Path(__file__).resolve().parent / "test_pressure_direct.py"
IMPL_GLOB = "primitives/*/implementations/genlayer/*.py"

# Methods declared gas-modularized out of the PPA core.
MODULARIZED = {
    "delegate", "revoke_delegation", "get_delegation",
    "issue_invoice", "settle_invoice", "get_invoice",
    "dispute_payment", "resolve_dispute", "get_dispute",
}
EXTENSIONS = {"delegation", "invoice-settlement", "dispute-refund"}


def _public_methods():
    """Union of every public method across all primitive implementations."""
    out = set()
    for path in sorted(REPO.glob(IMPL_GLOB)):
        tree = ast.parse(path.read_text())
        for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
            for fn in cls.body:
                if not isinstance(fn, ast.FunctionDef):
                    continue
                for dec in fn.decorator_list:
                    if "gl.public" in ast.unparse(dec):
                        out.add(fn.name)
    return out


def _contract_factories(tree):
    """Names whose return value is a deployed contract handle.

    A module-level helper is a factory if it takes `direct_deploy` as a
    parameter, or if its body deploys via `direct_deploy(...)`. `direct_deploy`
    itself counts.
    """
    factories = {"direct_deploy"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        params = {a.arg for a in node.args.args}
        if "direct_deploy" in params:
            factories.add(node.name)
            continue
        for sub in ast.walk(node):
            if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                    and sub.func.id == "direct_deploy"):
                factories.add(node.name)
                break
    return factories


def _contract_handles(fn, factories):
    """Local names bound to a deployed contract inside one test."""
    handles = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            callee = node.value.func
            name = callee.id if isinstance(callee, ast.Name) else None
            if name in factories:
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        handles.add(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Call):
            callee = node.value.func
            if isinstance(callee, ast.Name) and callee.id in factories \
                    and isinstance(node.target, ast.Name):
                handles.add(node.target.id)
    return handles


def _tests():
    """Yield (name, skipped, extension, has_assert, called_methods)."""
    tree = ast.parse(PRESSURE.read_text())
    factories = _contract_factories(tree)
    for fn in tree.body:
        if not isinstance(fn, ast.FunctionDef) or not fn.name.startswith("test_"):
            continue
        skipped, ext = False, None
        for dec in fn.decorator_list:
            d = ast.unparse(dec)
            if d.startswith("modularized_out("):
                skipped = True
                ext = d.split("modularized_out(")[1].rstrip(")").strip("'\"")
        # `assert` and `pytest.raises` are both assertion forms
        has_assert = any(isinstance(n, ast.Assert) for n in ast.walk(fn)) or any(
            isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "raises"
            and isinstance(n.func.value, ast.Name) and n.func.value.id == "pytest"
            for n in ast.walk(fn)
        )
        handles = _contract_handles(fn, factories)
        called = {
            n.func.attr
            for n in ast.walk(fn)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Name) and n.func.value.id in handles
        }
        yield fn.name, skipped, ext, has_assert, called


def test_all_public_methods_discovered():
    """Sanity: the union must be non-trivial or the drift guard is vacuous."""
    assert len(_public_methods()) > 50


def test_every_skip_is_classified_and_justified():
    skipped = [t for t in _tests() if t[1]]
    assert len(skipped) == 6, f"expected 6 modularized-out tests, found {len(skipped)}"
    for name, _s, ext, has_assert, _c in skipped:
        assert ext in EXTENSIONS, f"{name}: unrecognised extension {ext!r}"
        assert has_assert, f"{name}: skipped but its assertions were removed; " \
                           "the body must be preserved as specification"


def test_skipped_tests_only_target_modularized_methods():
    for name, skipped, _ext, _ha, called in _tests():
        if not skipped:
            continue
        overlap = called & MODULARIZED
        assert overlap, f"{name} is skipped but touches no modularized method: {sorted(called)}"


def test_no_unskipped_test_calls_a_method_that_exists_nowhere():
    """Drift guard: catches a new test written against a removed method."""
    public = _public_methods()
    offenders = {}
    for name, skipped, _ext, _ha, called in _tests():
        if skipped:
            continue
        missing = {m for m in called if m not in public and not m.startswith("_")}
        if missing:
            offenders[name] = sorted(missing)
    assert not offenders, (
        "these unskipped pressure tests call methods that exist in no primitive "
        f"implementation; classify them or restore the surface: {offenders}"
    )


def test_skip_reason_states_the_mandatory_property():
    """The skip text must carry the obligation forward, not just say 'skipped'."""
    import pytest  # noqa: F401  (marker resolves at collection time)
    from test_pressure_direct import modularized_out

    for ext in EXTENSIONS:
        reason = modularized_out(ext).mark.kwargs["reason"]
        assert "MODULARIZED_OUT_PRESSURE_SPEC" in reason
        assert "Mandatory property when the extension returns" in reason
        assert "This skip is not a pass" in reason
