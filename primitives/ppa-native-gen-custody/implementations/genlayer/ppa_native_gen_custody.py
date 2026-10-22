# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
"""PPA Native GEN Custody (GenLayer) v0.1 - IMPLEMENTING.

Deterministic custody of native GEN behind an EXECUTED PPA Core consequence.
The owner can authorize a Core-bound intent and cannot choose the recipient or
amount. Any caller can settle the exact intent, but only at the stored expiry,
with the stored recipient and amount, and while the vault is funded and not
paused. There is no owner withdrawal or settle shortcut.

Authority:
  PPA Core consequence/payment/GEN account
    -> this contract (read + deterministic revalidation)
    -> persisted intent (exact recipient/amount/expiry)
    -> permissionless settle
    -> finalized native GEN emit_transfer to the exact recipient

The contract does not adjudicate, does not call an LLM, and does not read the
web. Child-transaction success is external; the vault records PENDING_FINALITY
and never claims the recipient was credited.
"""

import datetime
import hashlib
import json
import typing

from genlayer import *
import genlayer.gl as gl


NATIVE_CURRENCY = "GEN"
MAX_TTL = 604800
ZERO_ADDRESS = "0" * 40


def _now_iso():
    dt = getattr(gl.message, "datetime", None)
    if dt:
        return dt
    return gl.message_raw["datetime"]


def _ts(iso):
    txt = iso.strip().replace("Z", "+00:00")
    return int(datetime.datetime.fromisoformat(txt).timestamp())


