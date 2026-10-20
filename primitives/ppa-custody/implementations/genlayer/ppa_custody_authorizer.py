# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
"""PPA Custody Authorizer (GenLayer) v0.1 — IMPLEMENTING.

Deterministic bridge from an EXECUTED PPA Core consequence to an EVM custody
intent. It contains no LLM/web/nondeterministic operation. The only side effect
is an `EthSend` to the configured custody vault, and only after the exact Core
binding and vault configuration checks pass.

Authority:
  PPA Core consequence/payment/account
    -> this contract (read + deterministic revalidation)
    -> vault.authorize(exact proposal/token/recipient/amount/expiry)
    -> permissionless vault.settle(exact fields)

The authorizer holds no tokens, cannot change Core state, and does not adjudicate.
"""

import datetime
import hashlib
import json
import typing

from genlayer import *
import genlayer.gl as gl


MAX_TTL = 604800


def _now_iso():
    dt = getattr(gl.message, "datetime", None)
    if dt:
        return dt
    return gl.message_raw["datetime"]


def _ts(iso):
    txt = iso.strip().replace("Z", "+00:00")
    return int(datetime.datetime.fromisoformat(txt).timestamp())


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _norm_addr(value):
    if not isinstance(value, str):
        return ""
    return value.lower().removeprefix("0x")


def _valid_addr(value):
    if not isinstance(value, str):
        return False
    if len(value) != 42 or not value.startswith("0x"):
        return False
    try:
        int(value[2:], 16)
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


@gl.evm.contract_interface
class CustodyVault:
    class View:
        def paused(self, /) -> bool: ...

        def allowedTokens(self, token: Address, /) -> bool: ...

    class Write:
        def authorize(
            self,
            proposal_id: str,
            token: Address,
            recipient: Address,
            amount: u256,
            expires_at: u256,
            /,
        ) -> None: ...


