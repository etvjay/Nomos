# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
"""Financial Contract primitive (GenLayer) v0.1 — narrowed scope.

SCOPE_NARROWED per PRIMITIVE_QUALIFICATION: v0.1 implements a canonical
**obligation / cash-flow lifecycle** — principal conservation, deterministic
payment application, maturity, closure, and creditor-declared default.
Contingent clauses, interest accrual rules, covenants, restructuring, and
natural-language conditions are explicitly OUT of this version; where
interpretive judgment is needed, upstream primitives (Claim Verification,
Policy Envelope) supply bounded results that feed lifecycle transitions.

JUDGMENT_BOUNDARY = NONE for the v0.1 canonical slice. Principal/balance
conservation and payment application are fully deterministic. Historical
cash flows are append-only and can never be rewritten by any judgment.

Article V: applying a payment RECORDS its application; actual fund transfer
remains with settlement/custody layers outside Nomos accounting state.
"""

from genlayer import *
import json


def _valid_uint(s: str) -> bool:
    if not s:
        return False
    if not s.isdecimal():
        return False
    if len(s) > 39:
        return False
    if len(s) > 1 and s[0] == "0":
        return False
    return int(s) > 0


def _valid_int_ts(s: str) -> bool:
    if not s:
        return False
    body = s[1:] if s.startswith("-") else s
    return body.isdecimal()


def _canonical(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


class FinancialContract(gl.Contract):
    contracts: TreeMap[str, str]
    payments: TreeMap[str, str]

    def __init__(self) -> None:
        pass

    @gl.public.write
    def open_contract(
        self,
        contract_id: str,
        creditor: str,
        obligor: str,
        principal: str,
        asset: str,
        valid_after: str,
        maturity: str,
        authority_ref: str,
    ) -> str:
        """Open an ACTIVE obligation. Binds exact upstream authority origin."""
        if not contract_id or not creditor or not obligor or not asset or not authority_ref:
            raise ValueError("FinancialContract: empty required field")
        if creditor.lower() == obligor.lower():
            raise ValueError("FinancialContract: self-dealing is not permitted")
        if not _valid_uint(principal):
            raise ValueError("FinancialContract: principal must be positive uint-string")
        if not _valid_int_ts(valid_after) or not _valid_int_ts(maturity):
            raise ValueError("FinancialContract: invalid dates")
        if int(valid_after) > int(maturity):
            raise ValueError("FinancialContract: valid_after exceeds maturity")
        if contract_id in self.contracts:
            raise ValueError("FinancialContract: contract already exists")
        record = {
            "contract_id": contract_id,
            "creditor": creditor,
            "obligor": obligor,
            "principal": principal,
            "asset": asset,
            "valid_after": str(int(valid_after)),
            "maturity": str(int(maturity)),
            "authority_ref": authority_ref,
            "total_paid": "0",
            "outstanding": principal,
            "status": "ACTIVE",
        }
        canonical = _canonical(record)
        self.contracts[contract_id] = canonical
        return canonical

    @gl.public.write
    def apply_payment(
        self,
        contract_id: str,
        payment_id: str,
        amount: str,
        at_timestamp: str,
    ) -> str:
        """Apply one payment deterministically. Conservation enforced exactly."""
        record = self.contracts.get(contract_id, "")
        if not record:
            raise ValueError("FinancialContract: unknown contract")
        contract = json.loads(record)
        if not payment_id:
            raise ValueError("FinancialContract: payment_id must not be empty")
        pay_key = contract_id + "/" + payment_id
        if pay_key in self.payments:
            raise ValueError("FinancialContract: payment already exists")
        if not _valid_uint(amount):
            raise ValueError("FinancialContract: amount must be positive uint-string")
        if not _valid_int_ts(at_timestamp):
            raise ValueError("FinancialContract: invalid timestamp")

        # Fail-closed gates.
        if contract["status"] != "ACTIVE":
            reason = (
                "CONTRACT_CLOSED" if contract["status"] == "CLOSED"
                else "CONTRACT_DEFAULTED" if contract["status"] == "DEFAULTED"
                else "CONTRACT_MATURED"
            )
            return self._deny(pay_key, amount, reason)
        ts = int(at_timestamp)
        if ts < int(contract["valid_after"]):
            return self._deny(pay_key, amount, "BEFORE_VALIDITY_WINDOW")
        outstanding = int(contract["outstanding"])
        requested = int(amount)
        if requested > outstanding:
            return self._deny(pay_key, amount, "EXCEEDS_OUTSTANDING")

        # Deterministic application — conservation exact.
        contract["outstanding"] = str(outstanding - requested)
        contract["total_paid"] = str(int(contract["total_paid"]) + requested)
        new_status = "CLOSED" if contract["outstanding"] == "0" else contract["status"]
        contract["status"] = new_status
        self.contracts[contract_id] = _canonical(contract)

        payment = {
            "payment_key": pay_key,
            "payment_id": payment_id,
            "contract_id": contract_id,
            "amount": amount,
            "applied_at": str(ts),
            "status": "APPLIED",
        }
        canonical = _canonical(payment)
        self.payments[pay_key] = canonical
        return _canonical({
            "payment_key": pay_key,
            "applied": amount,
            "outstanding": contract["outstanding"],
            "total_paid": contract["total_paid"],
            "contract_status": new_status,
        })

    @gl.public.write
    def declare_default(self, contract_id: str) -> str:
        """Creditor declares default on a past-maturity contract with outstanding balance.

        Terminal for payments; historical records untouched. Actual remedies
        (acceleration, collection) loop through Gaia + Workflow Authorization.
        """
        record = self.contracts.get(contract_id, "")
        if not record:
            raise ValueError("FinancialContract: unknown contract")
        contract = json.loads(record)
        # Only the creditor may declare default.
        if gl.message.sender_address.as_hex.lower().removeprefix("0x") != contract["creditor"].lower().removeprefix("0x"):
            raise ValueError("FinancialContract: only the creditor may declare default")
        if contract["status"] != "ACTIVE":
            raise ValueError("FinancialContract: contract not active")
        if int(contract["outstanding"]) == 0:
            raise ValueError("FinancialContract: nothing outstanding")
        # Default requires maturity to have passed. Block time is the
        # transaction datetime (ISO string) from the raw message.
        block_dt = gl.message_raw["datetime"]  # ISO-8601 string
        from datetime import datetime as _dt
        block_ts = int(_dt.fromisoformat(str(block_dt).replace("Z", "+00:00")).timestamp())
        if block_ts <= int(contract["maturity"]):
            raise ValueError("FinancialContract: maturity has not passed")

        contract["status"] = "DEFAULTED"
        self.contracts[contract_id] = _canonical(contract)
        return _canonical(contract)

    def _deny(self, pay_key: str, amount: str, reason_code: str) -> str:
        return _canonical({
            "payment_key": pay_key,
            "decision": "DENY",
            "reason_code": reason_code,
            "attempted": amount,
        })

    @gl.public.view
    def get_contract(self, contract_id: str) -> str:
        return self.contracts.get(contract_id, "")

    @gl.public.view
    def get_payment(self, contract_id: str, payment_id: str) -> str:
        return self.payments.get(contract_id + "/" + payment_id, "")