def _iso(epoch):
    return (
        datetime.datetime.fromtimestamp(int(epoch), datetime.timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _norm_addr(value):
    if not isinstance(value, str):
        return ""
    return value.lower().removeprefix("0x")


def _valid_addr(value):
    if not isinstance(value, str):
        return False
    text = value.lower()
    if not text.startswith("0x") or len(text) != 42:
        return False
    try:
        int(text[2:], 16)
    except ValueError:
        return False
    return True


def _valid_id(value):
    return isinstance(value, str) and 0 < len(value) <= 128


def _positive_uint(value):
    if not isinstance(value, str) or not value.isdigit():
        return None
    n = int(value)
    if n <= 0:
        return None
    return n


def _as_dict(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


class PPANativeGenCustody(gl.Contract):
    meta: TreeMap[str, str]
    intents: TreeMap[str, str]
    deposits: TreeMap[str, str]
    refunds: TreeMap[str, str]

    def __init__(self) -> None:
        pass

    def _sender(self):
        return gl.message.sender_address.as_hex.lower().removeprefix("0x")

    def _own_address(self):
        ca = gl.message.contract_address
        if isinstance(ca, (bytes, bytearray)):
            return bytes(ca).hex()
        h = ca.as_hex if hasattr(ca, "as_hex") else str(ca)
        return h.lower().removeprefix("0x")

    def _assert_initialized(self):
        if not self.meta.get("owner"):
            raise ValueError("Custody: not initialized")

    def _assert_owner(self):
        self._assert_initialized()
        if self._sender() != self.meta.get("owner"):
            raise ValueError("Custody: caller is not owner")

    def _paused(self):
        return self.meta.get("paused") == "1"

    def _max_ttl(self):
        try:
            return int(self.meta.get("max_ttl", str(MAX_TTL)))
        except Exception:
            return MAX_TTL

    def _total(self, key):
        try:
            return int(self.meta.get(key, "0"))
        except Exception:
            return 0

    def _set_total(self, key, value):
        self.meta[key] = str(int(value))

    def _next_seq(self, key):
        try:
            seq = int(self.meta.get(key, "1"))
        except Exception:
            seq = 1
        self.meta[key] = str(seq + 1)
        return seq

    def _refusal(self, base, reason, detail=""):
        record = dict(base)
        record["status"] = "UNDETERMINED" if reason.startswith("UNDETERMINED_") else "REJECTED"
        record["reason_code"] = reason
        if detail:
            record["detail"] = detail
        return record

    def _get_intent(self, consequence_id):
        raw = self.intents.get(consequence_id)
        if not raw:
            return None
        return _as_dict(raw)

    @gl.public.write
    def initialize(
        self,
        owner: str,
        core_address: str,
        adapter_address: str,
        max_ttl_seconds: str,
    ) -> typing.Any:
        if self.meta.get("owner"):
            raise ValueError("Custody: already initialized")
        for value in (owner, core_address, adapter_address):
            if not _valid_addr(value):
                raise ValueError("Custody: invalid address")
        ttl = _positive_uint(max_ttl_seconds)
        if ttl is None or ttl > MAX_TTL:
            raise ValueError("Custody: invalid max_ttl_seconds")

        self.meta["owner"] = _norm_addr(owner)
        self.meta["core"] = _norm_addr(core_address)
        self.meta["adapter"] = _norm_addr(adapter_address)
        self.meta["currency"] = NATIVE_CURRENCY
        self.meta["max_ttl"] = str(ttl)
        self.meta["paused"] = "0"
        self.meta["created"] = _now_iso()
        self.meta["self"] = self._own_address()
        self.meta["next_deposit"] = "1"
        self.meta["next_refund"] = "1"
        self.meta["total_deposited"] = "0"
        self.meta["total_emitted"] = "0"
        self.meta["total_refunded"] = "0"
        return {
            "status": "INITIALIZED",
            "owner": self.meta["owner"],
            "core": self.meta["core"],
            "adapter": self.meta["adapter"],
            "currency": NATIVE_CURRENCY,
            "max_ttl": str(ttl),
            "self": self.meta["self"],
        }

    @gl.public.write.payable
    def deposit(self) -> typing.Any:
        self._assert_initialized()
        value = int(gl.message.value)
        if value <= 0:
            raise ValueError("Custody: deposit value required")
        seq = self._next_seq("next_deposit")
        record = {
            "seq": str(seq),
            "sender": self._sender(),
            "amount": str(value),
            "balance_after": str(int(self.balance)),
            "at": _now_iso(),
        }
        self.deposits[str(seq)] = json.dumps(record)
        self._set_total("total_deposited", self._total("total_deposited") + value)
        return record

    def _evaluate(self, consequence_id, ttl_seconds):
        now_iso = _now_iso()
        try:
            now = _ts(now_iso)
        except Exception:
            now = 0
        base = {
            "consequence_id": consequence_id,
            "proposal_id": consequence_id,
            "currency": NATIVE_CURRENCY,
            "recipient": "",
            "amount": "0",
            "evaluated_at": now_iso,
            "expires_at": _iso(now + ttl_seconds),
        }
        if not _valid_id(consequence_id):
            return self._refusal(base, "REJECTED_INVALID_CONSEQUENCE_ID")
        if ttl_seconds <= 0 or ttl_seconds > self._max_ttl():
            return self._refusal(base, "REJECTED_INVALID_TTL")

        core_hex = self.meta.get("core", "")
        if not core_hex:
            return self._refusal(base, "UNDETERMINED_DEPENDENCY", "core-not-configured")
        try:
            core = gl.get_contract_at(Address("0x" + core_hex))
        except Exception as exc:
            return self._refusal(base, "REJECTED_CORE_UNAVAILABLE", str(exc)[:200])

        try:
            consequence = _as_dict(core.view().get_consequence(consequence_id))
        except Exception as exc:
            message = str(exc).lower()
            if "no consequence" in message or "not found" in message:
                return self._refusal(base, "REJECTED_NO_CONSEQUENCE", str(exc)[:200])
            return self._refusal(base, "REJECTED_CORE_UNAVAILABLE", str(exc)[:200])
        if consequence is None:
            return self._refusal(base, "UNDETERMINED_DEPENDENCY", "consequence-not-object")

        if consequence.get("proposal_id") != consequence_id:
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "consequence-proposal-mismatch")
        if consequence.get("status") != "EXECUTED" or consequence.get("reason_code") != "EXECUTED":
            return self._refusal(
                base,
                "REJECTED_CONSEQUENCE_NOT_EXECUTED",
                str(consequence.get("status", "")),
            )
        if consequence.get("payment_status") != "SETTLED":
            return self._refusal(
                base,
                "REJECTED_PAYMENT_NOT_SETTLED",
                str(consequence.get("payment_status", "")),
            )
        if _norm_addr(consequence.get("adapter_caller", "")) != self.meta.get("adapter", ""):
            return self._refusal(
                base,
                "REJECTED_WRONG_ADAPTER",
                _norm_addr(consequence.get("adapter_caller", "")),
            )

        payment_id = consequence.get("payment_id", "")
        if not _valid_id(payment_id):
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "invalid-payment-id")
        try:
            payment = _as_dict(core.view().get_payment(payment_id))
            account_id = (payment or {}).get("account_id", "")
            account = _as_dict(core.view().get_account(account_id)) if account_id else None
        except Exception as exc:
            return self._refusal(base, "REJECTED_CORE_UNAVAILABLE", str(exc)[:200])
        if payment is None or account is None:
            return self._refusal(base, "UNDETERMINED_DEPENDENCY", "payment-or-account-not-object")

        if payment.get("payment_id") != payment_id:
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "payment-id-mismatch")
        if payment.get("proposal_id") != consequence_id:
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "payment-proposal-mismatch")
        if payment.get("decision_id") != consequence.get("decision_id"):
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "payment-decision-mismatch")
        if payment.get("status") != "SETTLED":
            return self._refusal(
                base,
                "REJECTED_PAYMENT_NOT_SETTLED",
                str(payment.get("status", "")),
            )
        if _norm_addr(payment.get("to", "")) != _norm_addr(consequence.get("requested_recipient", "")):
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "recipient-mismatch")
        if str(payment.get("amount", "")) != str(consequence.get("requested_amount", "")):
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "amount-mismatch")
        if payment.get("actor") != "adapter:" + self.meta.get("adapter", ""):
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "actor-mismatch")
        if payment.get("memo") != "proposal:" + consequence_id:
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "memo-mismatch")
        if payment.get("account_id") != account.get("account_id"):
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "account-mismatch")

        if account.get("status") != "ACTIVE":
            return self._refusal(
                base,
                "REJECTED_ACCOUNT_NOT_ACTIVE",
                str(account.get("status", "")),
            )
        rules = account.get("rules", {})
        if not isinstance(rules, dict):
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "rules-not-object")
        currency = rules.get("currency")
        if currency != NATIVE_CURRENCY:
            return self._refusal(base, "REJECTED_CURRENCY_MISMATCH", str(currency))
        policy_version = consequence.get("policy_version", "")
        if rules.get("policy_version") and rules.get("policy_version") != policy_version:
            return self._refusal(base, "REJECTED_POLICY_VERSION", str(rules.get("policy_version")))

        amount_text = str(consequence.get("requested_amount", ""))
        if not amount_text.isdigit() or int(amount_text) <= 0:
            return self._refusal(base, "REJECTED_INVALID_AMOUNT", amount_text)
        recipient = consequence.get("requested_recipient", "")
        if not _valid_addr(recipient) or _norm_addr(recipient) == ZERO_ADDRESS:
            return self._refusal(base, "REJECTED_INVALID_RECIPIENT", str(recipient))

        try:
            created_at = _ts(consequence.get("created_at", ""))
        except Exception:
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "invalid-created_at")
        if created_at <= 0:
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "invalid-created_at")

        snapshot = {
            "proposal_id": consequence_id,
            "payment_id": payment_id,
            "decision_id": consequence.get("decision_id", ""),
            "adapter_caller": _norm_addr(consequence.get("adapter_caller", "")),
            "currency": currency,
            "recipient": _norm_addr(recipient),
            "amount": amount_text,
            "policy_version": policy_version,
            "core_created_at": consequence.get("created_at", ""),
            "payment_actor": payment.get("actor", ""),
            "payment_memo": payment.get("memo", ""),
        }
        base.update(
            {
                "recipient": _norm_addr(recipient),
                "amount": amount_text,
                "payment_id": payment_id,
                "decision_id": consequence.get("decision_id", ""),
                "adapter_caller": _norm_addr(consequence.get("adapter_caller", "")),
                "policy_version": policy_version,
                "core_created_at": consequence.get("created_at", ""),
                "core_snapshot_hash": "sha256:" + _sha(json.dumps(snapshot, sort_keys=True)),
            }
        )
        base["status"] = "AUTHORIZED"
        base["reason_code"] = ""
        return base

    @gl.public.view
    def preview_authorization(self, consequence_id: str, ttl_seconds: str) -> typing.Any:
        ttl = _positive_uint(ttl_seconds)
        if ttl is None:
            return self._refusal(
                {
                    "consequence_id": consequence_id,
                    "currency": NATIVE_CURRENCY,
                    "recipient": "",
                    "amount": "0",
                },
                "REJECTED_INVALID_TTL",
            )
        if self._paused():
            return self._refusal(
                {
                    "consequence_id": consequence_id,
                    "currency": NATIVE_CURRENCY,
                    "recipient": "",
                    "amount": "0",
                },
                "REJECTED_VAULT_PAUSED",
            )
        return self._evaluate(consequence_id, ttl)

    @gl.public.write
    def authorize(self, consequence_id: str, ttl_seconds: str) -> typing.Any:
        self._assert_owner()
        ttl = _positive_uint(ttl_seconds)
        if ttl is None or ttl > self._max_ttl():
            return {"status": "REJECTED", "reason_code": "REJECTED_INVALID_TTL"}
        if self._paused():
            return {"status": "REJECTED", "reason_code": "REJECTED_VAULT_PAUSED"}

        prior = self._get_intent(consequence_id)
        if prior:
            status = prior.get("status")
            if status == "AUTHORIZED":
                return {"status": "REJECTED", "reason_code": "REJECTED_REPLAY"}
            if status == "PENDING_FINALITY":
                return {"status": "REJECTED", "reason_code": "REJECTED_ALREADY_EMITTED"}
            if status == "EXPIRED":
                return {"status": "REJECTED", "reason_code": "REJECTED_INTENT_EXPIRED"}

        plan = self._evaluate(consequence_id, ttl)
        if plan.get("status") != "AUTHORIZED":
            record = dict(plan)
            record["attempts"] = 1
            record["last_attempt_at"] = _now_iso()
            self.intents[consequence_id] = json.dumps(record)
            return record

        now_iso = _now_iso()
        record = {
            "consequence_id": consequence_id,
            "proposal_id": consequence_id,
            "payment_id": plan.get("payment_id", ""),
            "decision_id": plan.get("decision_id", ""),
            "adapter_caller": plan.get("adapter_caller", ""),
            "recipient": plan.get("recipient", ""),
            "amount": plan.get("amount", "0"),
            "currency": NATIVE_CURRENCY,
            "policy_version": plan.get("policy_version", ""),
            "core_created_at": plan.get("core_created_at", ""),
            "core_snapshot_hash": plan.get("core_snapshot_hash", ""),
            "status": "AUTHORIZED",
            "execution": "NONE",
            "authorized_at": now_iso,
            "expires_at": plan.get("expires_at", ""),
            "attempts": 0,
            "last_reason_code": "",
            "last_attempt_at": "",
            "settler": "",
            "settled_at": "",
            "vault_before": "",
            "vault_after": "",
            "transfer_seq": "",
        }
        self.intents[consequence_id] = json.dumps(record)
        return record

    def _settlement_checks(self, consequence_id, recipient, amount, mutate):
        base = {
            "consequence_id": consequence_id,
            "status": "NONE",
            "reason_code": "",
        }
        if self._paused():
            return self._refusal(base, "REJECTED_VAULT_PAUSED")
        intent = self._get_intent(consequence_id)
        if not intent:
            return self._refusal(base, "REJECTED_INTENT_NOT_FOUND")
        if intent.get("status") == "PENDING_FINALITY":
            return self._refusal(base, "REJECTED_ALREADY_EMITTED")
        if intent.get("status") == "EXPIRED":
            return self._refusal(base, "REJECTED_INTENT_EXPIRED")
        if intent.get("status") != "AUTHORIZED":
            return self._refusal(base, "REJECTED_INTENT_NOT_FOUND", str(intent.get("status", "")))

        if not _valid_addr(recipient):
            return self._refusal(base, "REJECTED_INVALID_RECIPIENT", str(recipient))
        if _norm_addr(recipient) != intent.get("recipient"):
            return self._refusal(base, "REJECTED_RECIPIENT_MISMATCH", _norm_addr(recipient))
        amount_text = str(amount)
        if not amount_text.isdigit() or int(amount_text) <= 0:
            return self._refusal(base, "REJECTED_INVALID_AMOUNT", amount_text)
        if amount_text != intent.get("amount"):
            return self._refusal(base, "REJECTED_AMOUNT_MISMATCH", amount_text)

        try:
            now = _ts(_now_iso())
            expires_at = _ts(intent.get("expires_at", ""))
        except Exception:
            return self._refusal(base, "REJECTED_INTENT_EXPIRED", "invalid-expiry")
        if now >= expires_at:
            if mutate:
                intent["status"] = "EXPIRED"
                intent["execution"] = "EXPIRED"
                self.intents[consequence_id] = json.dumps(intent)
            return self._refusal(base, "REJECTED_INTENT_EXPIRED")

        plan = self._evaluate(consequence_id, self._max_ttl())
        if plan.get("status") != "AUTHORIZED":
            if mutate:
                intent["attempts"] = int(intent.get("attempts", 0)) + 1
                intent["last_reason_code"] = "REJECTED_CORE_BINDING"
                intent["last_attempt_at"] = _now_iso()
                self.intents[consequence_id] = json.dumps(intent)
            return self._refusal(base, "REJECTED_CORE_BINDING", plan.get("reason_code", ""))
        if plan.get("recipient") != intent.get("recipient") or plan.get("amount") != intent.get("amount"):
            if mutate:
                intent["attempts"] = int(intent.get("attempts", 0)) + 1
                intent["last_reason_code"] = "REJECTED_CORE_BINDING"
                intent["last_attempt_at"] = _now_iso()
                self.intents[consequence_id] = json.dumps(intent)
            return self._refusal(base, "REJECTED_CORE_BINDING", "core-intent-mismatch")

        if int(self.balance) < int(intent.get("amount", "0")):
            return self._refusal(base, "REJECTED_INSUFFICIENT_CUSTODY")

        return {
            "status": "SETTLEABLE",
            "reason_code": "",
            "intent": intent,
            "plan": plan,
        }

    @gl.public.view
    def preview_settlement(self, consequence_id: str, recipient: str, amount: str) -> typing.Any:
        result = self._settlement_checks(consequence_id, recipient, amount, False)
        if result.get("status") == "SETTLEABLE":
            return {
                "status": "SETTLEABLE",
                "reason_code": "",
                "consequence_id": consequence_id,
                "recipient": result["intent"].get("recipient", ""),
                "amount": result["intent"].get("amount", "0"),
                "expires_at": result["intent"].get("expires_at", ""),
                "core_snapshot_hash": result["intent"].get("core_snapshot_hash", ""),
                "vault_balance": str(int(self.balance)),
            }
        return result

    @gl.public.write
    def settle(self, consequence_id: str, recipient: str, amount: str) -> typing.Any:
        self._assert_initialized()
        result = self._settlement_checks(consequence_id, recipient, amount, True)
        if result.get("status") != "SETTLEABLE":
            return result

        intent = result["intent"]
        plan = result["plan"]
        if plan.get("core_snapshot_hash") != intent.get("core_snapshot_hash"):
            intent["attempts"] = int(intent.get("attempts", 0)) + 1
            intent["last_reason_code"] = "REJECTED_CORE_BINDING"
            intent["last_attempt_at"] = _now_iso()
            self.intents[consequence_id] = json.dumps(intent)
            return {"status": "REJECTED", "reason_code": "REJECTED_CORE_BINDING", "detail": "snapshot-drift"}

        before = int(self.balance)
        seq = self._next_seq("next_settlement")
        intent["status"] = "PENDING_FINALITY"
        intent["execution"] = "PENDING_FINALITY"
        intent["attempts"] = int(intent.get("attempts", 0)) + 1
        intent["last_reason_code"] = ""
        intent["last_attempt_at"] = _now_iso()
        intent["settler"] = self._sender()
        intent["settled_at"] = _now_iso()
        intent["vault_before"] = str(before)
        intent["transfer_seq"] = str(seq)
        self.intents[consequence_id] = json.dumps(intent)
        self._set_total("total_emitted", self._total("total_emitted") + int(intent["amount"]))

        gl.chain.Account(Address("0x" + intent["recipient"])).emit_transfer(
            value=u256(int(intent["amount"])),
            on="finalized",
        )

        intent["vault_after"] = str(int(self.balance))
        self.intents[consequence_id] = json.dumps(intent)
        return intent

    @gl.public.write.payable
    def __on_errored_message__(self) -> typing.Any:
        self._assert_initialized()
        value = int(gl.message.value)
        seq = self._next_seq("next_refund")
        record = {
            "seq": str(seq),
            "amount": str(value),
            "balance_after": str(int(self.balance)),
            "at": _now_iso(),
        }
        self.refunds[str(seq)] = json.dumps(record)
        if value > 0:
            self._set_total("total_refunded", self._total("total_refunded") + value)
        return record

    @gl.public.write
    def set_paused(self, paused: bool) -> typing.Any:
        self._assert_owner()
        self.meta["paused"] = "1" if paused else "0"
        return {"status": "PAUSED" if paused else "UNPAUSED", "paused": bool(paused)}

    @gl.public.write
    def pause(self) -> typing.Any:
        self._assert_owner()
        self.meta["paused"] = "1"
        return {"status": "PAUSED", "paused": True}

    @gl.public.write
    def unpause(self) -> typing.Any:
        self._assert_owner()
        self.meta["paused"] = "0"
        return {"status": "UNPAUSED", "paused": False}

    @gl.public.write
    def set_max_ttl(self, ttl_seconds: str) -> typing.Any:
        self._assert_owner()
        ttl = _positive_uint(ttl_seconds)
        if ttl is None or ttl > MAX_TTL:
            return {"status": "REJECTED", "reason_code": "REJECTED_INVALID_TTL"}
        self.meta["max_ttl"] = str(ttl)
        return {"status": "TTL_UPDATED", "max_ttl": str(ttl)}

    @gl.public.view
    def get_intent(self, consequence_id: str) -> typing.Any:
        intent = self._get_intent(consequence_id)
        if intent is None:
            return {"consequence_id": consequence_id, "status": "NONE"}
        return intent

    @gl.public.view
    def get_config(self) -> typing.Any:
        return {
            "owner": self.meta.get("owner", ""),
            "core": self.meta.get("core", ""),
            "adapter": self.meta.get("adapter", ""),
            "currency": self.meta.get("currency", NATIVE_CURRENCY),
            "max_ttl": self.meta.get("max_ttl", "0"),
            "paused": self._paused(),
            "self": self.meta.get("self", ""),
            "created": self.meta.get("created", ""),
            "total_deposited": self.meta.get("total_deposited", "0"),
            "total_emitted": self.meta.get("total_emitted", "0"),
            "total_refunded": self.meta.get("total_refunded", "0"),
        }

    @gl.public.view
    def get_balance(self) -> typing.Any:
        balance = int(self.balance)
        expected = self._total("total_deposited") - self._total("total_emitted") + self._total("total_refunded")
        return {
            "balance": str(balance),
            "total_deposited": str(self._total("total_deposited")),
            "total_emitted": str(self._total("total_emitted")),
            "total_refunded": str(self._total("total_refunded")),
            "expected_balance": str(expected),
            "reconciled": balance == expected,
        }

    @gl.public.view
    def get_deposit(self, seq: str) -> typing.Any:
        raw = self.deposits.get(str(seq))
        if not raw:
            return {"seq": str(seq), "status": "NONE"}
        return json.loads(raw)

    @gl.public.view
    def get_refund(self, seq: str) -> typing.Any:
        raw = self.refunds.get(str(seq))
        if not raw:
            return {"seq": str(seq), "status": "NONE"}
        return json.loads(raw)