class PPACustodyAuthorizer(gl.Contract):
    meta: TreeMap[str, str]
    assets: TreeMap[str, str]
    authorizations: TreeMap[str, str]

    def __init__(self) -> None:
        pass

    @gl.public.write
    def initialize(
        self,
        owner: str,
        core_address: str,
        adapter_address: str,
        vault_address: str,
        token_address: str,
        currency: str,
        max_ttl_seconds: str,
    ) -> typing.Any:
        if self.meta.get("owner"):
            raise ValueError("Custody: already initialized")
        for value in (owner, core_address, adapter_address, vault_address, token_address):
            if not _valid_addr(value):
                raise ValueError("Custody: invalid address")
        if not isinstance(currency, str) or not currency.strip():
            raise ValueError("Custody: currency required")
        ttl = _positive_uint(max_ttl_seconds)
        if ttl is None or ttl > MAX_TTL:
            raise ValueError("Custody: invalid max_ttl_seconds")

        self.meta["owner"] = _norm_addr(owner)
        self.meta["core"] = _norm_addr(core_address)
        self.meta["adapter"] = _norm_addr(adapter_address)
        self.meta["vault"] = _norm_addr(vault_address)
        self.meta["currency"] = currency
        self.meta["token"] = _norm_addr(token_address)
        self.meta["max_ttl"] = str(ttl)
        self.meta["paused"] = "0"
        self.meta["created"] = _now_iso()
        self.meta["self"] = self._own_address()
        self.assets[currency] = _norm_addr(token_address)
        return {
            "status": "INITIALIZED",
            "core": self.meta["core"],
            "adapter": self.meta["adapter"],
            "vault": self.meta["vault"],
            "currency": currency,
            "token": self.meta["token"],
            "max_ttl": str(ttl),
        }

    def _sender(self):
        return gl.message.sender_address.as_hex.lower().removeprefix("0x")

    def _own_address(self):
        try:
            ca = gl.message.contract_address
            if isinstance(ca, (bytes, bytearray)):
                return bytes(ca).hex()
            h = ca.as_hex if hasattr(ca, "as_hex") else str(ca)
            return h.lower().removeprefix("0x")
        except Exception:
            return ""

    def _assert_owner(self):
        if self._sender() != self.meta.get("owner"):
            raise ValueError("Custody: caller is not owner")

    def _max_ttl(self):
        try:
            return int(self.meta.get("max_ttl", "0"))
        except Exception:
            return 0

    @gl.public.write
    def register_asset(self, currency: str, token_address: str) -> typing.Any:
        self._assert_owner()
        if not isinstance(currency, str) or not currency.strip():
            raise ValueError("Custody: currency required")
        if not _valid_addr(token_address):
            raise ValueError("Custody: invalid token address")
        existing = self.assets.get(currency)
        if existing and _norm_addr(existing) != _norm_addr(token_address):
            raise ValueError("Custody: asset already registered")
        self.assets[currency] = _norm_addr(token_address)
        return {"status": "REGISTERED", "currency": currency, "token": _norm_addr(token_address)}

    @gl.public.write
    def set_max_ttl(self, ttl_seconds: str) -> typing.Any:
        self._assert_owner()
        ttl = _positive_uint(ttl_seconds)
        if ttl is None or ttl > MAX_TTL:
            raise ValueError("Custody: invalid max_ttl_seconds")
        self.meta["max_ttl"] = str(ttl)
        return {"status": "TTL_UPDATED", "max_ttl": str(ttl)}

    @gl.public.write
    def set_paused(self, paused: bool) -> typing.Any:
        self._assert_owner()
        self.meta["paused"] = "1" if paused else "0"
        return {"status": "PAUSED" if paused else "UNPAUSED", "paused": paused}

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

    @gl.public.view
    def get_config(self) -> typing.Any:
        return {
            "owner": self.meta.get("owner", ""),
            "core": self.meta.get("core", ""),
            "adapter": self.meta.get("adapter", ""),
            "vault": self.meta.get("vault", ""),
            "currency": self.meta.get("currency", ""),
            "token": self.meta.get("token", ""),
            "max_ttl": self.meta.get("max_ttl", "0"),
            "paused": self.meta.get("paused") == "1",
            "self": self.meta.get("self", ""),
            "created": self.meta.get("created", ""),
        }

    @gl.public.view
    def get_asset(self, currency: str) -> typing.Any:
        token = self.assets.get(currency)
        if not token:
            raise ValueError("Custody: unknown asset")
        return {"currency": currency, "token": token}

    @gl.public.view
    def get_authorization(self, proposal_id: str) -> typing.Any:
        raw = self.authorizations.get(proposal_id)
        if not raw:
            return {"proposal_id": proposal_id, "status": "NONE"}
        return json.loads(raw)

    def _refusal(self, base, reason, detail=""):
        record = dict(base)
        record["status"] = "UNDETERMINED" if reason.startswith("UNDETERMINED_") else "REJECTED"
        record["reason_code"] = reason
        if detail:
            record["detail"] = detail
        return record

    def _evaluate(self, proposal_id, ttl_seconds):
        now_iso = _now_iso()
        try:
            now = _ts(now_iso)
        except Exception:
            now = 0
        base = {
            "proposal_id": proposal_id,
            "currency": self.meta.get("currency", ""),
            "token": self.meta.get("token", ""),
            "recipient": "",
            "amount": "0",
            "evaluated_at": now_iso,
            "expires_at": str(now + ttl_seconds),
        }
        if not _valid_id(proposal_id):
            return self._refusal(base, "REJECTED_INVALID_PROPOSAL_ID")
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
            consequence = _as_dict(core.view().get_consequence(proposal_id))
        except Exception as exc:
            message = str(exc).lower()
            if "no consequence" in message or "not found" in message:
                return self._refusal(base, "REJECTED_NO_CONSEQUENCE", str(exc)[:200])
            return self._refusal(base, "REJECTED_CORE_UNAVAILABLE", str(exc)[:200])
        if consequence is None:
            return self._refusal(base, "UNDETERMINED_DEPENDENCY", "consequence-not-object")

        if consequence.get("proposal_id") != proposal_id:
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "consequence-proposal-mismatch")
        if consequence.get("status") != "EXECUTED" or consequence.get("reason_code") != "EXECUTED":
            return self._refusal(base, "REJECTED_CONSEQUENCE_NOT_EXECUTED", str(consequence.get("status", "")))
        if consequence.get("payment_status") != "SETTLED":
            return self._refusal(base, "REJECTED_PAYMENT_NOT_SETTLED", str(consequence.get("payment_status", "")))
        if _norm_addr(consequence.get("adapter_caller", "")) != self.meta.get("adapter", ""):
            return self._refusal(base, "REJECTED_WRONG_ADAPTER", _norm_addr(consequence.get("adapter_caller", "")))

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
        if payment.get("proposal_id") != proposal_id:
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "payment-proposal-mismatch")
        if payment.get("decision_id") != consequence.get("decision_id"):
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "payment-decision-mismatch")
        if payment.get("status") != "SETTLED":
            return self._refusal(base, "REJECTED_PAYMENT_NOT_SETTLED", str(payment.get("status", "")))
        if _norm_addr(payment.get("to", "")) != _norm_addr(consequence.get("requested_recipient", "")):
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "recipient-mismatch")
        if str(payment.get("amount", "")) != str(consequence.get("requested_amount", "")):
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "amount-mismatch")
        if payment.get("actor") != "adapter:" + self.meta.get("adapter", ""):
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "actor-mismatch")
        if payment.get("memo") != "proposal:" + proposal_id:
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "memo-mismatch")
        if payment.get("account_id") != account.get("account_id"):
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "account-mismatch")

        if account.get("status") != "ACTIVE":
            return self._refusal(base, "REJECTED_ACCOUNT_NOT_ACTIVE", str(account.get("status", "")))
        rules = account.get("rules", {})
        if not isinstance(rules, dict):
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "rules-not-object")
        currency = rules.get("currency")
        if currency != self.meta.get("currency"):
            return self._refusal(base, "REJECTED_CURRENCY_MISMATCH", str(currency))
        policy_version = consequence.get("policy_version", "")
        if rules.get("policy_version") and rules.get("policy_version") != policy_version:
            return self._refusal(base, "REJECTED_POLICY_VERSION", str(rules.get("policy_version")))
        token = self.assets.get(currency)
        if not token:
            return self._refusal(base, "REJECTED_UNKNOWN_ASSET", str(currency))

        amount_text = str(consequence.get("requested_amount", ""))
        if not amount_text.isdigit() or int(amount_text) <= 0:
            return self._refusal(base, "REJECTED_AMOUNT", amount_text)
        recipient = consequence.get("requested_recipient", "")
        if not _valid_addr(recipient) or _norm_addr(recipient) == "0" * 40:
            return self._refusal(base, "REJECTED_RECIPIENT", str(recipient))

        try:
            created_at = _ts(consequence.get("created_at", ""))
        except Exception:
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "invalid-created_at")
        if created_at <= 0:
            return self._refusal(base, "REJECTED_PAYMENT_BINDING", "invalid-created_at")

        base.update(
            {
                "currency": currency,
                "token": token,
                "recipient": recipient,
                "amount": amount_text,
                "payment_id": payment_id,
                "decision_id": consequence.get("decision_id", ""),
                "adapter_caller": _norm_addr(consequence.get("adapter_caller", "")),
                "core_created_at": consequence.get("created_at", ""),
                "expires_at": str(now + ttl_seconds),
            }
        )
        snapshot = {
            "proposal_id": proposal_id,
            "payment_id": payment_id,
            "decision_id": consequence.get("decision_id", ""),
            "adapter_caller": _norm_addr(consequence.get("adapter_caller", "")),
            "currency": currency,
            "token": token,
            "recipient": recipient,
            "amount": amount_text,
            "policy_version": policy_version,
            "core_created_at": consequence.get("created_at", ""),
            "payment_actor": payment.get("actor", ""),
            "payment_memo": payment.get("memo", ""),
        }
        base["core_snapshot_hash"] = "sha256:" + _sha(json.dumps(snapshot, sort_keys=True))
        base["status"] = "AUTHORIZED"
        base["reason_code"] = ""
        return base

    @gl.public.view
    def preview_authorization(self, proposal_id: str) -> typing.Any:
        return self._evaluate(proposal_id, self._max_ttl())

    def _persist_refusal(self, proposal_id, reason, plan=None, detail=""):
        prior_raw = self.authorizations.get(proposal_id)
        attempts = 1
        if prior_raw:
            try:
                attempts = int(json.loads(prior_raw).get("attempts", 0)) + 1
            except Exception:
                attempts = 1
        record = dict(plan or {})
        record["proposal_id"] = proposal_id
        record["status"] = "UNDETERMINED" if reason.startswith("UNDETERMINED_") else "REJECTED"
        record["reason_code"] = reason
        record["attempts"] = attempts
        record["recorded_at"] = _now_iso()
        if detail:
            record["detail"] = detail
        self.authorizations[proposal_id] = json.dumps(record)
        return {
            "proposal_id": proposal_id,
            "status": record["status"],
            "reason_code": reason,
            "attempts": attempts,
            "detail": detail,
        }

    @gl.public.write
    def authorize_settlement(self, proposal_id: str, ttl_seconds: str) -> typing.Any:
        self._assert_owner()
        ttl = _positive_uint(ttl_seconds)
        if ttl is None or ttl > self._max_ttl():
            return self._persist_refusal(proposal_id, "REJECTED_INVALID_TTL")
        if self.meta.get("paused") == "1":
            return self._persist_refusal(proposal_id, "REJECTED_AUTHORIZER_PAUSED")

        prior_raw = self.authorizations.get(proposal_id)
        if prior_raw:
            try:
                prior = json.loads(prior_raw)
            except Exception:
                prior = {}
            if prior.get("status") in ("AUTHORIZED", "SETTLED"):
                return {
                    "proposal_id": proposal_id,
                    "status": "REJECTED",
                    "reason_code": "REJECTED_REPLAY",
                    "attempts": prior.get("attempts", 1),
                }

        plan = self._evaluate(proposal_id, ttl)
        if plan.get("status") != "AUTHORIZED":
            return self._persist_refusal(proposal_id, plan.get("reason_code", "REJECTED_CORE_UNAVAILABLE"), plan, plan.get("detail", ""))

        vault_hex = self.meta.get("vault", "")
        token_hex = plan.get("token", "")
        try:
            expires_at = int(plan["expires_at"])
            vault = CustodyVault(Address("0x" + vault_hex))
            vault.emit().authorize(
                proposal_id,
                Address("0x" + token_hex),
                Address(plan["recipient"]),
                u256(int(plan["amount"])),
                u256(expires_at),
            )
        except Exception as exc:
            return self._persist_refusal(proposal_id, "REJECTED_EVM_AUTHORIZE_FAILED", plan, str(exc)[:200])

        prior_attempts = 0
        if prior_raw:
            try:
                prior_attempts = int(json.loads(prior_raw).get("attempts", 0))
            except Exception:
                prior_attempts = 0
        record = dict(plan)
        record["status"] = "AUTHORIZED"
        record["reason_code"] = ""
        record["execution"] = "PENDING_FINALITY"
        record["authorized_at"] = _now_iso()
        record["attempts"] = prior_attempts + 1
        self.authorizations[proposal_id] = json.dumps(record)
        return {
            "proposal_id": proposal_id,
            "status": "AUTHORIZED",
            "reason_code": "",
            "token": token_hex,
            "recipient": plan["recipient"],
            "amount": plan["amount"],
            "expires_at": plan["expires_at"],
            "execution": "PENDING_FINALITY",
            "attempts": record["attempts"],
        }
