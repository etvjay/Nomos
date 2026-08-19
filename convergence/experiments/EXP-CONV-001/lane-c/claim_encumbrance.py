# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
from genlayer import *

import json

RESERVED = "RESERVED"
COMMITTED = "COMMITTED"
RELEASED = "RELEASED"
SETTLED = "SETTLED"
TERMINAL = (RELEASED, SETTLED)
MAX_AMOUNT_DIGITS = 39


class ClaimEncumbrance(gl.Contract):
    financeable: TreeMap[str, str]
    active: TreeMap[str, str]
    encumbrances: TreeMap[str, str]

    def __init__(self):
        pass

    def _validate_id(self, value, name):
        if not isinstance(value, str) or value == "":
            raise ValueError(f"ClaimEncumbrance: {name} must be a non-empty string")

    def _validate_amount(self, value):
        if not isinstance(value, str) or value == "":
            raise ValueError("ClaimEncumbrance: amount must be a non-empty string")
        if len(value) > MAX_AMOUNT_DIGITS:
            raise ValueError("ClaimEncumbrance: amount exceeds the maximum of 39 digits")
        if not value.isascii() or not value.isdigit():
            raise ValueError("ClaimEncumbrance: amount must be a digit string")
        if int(value) == 0:
            raise ValueError("ClaimEncumbrance: amount must be greater than zero")

    def _canonical(self, obj):
        return json.dumps(obj, sort_keys=True, separators=(",", ":"))

    def _claim_record(self, claim_id, amount):
        return self._canonical(
            {"claim_id": claim_id, "financeable_amount": amount}
        )

    def _encumbrance_record(self, reservation_id, claim_id, amount, status):
        return self._canonical(
            {
                "reservation_id": reservation_id,
                "claim_id": claim_id,
                "amount": amount,
                "status": status,
            }
        )

    def _load_encumbrance(self, reservation_id):
        stored = self.encumbrances.get(reservation_id, None)
        if stored is None:
            raise ValueError(f"ClaimEncumbrance: unknown reservation {reservation_id}")
        return json.loads(stored)

    def _decrement_active(self, claim_id, amount):
        current = int(self.active.get(claim_id, "0"))
        self.active[claim_id] = str(current - int(amount))

    def _terminate(self, reservation_id, target):
        rec = self._load_encumbrance(reservation_id)
        if rec["status"] in TERMINAL:
            raise ValueError(
                f"ClaimEncumbrance: reservation {reservation_id} already "
                f"in terminal status {rec['status']}"
            )
        encoded = self._encumbrance_record(
            rec["reservation_id"], rec["claim_id"], rec["amount"], target
        )
        self.encumbrances[reservation_id] = encoded
        self._decrement_active(rec["claim_id"], rec["amount"])
        return encoded

    @gl.public.write
    def set_financeable_amount(self, claim_id: str, amount: str) -> str:
        self._validate_id(claim_id, "claim_id")
        self._validate_amount(amount)
        if claim_id in self.financeable:
            raise ValueError(
                "ClaimEncumbrance: financeable amount already set for claim " + claim_id
            )
        self.financeable[claim_id] = amount
        self.active[claim_id] = "0"
        return self._claim_record(claim_id, amount)

    @gl.public.write
    def reserve(self, reservation_id: str, claim_id: str, amount: str) -> str:
        self._validate_id(reservation_id, "reservation_id")
        self._validate_id(claim_id, "claim_id")
        self._validate_amount(amount)
        if reservation_id in self.encumbrances:
            raise ValueError(
                "ClaimEncumbrance: reservation already exists " + reservation_id
            )
        financeable_amount = self.financeable.get(claim_id, None)
        if financeable_amount is None:
            raise ValueError("ClaimEncumbrance: unknown claim " + claim_id)
        active_sum = int(self.active.get(claim_id, "0"))
        requested = int(amount)
        if active_sum + requested > int(financeable_amount):
            raise ValueError(
                "ClaimEncumbrance: reservation would exceed financeable capacity"
            )
        encoded = self._encumbrance_record(
            reservation_id, claim_id, amount, RESERVED
        )
        self.encumbrances[reservation_id] = encoded
        self.active[claim_id] = str(active_sum + requested)
        return encoded

    @gl.public.write
    def commit(self, reservation_id: str) -> str:
        self._validate_id(reservation_id, "reservation_id")
        rec = self._load_encumbrance(reservation_id)
        if rec["status"] != RESERVED:
            raise ValueError(
                f"ClaimEncumbrance: cannot commit reservation {reservation_id} "
                f"in status {rec['status']}"
            )
        encoded = self._encumbrance_record(
            rec["reservation_id"], rec["claim_id"], rec["amount"], COMMITTED
        )
        self.encumbrances[reservation_id] = encoded
        return encoded

    @gl.public.write
    def release(self, reservation_id: str) -> str:
        self._validate_id(reservation_id, "reservation_id")
        return self._terminate(reservation_id, RELEASED)

    @gl.public.write
    def settle(self, reservation_id: str) -> str:
        self._validate_id(reservation_id, "reservation_id")
        return self._terminate(reservation_id, SETTLED)

    @gl.public.view
    def get_encumbrance(self, reservation_id: str) -> str:
        self._validate_id(reservation_id, "reservation_id")
        return self.encumbrances.get(reservation_id, "")

    @gl.public.view
    def active_encumbrances(self, claim_id: str) -> str:
        self._validate_id(claim_id, "claim_id")
        return self.active.get(claim_id, "0")

    @gl.public.view
    def financeable_amount(self, claim_id: str) -> str:
        self._validate_id(claim_id, "claim_id")
        return self.financeable.get(claim_id, "")