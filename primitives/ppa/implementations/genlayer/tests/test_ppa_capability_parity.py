"""PPA capability/source parity guards.

These are pure-AST tests: no GLSim, no deployment. They exist so that the
public surface declared in CAPABILITY.json cannot silently drift from the
executable contract, and so that the two gas-modularization decisions taken
for the v0.2 core deploy stay enforced rather than forgotten.

What each guard protects:

1. `test_public_surface_matches_capability` — a method present in the contract
   but absent from CAPABILITY.json (or vice versa) means the capability
   contract no longer describes the thing that will actually run. AGENTS.md
   requires CAPABILITY.json to describe the canonical input/output surface.

2. `test_capability_public_methods_are_annotated` — the slimming pass for the
   Bradbury gas ceiling strips docstrings and helper annotations first, but
   MUST keep public-method type annotations. Otherwise CAPABILITY.json keeps
   publishing typed inputs that the source no longer expresses, and a
   downstream builder gets a typed interface with no executable evidence
   behind it.

3. `test_gas_modularized_methods_absent_from_core` — invoice/dispute/delegate
   were moved out of the core contract to fit the ~16.77M Bradbury gas
   ceiling. They are declared unsupported in CAPABILITY.json. This guard
   fails if they are reintroduced into the core without updating the
   capability contract first.

Run:
    python -m pytest primitives/ppa/implementations/genlayer/tests/test_ppa_capability_parity.py -q
"""
import ast
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
CAPABILITY = REPO / "primitives" / "ppa" / "CAPABILITY.json"
CONTRACT = REPO / "primitives" / "ppa" / "implementations" / "genlayer" / "ppa.py"

GAS_MODULARIZED = [
    "issue_invoice", "settle_invoice", "get_invoice",
    "dispute_payment", "resolve_dispute", "get_dispute",
    "delegate", "revoke_delegation", "get_delegation",
]


def _capability():
    return json.loads(CAPABILITY.read_text())


def _contract_class():
    tree = ast.parse(CONTRACT.read_text())
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            return node
    raise AssertionError("no class found in ppa.py")


def _public_methods():
    """Map public method name -> ast.FunctionDef for @gl.public.* methods."""
    cls = _contract_class()
    out = {}
    for node in cls.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            if "gl.public" in ast.unparse(dec):
                out[node.name] = node
                break
    return out


def test_public_surface_matches_capability():
    declared = {m["name"] for m in _capability()["publicMethods"]}
    actual = set(_public_methods())
    assert actual - declared == set(), (
        f"contract exposes methods absent from CAPABILITY.json: "
        f"{sorted(actual - declared)}"
    )
    assert declared - actual == set(), (
        f"CAPABILITY.json declares methods absent from the contract: "
        f"{sorted(declared - actual)}"
    )


def test_capability_public_methods_are_annotated():
    """CAPABILITY publishes typed inputs; the source must carry them."""
    public = _public_methods()
    unannotated = []
    for name, fn in public.items():
        params = fn.args.args[1:]  # skip self
        has_param_ann = all(a.annotation is not None for a in params) if params else True
        if not (has_param_ann and fn.returns is not None):
            unannotated.append(name)
    assert unannotated == [], (
        "public methods must keep parameter and return annotations for "
        f"CAPABILITY parity: {sorted(unannotated)}"
    )


def test_storage_fields_keep_annotations():
    """TreeMap storage annotations are load-bearing; never de-annotate them."""
    cls = _contract_class()
    storage = [n for n in cls.body if isinstance(n, ast.AnnAssign)]
    assert storage, "expected class-level AnnAssign storage fields"
    unannotated = [ast.unparse(n.target) for n in storage if n.annotation is None]
    assert unannotated == [], f"storage fields lost annotations: {unannotated}"


def test_gas_modularized_methods_absent_from_core():
    public = set(_public_methods())
    reintroduced = sorted(public & set(GAS_MODULARIZED))
    assert reintroduced == [], (
        "gas-modularized methods must not return to the core contract without "
        f"updating CAPABILITY.json: {reintroduced}"
    )
    unsupported = " ".join(_capability().get("unsupported", []))
    assert "gas-modularized" in unsupported, (
        "CAPABILITY.json must record why invoice/dispute/delegate are absent "
        "from the core deploy"
    )