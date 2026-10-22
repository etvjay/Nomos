"""Direct-VM tests for PPA native GEN custody.

The direct VM gives each contract its own storage, a settable message value,
and time warping. Native emit_transfer is stubbed because direct mode has no
gl.chain; the stub debits the vault and credits the recipient so accounting is
checked end to end. Live child-transaction finality remains a testnet proof.

Run:
    source ~/nomos-venv312/bin/activate
    python -m pytest primitives/ppa-native-gen-custody/implementations/genlayer/tests/ -q
"""

import json
import os
import sys

import pytest

from gltest.direct.loader import create_address
from glsim.engine import SimEngine
from glsim.state import StateStore

CORE = "contracts/ppa_core.py"
CUSTODY = os.environ.get("NOMOS_CUSTODY_PATH", "contracts/ppa_native_gen_custody.py")
BASE = "2026-01-01T00:00:00Z"
FAR = "2099-01-01T00:00:00+00:00"
UNIT = str(10**18)
TEN = str(10 * 10**18)
FIVE = str(5 * 10**18)
RECIPIENT = "0x9f6aa7364d20cf25f054ea83f3cb950317fd34b6"
WRONG_RECIPIENT = "0x1111111111111111111111111111111111111111"
OWNER = create_address("custody-owner")
ADAPTER = create_address("custody-adapter")
STRANGER = create_address("custody-stranger")


def _hex(address):
    if isinstance(address, str):
        return address
    if hasattr(address, "as_hex"):
        value = address.as_hex
        return value if isinstance(value, str) else value()
    return "0x" + bytes(address).hex()


OWNER_HEX = _hex(OWNER)
ADAPTER_HEX = _hex(ADAPTER)
STRANGER_HEX = _hex(STRANGER)


def _decode(value):
    if isinstance(value, str):
        return json.loads(value)
    return value


def _proposal(pid="PROP-NGEN-1", amount=UNIT, to=RECIPIENT, account="ACC-GEN"):
    return json.dumps(
        {
            "proposal_id": pid,
            "decision_id": "DEC-" + pid,
            "payment_id": "PAY-" + pid,
            "account_id": account,
            "to": to,
            "amount": amount,
            "policy_version": "GEN-V1",
            "evidence_hash": "sha256:gen-test",
            "expires_at": FAR,
        }
    )


class _AccountStub:
    def __init__(self, engine, address):
        self.engine = engine
        self.address = address

    def emit_transfer(self, value, on="finalized"):
        import genlayer.gl as gl

        amount = int(value)
        vault = self.engine.vm._to_bytes(gl.message.contract_address)
        recipient = self.engine.vm._to_bytes(self.address)
        assert self.engine.vm._balances.get(vault, 0) >= amount
        self.engine.vm._balances[vault] = self.engine.vm._balances.get(vault, 0) - amount
        self.engine.vm._balances[recipient] = (
            self.engine.vm._balances.get(recipient, 0) + amount
        )
        self.engine.transfers.append(
            {"vault": vault.hex(), "recipient": recipient.hex(), "amount": amount, "on": on}
        )
        return amount


class _ChainStub:
    def __init__(self, engine):
        self.engine = engine

    def Account(self, address):
        return _AccountStub(self.engine, address)


def _warp(engine, iso):
    engine.vm.warp(iso)
    if "genlayer.gl" in sys.modules:
        sys.modules["genlayer.gl"].message_raw["datetime"] = iso


def _wire(
    currency="GEN",
    core_adapter=ADAPTER_HEX,
    vault_adapter=None,
):
    vault_adapter = vault_adapter or core_adapter
    state = StateStore(chain_id=4221)
    engine = SimEngine(state)
    engine.activate()
    engine.transfers = []
    try:
        core_addr, _ = engine.deploy(CORE)
        engine.call_method(core_addr, "initialize", args=[OWNER_HEX], sender=OWNER_HEX)
        engine.call_method(
            core_addr,
            "create_account",
            args=[
                "ACC-GEN",
                json.dumps(
                    {
                        "daily_limit": str(50 * 10**18),
                        "per_tx_limit": str(20 * 10**18),
                        "currency": currency,
                        "policy_version": "GEN-V1",
                    }
                ),
            ],
            sender=OWNER_HEX,
        )
        engine.call_method(core_addr, "deposit", args=["ACC-GEN", TEN], sender=OWNER_HEX)
        engine.call_method(
            core_addr, "register_adapter", args=[core_adapter], sender=OWNER_HEX
        )
        vault_addr, _ = engine.deploy(CUSTODY)
        engine.call_method(
            vault_addr,
            "initialize",
            args=[OWNER_HEX, core_addr, vault_adapter, "86400"],
            sender=OWNER_HEX,
        )
        _warp(engine, BASE)
        import genlayer.gl as gl

        gl.chain = _ChainStub(engine)
        return engine, core_addr, vault_addr
    except Exception:
        engine.deactivate()
        raise


