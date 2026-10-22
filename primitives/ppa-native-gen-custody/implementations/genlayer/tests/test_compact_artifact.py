"""The committed deploy artifact must match the deterministic generator."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from tools.nomos_compact_contract import compact  # noqa: E402

SOURCE = ROOT / "primitives/ppa-native-gen-custody/implementations/genlayer/ppa_native_gen_custody.py"
ARTIFACT = ROOT / "primitives/ppa-native-gen-custody/implementations/genlayer/build/ppa_native_gen_custody.compact.py"


def test_compact_artifact_is_current():
    assert compact(SOURCE.read_text(encoding="utf-8")) == ARTIFACT.read_text(encoding="utf-8")
