"""Local glsim tests for the deterministic PPA custody authorizer.

The EVM vault cannot be called by glsim (no EthCall/EthSend). The vault's
mechanics are covered by Foundry tests and the live Phase 1 run. These tests
cover the Core-side decision and the fail-closed vault-unavailable path.

Run:
    source ~/nomos-venv312/bin/activate
    python -m pytest primitives/ppa-custody/implementations/genlayer/tests/ -q
"""
import json
import time

from gltest import get_contract_factory, get_accounts
from gltest.assertions import tx_execution_failed

OWNER = get_accounts()[0]
STRANGER = get_accounts()[1]
OWNER_ADDR = OWNER.address
CORE = "ppa_core.py"
AUTHORIZER = "ppa_custody_authorizer.py"
RECIPIENT = "0x9f6aa7364d20cf25f054ea83f3cb950317fd34b6"
TOKEN = "0x2222222222222222222222222222222222222222"
VAULT = "0x1111111111111111111111111111111111111111"
FAR = "2099-01-01T00:00:00+00:00"
UNIT = str(10**18)
TEN = str(10 * 10**18)
FIVE = str(5 * 10**18)


def _decode(value):
    if isinstance(value, str):
        return json.loads(value)
    return value


def _wire(currency="NTEST"):
    core = get_contract_factory(contract_file_path=CORE).deploy()
    core.initialize(args=[OWNER_ADDR]).transact(wait_interval=3000, wait_retries=10)
    core.create_account(
        args=[
            "ACC-CUSTODY",
            json.dumps(
                {
                    "daily_limit": str(50 * 10**18),
                    "per_tx_limit": str(20 * 10**18),
                    "currency": currency,
                    "policy_version": "CUSTODY-V1",
                }
            ),
        ]
    ).transact(wait_interval=3000, wait_retries=10)
    core.deposit(args=["ACC-CUSTODY", TEN]).transact(wait_interval=3000, wait_retries=10)
    core.register_adapter(args=[OWNER_ADDR]).transact(wait_interval=3000, wait_retries=10)
    authorizer = get_contract_factory(contract_file_path=AUTHORIZER).deploy()
    authorizer.initialize(
        args=[
            OWNER_ADDR,
            core.address,
            OWNER_ADDR,
            VAULT,
            TOKEN,
            "NTEST",
            "3600",
        ]
    ).transact(wait_interval=3000, wait_retries=10)
    return core, authorizer


def _proposal(pid="PROP-CUSTODY-1", amount=UNIT, to=RECIPIENT, account="ACC-CUSTODY"):
    return json.dumps(
        {
            "proposal_id": pid,
            "decision_id": "DEC-" + pid,
            "payment_id": "PAY-" + pid,
            "account_id": account,
            "to": to,
            "amount": amount,
            "policy_version": "CUSTODY-V1",
            "evidence_hash": "sha256:custody-test",
            "expires_at": FAR,
        }
    )


def _execute(core, proposal):
    return core.connect(OWNER).execute_proposal(args=[proposal]).transact(
        wait_interval=3000, wait_retries=10
    )


def test_preview_authorizes_executed_consequence():
    core, authorizer = _wire()
    _execute(core, _proposal("PROP-CUSTODY-1"))
    consequence = _decode(core.get_consequence(args=["PROP-CUSTODY-1"]).call())
    assert consequence["status"] == "EXECUTED", consequence

    preview = _decode(authorizer.preview_authorization(args=["PROP-CUSTODY-1"]).call())
    assert preview["status"] == "AUTHORIZED", preview
    assert preview["reason_code"] == ""
    assert preview["currency"] == "NTEST"
    assert preview["token"] == TOKEN.removeprefix("0x")
    assert preview["recipient"] == RECIPIENT
    assert preview["amount"] == UNIT
    assert preview["payment_id"] == "PAY-PROP-CUSTODY-1"
    assert preview["decision_id"] == "DEC-PROP-CUSTODY-1"
    assert preview["adapter_caller"] == OWNER_ADDR.lower().removeprefix("0x")
    assert preview["core_snapshot_hash"].startswith("sha256:")


