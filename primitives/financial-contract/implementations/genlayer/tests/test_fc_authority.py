"""Direct tests for Financial Contract v0.1 — creditor authority gate.

Covers sender-dependent default declaration the single-sender vector runner
cannot express.

Run:
    python -m pytest primitives/financial-contract/implementations/genlayer/tests/ -v
"""

import json

import pytest
from gltest.direct.loader import create_address

CONTRACT = "primitives/financial-contract/implementations/genlayer/financial_contract.py"


def _hex(a) -> str:
    return a.hex() if isinstance(a, bytes) else str(a).lower().removeprefix("0x")


def test_creditor_can_declare_default_after_maturity(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    contract.open_contract("FC1", _hex(direct_alice), "OBLIGOR-B", "100", "USD", "0", "1", "P1")
    # warp past maturity
    direct_vm.warp("2030-01-01T00:00:00Z")
    contract.declare_default("FC1")
    assert json.loads(contract.get_contract("FC1"))["status"] == "DEFAULTED"
    # payments denied on defaulted contract
    result = json.loads(contract.apply_payment("FC1", "P1", "10", "1830297600000"))
    assert result["decision"] == "DENY"


def test_non_creditor_cannot_declare_default(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    contract.open_contract("FC1", _hex(direct_alice), "OBLIGOR-B", "100", "USD", "0", "1", "P1")
    direct_vm.warp("2030-01-01T00:00:00Z")

    mallory = create_address("mallory")
    direct_vm.sender = mallory
    with pytest.raises(Exception):
        contract.declare_default("FC1")

    assert json.loads(contract.get_contract("FC1"))["status"] == "ACTIVE"


def test_default_before_maturity_rejected(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    contract.open_contract("FC1", _hex(direct_alice), "OBLIGOR-B", "100", "USD", "0", "1893456000", "P1")
    with pytest.raises(Exception):
        contract.declare_default("FC1")
    assert json.loads(contract.get_contract("FC1"))["status"] == "ACTIVE"