def _call(engine, address, method, args=None, sender=OWNER_HEX, value=0):
    engine.vm.value = value
    try:
        return engine.call_method(address, method, args=args or [], sender=sender)
    finally:
        engine.vm.value = 0


def _deposit(engine, vault, amount=TEN, sender=OWNER_HEX):
    vault_bytes = engine.vm._to_bytes(vault)
    engine.vm.deal(vault_bytes, engine.vm._balances.get(vault_bytes, 0) + int(amount))
    return _call(engine, vault, "deposit", sender=sender, value=int(amount))


def _execute(engine, core, proposal):
    return _call(engine, core, "execute_proposal", args=[proposal], sender=ADAPTER_HEX)


def _intent(engine, vault, pid):
    return _decode(_call(engine, vault, "get_intent", args=[pid], sender=STRANGER_HEX))


def _balance(engine, address):
    return engine.vm._balances.get(engine.vm._to_bytes(address), 0)


def test_initialize_and_deposit_accounting():
    engine, _, vault = _wire()
    try:
        config = _decode(engine.call_method(vault, "get_config", sender=STRANGER_HEX))
        assert config["currency"] == "GEN"
        assert config["owner"] == OWNER_HEX.removeprefix("0x")
        assert config["max_ttl"] == "86400"
        assert config["paused"] is False

        _deposit(engine, vault, TEN)
        balance = _decode(engine.call_method(vault, "get_balance", sender=STRANGER_HEX))
        assert balance["balance"] == TEN
        assert balance["total_deposited"] == TEN
        assert balance["total_emitted"] == "0"
        assert balance["reconciled"] is True
        deposit = _decode(_call(engine, vault, "get_deposit", args=["1"], sender=STRANGER_HEX))
        assert deposit["amount"] == TEN
        assert _balance(engine, vault) == int(TEN)
    finally:
        engine.deactivate()


def test_authorize_binds_exact_core_fields():
    engine, core, vault = _wire()
    try:
        _execute(engine, core, _proposal("PROP-NGEN-AUTH"))
        record = _decode(
            _call(engine, vault, "authorize", args=["PROP-NGEN-AUTH", "3600"])
        )
        assert record["status"] == "AUTHORIZED", record
        intent = _intent(engine, vault, "PROP-NGEN-AUTH")
        assert intent["status"] == "AUTHORIZED"
        assert intent["recipient"] == RECIPIENT.removeprefix("0x")
        assert intent["amount"] == UNIT
        assert intent["currency"] == "GEN"
        assert intent["execution"] == "NONE"
        assert intent["core_snapshot_hash"].startswith("sha256:")
        assert intent["payment_id"] == "PAY-PROP-NGEN-AUTH"
        assert intent["decision_id"] == "DEC-PROP-NGEN-AUTH"
        assert intent["adapter_caller"] == ADAPTER_HEX.removeprefix("0x")
        assert intent["expires_at"].endswith("Z")
    finally:
        engine.deactivate()