def test_preview_rejects_denied_consequence():
    core, authorizer = _wire()
    _execute(core, _proposal("PROP-CUSTODY-DENY", amount=str(21 * 10**18)))
    consequence = _decode(core.get_consequence(args=["PROP-CUSTODY-DENY"]).call())
    assert consequence["status"] == "REJECTED", consequence

    preview = _decode(authorizer.preview_authorization(args=["PROP-CUSTODY-DENY"]).call())
    assert preview["status"] == "REJECTED"
    assert preview["reason_code"] == "REJECTED_CONSEQUENCE_NOT_EXECUTED"


def test_preview_rejects_wrong_adapter():
    core, authorizer = _wire()
    _execute(core, _proposal("PROP-CUSTODY-WRONG-ADAPTER"))
    # The consequence was executed by OWNER, not by the configured adapter.
    wrong = get_contract_factory(contract_file_path=AUTHORIZER).deploy()
    wrong.initialize(
        args=[
            OWNER_ADDR,
            core.address,
            "0x3333333333333333333333333333333333333333",
            VAULT,
            TOKEN,
            "NTEST",
            "3600",
        ]
    ).transact(wait_interval=3000, wait_retries=10)
    preview = _decode(wrong.preview_authorization(args=["PROP-CUSTODY-WRONG-ADAPTER"]).call())
    assert preview["status"] == "REJECTED"
    assert preview["reason_code"] == "REJECTED_WRONG_ADAPTER"


def test_preview_rejects_currency_mismatch():
    core, authorizer = _wire(currency="USDC")
    _execute(core, _proposal("PROP-CUSTODY-CURRENCY"))
    preview = _decode(authorizer.preview_authorization(args=["PROP-CUSTODY-CURRENCY"]).call())
    assert preview["status"] == "REJECTED"
    assert preview["reason_code"] == "REJECTED_CURRENCY_MISMATCH"


def test_authorize_settlement_refuses_missing_consequence():
    core, authorizer = _wire()
    authorizer.authorize_settlement(args=["PROP-MISSING", "60"]).transact(
        wait_interval=3000, wait_retries=10
    )
    record = _decode(authorizer.get_authorization(args=["PROP-MISSING"]).call())
    assert record["status"] == "REJECTED"
    assert record["reason_code"] == "REJECTED_NO_CONSEQUENCE", record


def test_authorize_settlement_emits_pending_finality():
    core, authorizer = _wire()
    _execute(core, _proposal("PROP-CUSTODY-EVM"))
    authorizer.authorize_settlement(args=["PROP-CUSTODY-EVM", "60"]).transact(
        wait_interval=3000, wait_retries=10
    )
    record = _decode(authorizer.get_authorization(args=["PROP-CUSTODY-EVM"]).call())
    assert record["status"] == "AUTHORIZED", record
    assert record["execution"] == "PENDING_FINALITY", record
    assert record["reason_code"] == "", record


def test_authorize_settlement_owner_only():
    core, authorizer = _wire()
    _execute(core, _proposal("PROP-CUSTODY-OWNER"))
    tx = authorizer.connect(STRANGER).authorize_settlement(
        args=["PROP-CUSTODY-OWNER", "60"]
    ).transact(wait_interval=3000, wait_retries=10)
    assert tx_execution_failed(tx), "non-owner authorization did not fail"
    record = _decode(authorizer.get_authorization(args=["PROP-CUSTODY-OWNER"]).call())
    assert record["status"] == "NONE", record


def test_preview_is_view_only_and_replay_safe():
    core, authorizer = _wire()
    _execute(core, _proposal("PROP-CUSTODY-VIEW"))
    first = _decode(authorizer.preview_authorization(args=["PROP-CUSTODY-VIEW"]).call())
    second = _decode(authorizer.preview_authorization(args=["PROP-CUSTODY-VIEW"]).call())
    assert first["status"] == "AUTHORIZED"
    assert second["status"] == "AUTHORIZED"
    assert first["core_snapshot_hash"] == second["core_snapshot_hash"]
    record = _decode(authorizer.get_authorization(args=["PROP-CUSTODY-VIEW"]).call())
    assert record["status"] == "NONE"
