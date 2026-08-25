"""Direct tests for DAA v0.1 - authority-source gating.

Covers sender-dependent flows the single-sender vector runner cannot express:
only the recorded authority source may award/reject/revoke; the beneficiary
cannot self-award.

Run:
    python -m pytest primitives/daa/implementations/genlayer/tests/ -v
"""

import json

import pytest
from gltest.direct.loader import create_address

CONTRACT = "primitives/daa/implementations/genlayer/daa.py"

REQUEST_ARGS = (
    "REQ1", "POOL-1", "USD", "BENEFICIARY-B", "treasury-facility",
    "500", "POLICYHASH-1", "0", "9999999999",
)


def _setup(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    contract.request_allocation(*REQUEST_ARGS)
    return contract


def test_authority_source_can_award(direct_vm, direct_deploy, direct_alice):
    contract = _setup(direct_vm, direct_deploy, direct_alice)
    contract.award("REQ1", "AWD1", "400", "5000000000")
    assert json.loads(contract.get_award("AWD1"))["status"] == "AWARDED"


def test_beneficiary_cannot_self_award(direct_vm, direct_deploy, direct_alice):
    contract = _setup(direct_vm, direct_deploy, direct_alice)

    beneficiary = create_address("beneficiary")
    direct_vm.sender = beneficiary
    with pytest.raises(Exception):
        contract.award("REQ1", "AWD1", "400", "5000000000")

    # Request unchanged; the authority source can still award afterwards.
    assert json.loads(contract.get_request("REQ1"))["status"] == "REQUESTED"
    direct_vm.sender = direct_alice
    contract.award("REQ1", "AWD1", "400", "5000000000")
    assert json.loads(contract.get_award("AWD1"))["status"] == "AWARDED"


def test_non_source_cannot_reject_or_revoke(direct_vm, direct_deploy, direct_alice):
    contract = _setup(direct_vm, direct_deploy, direct_alice)

    mallory = create_address("mallory")
    direct_vm.sender = mallory
    with pytest.raises(Exception):
        contract.reject_request("REQ1")

    direct_vm.sender = direct_alice
    contract.award("REQ1", "AWD1", "400", "5000000000")
    direct_vm.sender = mallory
    with pytest.raises(Exception):
        contract.revoke_award("AWD1")

    assert json.loads(contract.get_award("AWD1"))["status"] == "AWARDED"


def test_undetermined_creates_no_authority(direct_vm, direct_deploy, direct_alice):
    contract = _setup(direct_vm, direct_deploy, direct_alice)
    contract.undetermine_request("REQ1")
    assert json.loads(contract.get_request("REQ1"))["status"] == "UNDETERMINED"
    with pytest.raises(Exception):
        contract.award("REQ1", "AWDX", "10", "5000000000")