def test_preview_and_settle_emit_exact_amount():
    engine, core, vault = _wire()
    try:
        _execute(engine, core, _proposal("PROP-NGEN-SETTLE"))
        _deposit(engine, vault, TEN)
        _call(engine, vault, "authorize", args=["PROP-NGEN-SETTLE", "3600"])
        preview = _decode(
            _call(
                engine,
                vault,
                "preview_settlement",
                args=["PROP-NGEN-SETTLE", RECIPIENT, UNIT],
                sender=STRANGER_HEX,
            )
        )
        assert preview["status"] == "SETTLEABLE", preview
        vault_before = _balance(engine, vault)
        recipient_before = _balance(engine, RECIPIENT)

        record = _decode(
            _call(
                engine,
                vault,
                "settle",
                args=["PROP-NGEN-SETTLE", RECIPIENT, UNIT],
                sender=STRANGER_HEX,
            )
        )
        assert record["status"] == "PENDING_FINALITY", record
        assert _balance(engine, vault) == vault_before - int(UNIT)
        assert _balance(engine, RECIPIENT) == recipient_before + int(UNIT)
        assert engine.transfers[-1]["amount"] == int(UNIT)
        assert engine.transfers[-1]["on"] == "finalized"

        intent = _intent(engine, vault, "PROP-NGEN-SETTLE")
        assert intent["status"] == "PENDING_FINALITY"
        assert intent["execution"] == "PENDING_FINALITY"
        assert intent["settler"] == STRANGER_HEX.removeprefix("0x")
        balance = _decode(engine.call_method(vault, "get_balance", sender=STRANGER_HEX))
        assert balance["total_emitted"] == UNIT
        assert balance["total_deposited"] == TEN
        assert balance["reconciled"] is True
    finally:
        engine.deactivate()


def test_settle_replay_refused():
    engine, core, vault = _wire()
    try:
        _execute(engine, core, _proposal("PROP-NGEN-REPLAY"))
        _deposit(engine, vault, TEN)
        _call(engine, vault, "authorize", args=["PROP-NGEN-REPLAY", "3600"])
        _call(engine, vault, "settle", args=["PROP-NGEN-REPLAY", RECIPIENT, UNIT])
        replay = _decode(
            _call(
                engine,
                vault,
                "preview_settlement",
                args=["PROP-NGEN-REPLAY", RECIPIENT, UNIT],
                sender=STRANGER_HEX,
            )
        )
        assert replay["reason_code"] == "REJECTED_ALREADY_EMITTED"
        assert _intent(engine, vault, "PROP-NGEN-REPLAY")["status"] == "PENDING_FINALITY"
    finally:
        engine.deactivate()


def test_settle_wrong_recipient_and_amount_refused():
    engine, core, vault = _wire()
    try:
        _execute(engine, core, _proposal("PROP-NGEN-MISMATCH"))
        _deposit(engine, vault, TEN)
        _call(engine, vault, "authorize", args=["PROP-NGEN-MISMATCH", "3600"])

        wrong_recipient = _decode(
            _call(
                engine,
                vault,
                "preview_settlement",
                args=["PROP-NGEN-MISMATCH", WRONG_RECIPIENT, UNIT],
                sender=STRANGER_HEX,
            )
        )
        assert wrong_recipient["reason_code"] == "REJECTED_RECIPIENT_MISMATCH"
        wrong_amount = _decode(
            _call(
                engine,
                vault,
                "preview_settlement",
                args=["PROP-NGEN-MISMATCH", RECIPIENT, FIVE],
                sender=STRANGER_HEX,
            )
        )
        assert wrong_amount["reason_code"] == "REJECTED_AMOUNT_MISMATCH"
        assert _intent(engine, vault, "PROP-NGEN-MISMATCH")["status"] == "AUTHORIZED"
    finally:
        engine.deactivate()


def test_paused_vault_refuses_settlement():
    engine, core, vault = _wire()
    try:
        _execute(engine, core, _proposal("PROP-NGEN-PAUSED"))
        _deposit(engine, vault, TEN)
        _call(engine, vault, "authorize", args=["PROP-NGEN-PAUSED", "3600"])
        _call(engine, vault, "pause")
        refused = _decode(
            _call(
                engine,
                vault,
                "preview_settlement",
                args=["PROP-NGEN-PAUSED", RECIPIENT, UNIT],
                sender=STRANGER_HEX,
            )
        )
        assert refused["reason_code"] == "REJECTED_VAULT_PAUSED"
        _call(engine, vault, "unpause")
        record = _decode(
            _call(engine, vault, "settle", args=["PROP-NGEN-PAUSED", RECIPIENT, UNIT])
        )
        assert record["status"] == "PENDING_FINALITY", record
    finally:
        engine.deactivate()


def test_insufficient_custody_refused():
    engine, core, vault = _wire()
    try:
        _execute(engine, core, _proposal("PROP-NGEN-UNFUNDED"))
        _call(engine, vault, "authorize", args=["PROP-NGEN-UNFUNDED", "3600"])
        refused = _decode(
            _call(
                engine,
                vault,
                "preview_settlement",
                args=["PROP-NGEN-UNFUNDED", RECIPIENT, UNIT],
                sender=STRANGER_HEX,
            )
        )
        assert refused["reason_code"] == "REJECTED_INSUFFICIENT_CUSTODY"
        assert _intent(engine, vault, "PROP-NGEN-UNFUNDED")["status"] == "AUTHORIZED"
    finally:
        engine.deactivate()


