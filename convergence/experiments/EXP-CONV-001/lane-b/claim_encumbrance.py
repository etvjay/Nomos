# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
"""Deterministic Claim Encumbrance primitive (GenLayer).

Claim-level capacity accounting keyed by stable claim_id. A claim has an
immutable financeable amount; reservations draw down that capacity and move
through RESERVED -> COMMITTED and RESERVED/COMMITTED -> RELEASED/SETTLED.
All methods are deterministic; NONE of the decision boundary is delegated.
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


def _canonical(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


class ClaimEncumbrance(gl.Contract):
    financeable: TreeMap[str, str]
    encumbrances: TreeMap[str, str]
    active: TreeMap[str, str]

    def __init__(self) -> None:
        pass

    @gl.public.write
    def set_financeable_amount(self, claim_id: str, amount: str) -> str:
        if not claim_id:
            raise ValueError("ClaimEncumbrance: claim_id must not be empty")
        if not _valid_uint(amount):
            raise ValueError("ClaimEncumbrance: amount must be a positive uint-string")
        if claim_id in self.financeable:
            raise ValueError("ClaimEncumbrance: financeable amount already set for claim")
        self.financeable[claim_id] = amount
        self.active[claim_id] = "0"
        return _canonical(
            {"claim_id": claim_id, "financeable_amount": amount}
        )

    @gl.public.write
    def reserve(self, reservation_id: str, claim_id: str, amount: str) -> str:
        if not reservation_id:
            raise ValueError("ClaimEncumbrance: reservation_id must not be empty")
        if not _valid_uint(amount):
            raise ValueError("ClaimEncumbrance: amount must be a positive uint-string")
        if claim_id not in self.financeable:
            raise ValueError("ClaimEncumbrance: unknown claim")
        if reservation_id in self.encumbrances:
            raise ValueError("ClaimEncumbrance: reservation already exists")
        used = int(self.active.get(claim_id, "0"))
        requested = int(amount)
        if used + requested > int(self.financeable[claim_id]):
            raise ValueError("ClaimEncumbrance: exceeds financeable capacity")
        record = {
            "reservation_id": reservation_id,
            "claim_id": claim_id,
            "amount": amount,
            "status": "RESERVED",
        }
        canonical = _canonical(record)
        self.encumbrances[reservation_id] = canonical
        self.active[claim_id] = str(used + requested)
        return canonical

    @gl.public.write
    def commit(self, reservation_id: str) -> str:
        if reservation_id not in self.encumbrances:
            raise ValueError("ClaimEncumbrance: unknown reservation")
        record = json.loads(self.encumbrances[reservation_id])
        if record["status"] != "RESERVED":
            raise ValueError("ClaimEncumbrance: only RESERVED reservations may commit")
        record["status"] = "COMMITTED"
        canonical = _canonical(record)
        self.encumbrances[reservation_id] = canonical
        return canonical

    @gl.public.write
    def release(self, reservation_id: str) -> str:
        if reservation_id not in self.encumbrances:
            raise ValueError("ClaimEncumbrance: unknown reservation")
        record = json.loads(self.encumbrances[reservation_id])
        status = record["status"]
        if status in ("RELEASED", "SETTLED"):
            raise ValueError("ClaimEncumbrance: reservation already terminated")
        record["status"] = "RELEASED"
        canonical = _canonical(record)
        self.encumbrances[reservation_id] = canonical
        claim_id = record["claim_id"]
        self.active[claim_id] = str(
            int(self.active.get(claim_id, "0")) - int(record["amount"])
        )
        return canonical

    @gl.public.write
    def settle(self, reservation_id: str) -> str:
        if reservation_id not in self.encumbrances:
            raise ValueError("ClaimEncumbrance: unknown reservation")
        record = json.loads(self.encumbrances[reservation_id])
        status = record["status"]
        if status in ("RELEASED", "SETTLED"):
            raise ValueError("ClaimEncumbrance: reservation already terminated")
        record["status"] = "SETTLED"
        canonical = _canonical(record)
        self.encumbrances[reservation_id] = canonical
        claim_id = record["claim_id"]
        self.active[claim_id] = str(
            int(self.active.get(claim_id, "0")) - int(record["amount"])
        )
        return canonical

    @gl.public.view
    def get_encumbrance(self, reservation_id: str) -> str:
        if reservation_id not in self.encumbrances:
            return ""
        return self.encumbrances[reservation_id]

    @gl.public.view
    def active_encumbrances(self, claim_id: str) -> str:
        return self.active.get(claim_id, "0")

    @gl.public.view
    def financeable_amount(self, claim_id: str) -> str:
        return self.financeable.get(claim_id, "")