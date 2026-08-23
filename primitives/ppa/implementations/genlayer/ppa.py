# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
"""Programmable Payment Account (PPA) v0.1 — GenLayer Intelligent Contract.

The user-facing composite over the Nomos financial primitive stack. A PPA is
an account that holds committed capital and moves it only through
deterministic, rule-gated payment flows.

Composition (every money path routes through existing primitive semantics):

    create_account()   -> registers policy (limits/allowlist/attestation)
    deposit()          -> capital-commitment pattern (internal ledger)
    send()             -> policy gate + encumbrance + payable claim + settle
    issue/settle_invoice() -> structured receivable paid through send() gates
    dispute/resolve    -> gaia-pattern case lifecycle on a payment
    delegate()/revoke()-> scoped spending authority (daa/dal pattern)

JUDGMENT BOUNDARY: NONE for the v0.1 canonical slice. Every decision that
moves value is deterministic rule evaluation. (LLM judgment enters only in
upstream monitoring/dispute classification, composed separately.)

v0.1 note: primitive semantics are embedded in-account (single-contract
deployment for testnet simplicity). The state machines mirror the canonical
primitives 1:1; extraction into separate contracts with cross-calls is the
v0.2 step once Bradbury cross-contract calls are verified.
"""

import json
import typing

from genlayer import *


def _now_iso() -> str:
    """Transaction timestamp as ISO string."""
    dt = getattr(gl.message, "datetime", None)
    if dt:
        return dt
    return gl.message_raw["datetime"]


def _valid_addr(a: str) -> bool:
    return isinstance(a, str) and a.startswith("0x") and len(a) == 42


def _valid_id(i) -> bool:
    return isinstance(i, str) and 0 < len(i) <= 64