def test_expired_intent_refused_and_terminal():
    engine, core, vault = _wire()
    try:
        _execute(engine, core, _proposal("PROP-NGEN-EXPIRED"))
        _deposit(engine, vault, TEN)
        _call(engine, vault, "authorize", args=["PROP-NGEN-EXPIRED", "1"])
        _warp(engine, "2026-01-01T00:00:02Z")
        record = _decode(
            _call(engine, vault, "settle", args=["PROP-NGEN-EXPIRED", RECIPIENT, UNIT])
        )
        assert record["status"] == "REJECTED"
        assert record["reason_code"] == "REJECTED_INTENT_EXPIRED"
        intent = _intent(engine, vault, "PROP-NGEN-EXPIRED")
        assert intent["status"] == "EXPIRED"
        again = _decode(
            _call(engine, vault, "authorize", args=["PROP-NGEN-EXPIRED", "3600"])
        )
        assert again["reason_code"] == "REJECTED_INTENT_EXPIRED"
        assert _intent(engine, vault, "PROP-NGEN-EXPIRED")["status"] == "EXPIRED"
        assert _balance(engine, RECIPIENT) == 0
    finally:
        engine.deactivate()


def test_non_owner_authorize_reverts():
    engine, core, vault = _wire()
    try:
        _execute(engine, core, _proposal("PROP-NGEN-OWNER"))
        with pytest.raises(Exception):
            _call(engine, vault, "authorize", args=["PROP-NGEN-OWNER", "60"], sender=STRANGER_HEX)
        assert _intent(engine, vault, "PROP-NGEN-OWNER")["status"] == "NONE"
    finally:
        engine.deactivate()


def test_wrong_adapter_refused():
    engine, core, vault = _wire(vault_adapter=STRANGER_HEX)
    try:
        _execute(engine, core, _proposal("PROP-NGEN-ADAPTER"))
        _call(engine, vault, "authorize", args=["PROP-NGEN-ADAPTER", "3600"])
        intent = _intent(engine, vault, "PROP-NGEN-ADAPTER")
        assert intent["status"] == "REJECTED"
        assert intent["reason_code"] == "REJECTED_WRONG_ADAPTER"
    finally:
        engine.deactivate()


def test_currency_mismatch_refused():
    engine, core, vault = _wire(currency="USDC")
    try:
        _execute(engine, core, _proposal("PROP-NGEN-USDC"))
        _call(engine, vault, "authorize", args=["PROP-NGEN-USDC", "3600"])
        intent = _intent(engine, vault, "PROP-NGEN-USDC")
        assert intent["status"] == "REJECTED"
        assert intent["reason_code"] == "REJECTED_CURRENCY_MISMATCH"
    finally:
        engine.deactivate()


def test_missing_consequence_refused():
    engine, _, vault = _wire()
    try:
        _call(engine, vault, "authorize", args=["PROP-NGEN-MISSING", "3600"])
        intent = _intent(engine, vault, "PROP-NGEN-MISSING")
        assert intent["status"] == "REJECTED"
        assert intent["reason_code"] == "REJECTED_NO_CONSEQUENCE"
    finally:
        engine.deactivate()


def test_refund_hook_records_value_and_credits_balance():
    engine, _, vault = _wire()
    try:
        _deposit(engine, vault, TEN)
        before = _balance(engine, vault)
        vault_bytes = engine.vm._to_bytes(vault)
        engine.vm.deal(vault_bytes, before + int(UNIT))
        record = _decode(
            _call(engine, vault, "__on_errored_message__", value=int(UNIT))
        )
        assert record["amount"] == UNIT
        assert _decode(_call(engine, vault, "get_refund", args=["1"], sender=STRANGER_HEX))[
            "amount"
        ] == UNIT
        balance = _decode(engine.call_method(vault, "get_balance", sender=STRANGER_HEX))
        assert balance["total_refunded"] == UNIT
        assert balance["balance"] == str(before + int(UNIT))
        assert balance["reconciled"] is True
    finally:
        engine.deactivate()