class ProgrammablePaymentAccount(gl.Contract):
    meta: TreeMap[str, str]         # "owner" / "created" -> value
    accounts: TreeMap[str, str]     # account_id -> json record
    payments: TreeMap[str, str]     # payment_id -> json record
    invoices: TreeMap[str, str]     # invoice_id -> json record
    delegations: TreeMap[str, str]  # delegation_id -> json record
    disputes: TreeMap[str, str]     # dispute_id -> json record

    def __init__(self) -> None:
        pass

    @gl.public.write
    def initialize(self, owner: str) -> str:
        """One-time owner registration. Owner is the account controller."""
        if self.meta.get("owner"):
            raise ValueError("PPA: already initialized")
        if not _valid_addr(owner):
            raise ValueError("PPA: invalid owner address")
        self.meta["owner"] = self._norm(owner)
        self.meta["created"] = _now_iso()
        return "initialized"

    # ---------- authority ----------
    def _norm(self, a: str) -> str:
        return (a or "").lower().removeprefix("0x")

    def _sender(self) -> str:
        return gl.message.sender_address.as_hex.lower().removeprefix("0x")

    def _assert_owner(self) -> None:
        if self._sender() != self._norm(self.meta.get("owner")):
            raise ValueError("PPA: caller is not the account owner")

    def _resolve_actor(self, account_id: str = "") -> str:
        """Owner or an active delegated principal. Delegation narrows, never widens."""
        sender = self._sender()
        if sender == self._norm(self.meta.get("owner")):
            return "owner"
        now = int(_now_iso().replace("-", "").replace(":", "").replace("T", "").split(".")[0])
        keys = list(self.delegations.keys())
        for k in keys:
            d = json.loads(self.delegations[k])
            if d["principal"].lower().replace("0x", "") == sender:
                if d["status"] == "ACTIVE" and int(d["expires"]) >= now:
                    return "delegate:" + d["delegation_id"]
                if d["status"] == "ACTIVE":
                    d["status"] = "EXPIRED"
                    self.delegations[k] = json.dumps(d)
        raise ValueError("PPA: caller has no authority on this account")

    def _delegate_limits(self) -> tuple:
        """(per_tx_limit, daily_limit) for a delegator actor, else None."""
        sender = self._sender()
        now = int(_now_iso().replace("-", "").replace(":", "").replace("T", "").split(".")[0])
        for k in self.delegations.keys():
            d = json.loads(self.delegations[k])
            if d["principal"].lower().replace("0x", "") == sender and d["status"] == "ACTIVE" and int(d["expires"]) >= now:
                return int(d["per_tx_limit"]), int(d["daily_limit"])
        return None

    # ---------- accounts & rules ----------
    @gl.public.write
    def create_account(self, account_id: str, rules_json: str) -> str:
        """Open a sub-account under this PPA with a rules envelope."""
        self._assert_owner()
        if not _valid_id(account_id):
            raise ValueError("PPA: invalid account id")
        if self.accounts.get(account_id):
            raise ValueError("PPA: account id exists")
        rules = json.loads(rules_json)
        for req in ("daily_limit", "per_tx_limit", "currency"):
            if req not in rules:
                raise ValueError(f"PPA: rules missing {req}")
        rec = {
            "account_id": account_id,
            "rules": rules,
            "balance": "0",
            "committed": "0",
            "daily_spent": "0",
            "daily_window_start": _now_iso(),
            "status": "ACTIVE",
            "created": _now_iso(),
        }
        self.accounts[account_id] = json.dumps(rec)
        return "account_created"

    @gl.public.write
    def update_rules(self, account_id: str, rules_json: str) -> str:
        self._assert_owner()
        rec = self._get_account(account_id)
        rec["rules"] = json.loads(rules_json)
        self.accounts[account_id] = json.dumps(rec)
        return "rules_updated"

    @gl.public.view
    def get_account(self, account_id: str) -> typing.Any:
        return self._get_account(account_id)

    def _get_account(self, account_id: str) -> dict:
        raw = self.accounts.get(account_id)
        if not raw:
            raise ValueError("PPA: account not found")
        return json.loads(raw)

    # ---------- deposit / withdrawal ----------
    @gl.public.write
    def deposit(self, account_id: str, amount: str) -> str:
        """Credit the sub-account. In production this settles against an
        incoming proof-of-payable claim; v0.1 credits on authority check."""
        self._resolve_actor()
        rec = self._get_account(account_id)
        if rec["status"] != "ACTIVE":
            raise ValueError("PPA: account not active")
        if not amount.isdigit() or int(amount) <= 0:
            raise ValueError("PPA: invalid amount")
        rec["balance"] = str(int(rec["balance"]) + int(amount))
        self.accounts[account_id] = json.dumps(rec)
        return "deposited"

    @gl.public.write
    def withdraw(self, account_id: str, amount: str) -> str:
        """Owner-only withdrawal of uncommitted balance."""
        self._assert_owner()
        rec = self._get_account(account_id)
        available = int(rec["balance"]) - int(rec["committed"])
        if int(amount) > available:
            raise ValueError("PPA: insufficient uncommitted balance")
        rec["balance"] = str(int(rec["balance"]) - int(amount))
        self.accounts[account_id] = json.dumps(rec)
        return "withdrawn"

    # ---------- payments ----------
    @gl.public.write
    def send(self, account_id: str, payment_id: str, to: str, amount: str,
             evidence_hash: str = "", memo: str = "") -> typing.Any:
        """Core flow: policy gate -> encumbrance gate -> settle.
        DENY paths move no funds; the id stays consumable after rule change.

        Mirrors Nomos flow: policy-envelope.evaluate_request ->
        claim-encumbrance.reserve -> proof-of-payable open/attest/settle.
        """
        actor = self._resolve_actor()
        rec = self._get_account(account_id)
        if rec["status"] != "ACTIVE":
            raise ValueError("PPA: account not active")
        prior = self.payments.get(payment_id)
        if prior and json.loads(prior)["status"] != "DENIED":
            raise ValueError("PPA: payment id exists")
        if not _valid_addr(to):
            raise ValueError("PPA: invalid recipient")
        if not amount.isdigit() or int(amount) <= 0:
            raise ValueError("PPA: invalid amount")

        # --- 1. policy gate (policy-envelope semantics) ---
        rules = rec["rules"]
        allowlist = [a.lower().replace("0x", "") for a in rules.get("allowlist", [])]
        if allowlist and to.lower().replace("0x", "") not in allowlist:
            return self._deny(payment_id, account_id, "POLICY_DENYLIST")
        per_tx = int(rules["per_tx_limit"])
        if int(amount) > per_tx:
            return self._deny(payment_id, account_id, "POLICY_PER_TX_LIMIT")

        # delegation narrows: actor limits apply on top of account rules
        dl = self._delegate_limits()
        if dl is not None:
            d_per_tx, d_daily = dl
            if int(amount) > min(per_tx, d_per_tx):
                return self._deny(payment_id, account_id, "DELEGATE_PER_TX_LIMIT")

        daily = int(rules["daily_limit"])
        spent, window_start = self._roll_daily_window(rec)
        effective_daily = daily if dl is None else min(daily, dl[1])
        if spent + int(amount) > effective_daily:
            self.accounts[account_id] = json.dumps(rec)
            reason = "POLICY_DAILY_LIMIT" if dl is None else "DELEGATE_DAILY_LIMIT"
            return self._deny(payment_id, account_id, reason)

        # --- 2. encumbrance gate (claim-encumbrance semantics) ---
        available = int(rec["balance"]) - int(rec["committed"])
        if int(amount) > available:
            return self._deny(payment_id, account_id, "INSUFFICIENT_COMMITMENT")

        # --- 3+4. payable claim + settle (proof-of-payable semantics) ---
        rec["daily_spent"] = str(spent + int(amount))
        rec["balance"] = str(int(rec["balance"]) - int(amount))
        self.accounts[account_id] = json.dumps(rec)
        payment = {
            "payment_id": payment_id,
            "account_id": account_id,
            "to": to,
            "amount": amount,
            "evidence_hash": evidence_hash,
            "memo": memo,
            "actor": actor,
            "status": "SETTLED",
            "created": _now_iso(),
        }
        self.payments[payment_id] = json.dumps(payment)
        return {"success": True, "status": "SETTLED", "payment_id": payment_id,
                "amount": amount, "to": to}

    @gl.public.view
    def get_payment(self, payment_id: str) -> typing.Any:
        raw = self.payments.get(payment_id)
        if not raw:
            raise ValueError("PPA: payment not found")
        return json.loads(raw)

    def _deny(self, payment_id: str, account_id: str, reason: str) -> dict:
        """Denied requests are recorded (auditable), burn nothing, and do not
        consume the payment id (retry allowed after rule change)."""
        self.payments[payment_id] = json.dumps({
            "payment_id": payment_id, "account_id": account_id,
            "status": "DENIED", "reason": reason,
            "created": _now_iso(),
        })
        return {"success": False, "status": "DENIED", "reason": reason}

    def _roll_daily_window(self, rec: dict) -> tuple:
        now = int(_now_iso().replace("-", "").replace(":", "").replace("T", "").split(".")[0])
        start = int(rec["daily_window_start"].replace("-", "").replace(":", "").replace("T", "").split(".")[0])
        if now - start >= 86400:
            rec["daily_spent"] = "0"
            rec["daily_window_start"] = _now_iso()
            return 0, now
        return int(rec["daily_spent"]), start

    # ---------- invoices ----------
    @gl.public.write
    def issue_invoice(self, invoice_id: str, payer: str, amount: str,
                      items_json: str, due: str = "") -> str:
        """Structured receivable: a claim awaiting payer settlement."""
        self._resolve_actor()
        if not _valid_id(invoice_id) or self.invoices.get(invoice_id):
            raise ValueError("PPA: invalid or duplicate invoice id")
        if not _valid_addr(payer):
            raise ValueError("PPA: invalid payer")
        inv = {
            "invoice_id": invoice_id, "payer": payer, "amount": amount,
            "items": json.loads(items_json), "due": due,
            "status": "OPEN", "created": _now_iso(),
        }
        self.invoices[invoice_id] = json.dumps(inv)
        return "invoice_issued"

    @gl.public.write
    def settle_invoice(self, invoice_id: str, from_account_id: str) -> typing.Any:
        """Pay an invoice through the normal send() gates."""
        self._resolve_actor()
        raw = self.invoices.get(invoice_id)
        if not raw:
            raise ValueError("PPA: invoice not found")
        inv = json.loads(raw)
        if inv["status"] != "OPEN":
            raise ValueError("PPA: invoice not open")
        result = self.send(from_account_id, f"pay-{invoice_id}",
                           inv["payer"], inv["amount"],
                           evidence_hash=inv["invoice_id"], memo="invoice")
        if result.get("success"):
            inv["status"] = "SETTLED"
            inv["payment_id"] = f"pay-{invoice_id}"
            self.invoices[invoice_id] = json.dumps(inv)
        return result

    @gl.public.view
    def get_invoice(self, invoice_id: str) -> typing.Any:
        raw = self.invoices.get(invoice_id)
        if not raw:
            raise ValueError("PPA: invoice not found")
        return json.loads(raw)

    # ---------- disputes (gaia semantics) ----------
    @gl.public.write
    def dispute_payment(self, dispute_id: str, payment_id: str,
                        category: str, facts_json: str) -> str:
        """Open a dispute case on a settled payment (gaia pattern)."""
        self._resolve_actor()
        pay_raw = self.payments.get(payment_id)
        if not pay_raw:
            raise ValueError("PPA: payment not found")
        pay = json.loads(pay_raw)
        if pay["status"] != "SETTLED":
            raise ValueError("PPA: can only dispute settled payments")
        allowed = ("settlement-mismatch", "delivery-mismatch",
                   "unauthorized-payment", "amount-mismatch", "duplicate")
        if category not in allowed:
            raise ValueError("PPA: unknown dispute category")
        if self.disputes.get(dispute_id):
            raise ValueError("PPA: dispute id exists")
        case = {
            "dispute_id": dispute_id, "payment_id": payment_id,
            "category": category, "facts": json.loads(facts_json),
            "status": "OPEN", "remedy": None,
            "created": _now_iso(),
        }
        self.disputes[dispute_id] = json.dumps(case)
        return "dispute_opened"

    @gl.public.write
    def resolve_dispute(self, dispute_id: str, remedy: str) -> str:
        """Owner resolves: refund | waive | reject. Refund is a compensating
        entry — historical truth is never rewritten."""
        self._assert_owner()
        raw = self.disputes.get(dispute_id)
        if not raw:
            raise ValueError("PPA: dispute not found")
        case = json.loads(raw)
        if case["status"] != "OPEN":
            raise ValueError("PPA: dispute not open")
        if remedy not in ("refund", "waive", "reject"):
            raise ValueError("PPA: unknown remedy")
        if remedy == "refund":
            pay = json.loads(self.payments[case["payment_id"]])
            rec = self._get_account(pay["account_id"])
            rec["balance"] = str(int(rec["balance"]) + int(pay["amount"]))
            self.accounts[pay["account_id"]] = json.dumps(rec)
            pay["status"] = "REFUNDED"
            self.payments[case["payment_id"]] = json.dumps(pay)
        case["status"] = "RESOLVED"
        case["remedy"] = remedy
        self.disputes[dispute_id] = json.dumps(case)
        return "dispute_resolved:" + remedy

    @gl.public.view
    def get_dispute(self, dispute_id: str) -> typing.Any:
        raw = self.disputes.get(dispute_id)
        if not raw:
            raise ValueError("PPA: dispute not found")
        return json.loads(raw)

    # ---------- delegation (daa + dal semantics) ----------
    @gl.public.write
    def delegate(self, delegation_id: str, principal: str,
                 per_tx_limit: str, daily_limit: str, expires: str) -> str:
        """Grant scoped spending authority. Delegate sends still run the FULL
        policy gate of the sub-account used — delegation narrows, never widens."""
        self._assert_owner()
        if not _valid_id(delegation_id) or self.delegations.get(delegation_id):
            raise ValueError("PPA: invalid or duplicate delegation id")
        if not _valid_addr(principal):
            raise ValueError("PPA: invalid principal")
        for c in (per_tx_limit, daily_limit, expires):
            if not c.isdigit():
                raise ValueError("PPA: numeric fields must be digit strings")
        d = {
            "delegation_id": delegation_id, "principal": principal,
            "per_tx_limit": per_tx_limit, "daily_limit": daily_limit,
            "expires": expires, "status": "ACTIVE",
            "created": _now_iso(),
        }
        self.delegations[delegation_id] = json.dumps(d)
        return "delegated"

    @gl.public.write
    def revoke_delegation(self, delegation_id: str) -> str:
        self._assert_owner()
        raw = self.delegations.get(delegation_id)
        if not raw:
            raise ValueError("PPA: delegation not found")
        d = json.loads(raw)
        d["status"] = "REVOKED"
        self.delegations[delegation_id] = json.dumps(d)
        return "revoked"

    @gl.public.view
    def get_delegation(self, delegation_id: str) -> typing.Any:
        raw = self.delegations.get(delegation_id)
        if not raw:
            raise ValueError("PPA: delegation not found")
        return json.loads(raw)
