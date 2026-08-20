# {"schema": "genlayer/capital-commitment/0.1.0", "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6"}
"""Capital Commitment primitive (deterministic, EXACT convergence).

Backs a pool+asset with immutable capacity, allows deterministic
reserve/commit/release/expire transitions of commitments within that
capacity, and exposes views for the active commitment sum and remaining
available capacity. No nondeterministic input is used; expiry takes an
explicit ``at`` timestamp.
"""

import json

from genlayer import *


class CapitalCommitment(gl.Contract):
    backings: TreeMap[str, str]
    actives: TreeMap[str, str]
    commitments: TreeMap[str, str]

    _SEP = "\x1f"

    def __init__(self) -> None:
        pass

    def _check_id(self, value, label: str) -> str:
        if not isinstance(value, str) or value == "":
            raise ValueError(f"CapitalCommitment: {label} must be a non-empty string")
        return value

    def _uint(self, value, label: str) -> str:
        if not isinstance(value, str) or value == "":
            raise ValueError(f"CapitalCommitment: {label} must be a non-empty uint-string")
        if not value.isdigit():
            raise ValueError(f"CapitalCommitment: {label} must be an ASCII decimal uint-string")
        if len(value) > 39:
            raise ValueError(f"CapitalCommitment: {label} exceeds 39 digits")
        if value[0] == "0":
            raise ValueError(f"CapitalCommitment: {label} must be positive without leading zeros")
        return value

    def _key(self, pool_id: str, asset: str) -> str:
        return pool_id + self._SEP + asset

    def _canon(self, obj) -> str:
        return json.dumps(obj, sort_keys=True, separators=(",", ":"))

    def _record(
        self, commitment_id, pool_id, asset, beneficiary, amount, valid_until, status
    ) -> dict:
        return {
            "commitment_id": commitment_id,
            "pool_id": pool_id,
            "asset": asset,
            "beneficiary": beneficiary,
            "amount": amount,
            "valid_until": valid_until,
            "status": status,
        }

    def _load(self, commitment_id: str) -> dict:
        raw = self.commitments.get(commitment_id)
        if raw is None:
            raise ValueError("CapitalCommitment: unknown commitment")
        return json.loads(raw)

    def _free_capacity(self, pool_id: str, asset: str, amount: str) -> None:
        key = self._key(pool_id, asset)
        self.actives[key] = str(int(self.actives.get(key, "0")) - int(amount))

    @gl.public.write
    def set_backing(self, pool_id: str, asset: str, amount: str) -> str:
        self._check_id(pool_id, "pool_id")
        self._check_id(asset, "asset")
        amount = self._uint(amount, "amount")
        key = self._key(pool_id, asset)
        if key in self.backings:
            raise ValueError("CapitalCommitment: backing already set for pool+asset")
        self.backings[key] = amount
        return self._canon({"pool_id": pool_id, "asset": asset, "amount": amount})

    @gl.public.write
    def reserve(
        self,
        commitment_id: str,
        pool_id: str,
        asset: str,
        beneficiary: str,
        amount: str,
        valid_until: str,
    ) -> str:
        self._check_id(commitment_id, "commitment_id")
        self._check_id(pool_id, "pool_id")
        self._check_id(asset, "asset")
        self._check_id(beneficiary, "beneficiary")
        amount = self._uint(amount, "amount")
        valid_until = self._uint(valid_until, "valid_until")
        if commitment_id in self.commitments:
            raise ValueError("CapitalCommitment: commitment_id already reserved")
        key = self._key(pool_id, asset)
        backing = self.backings.get(key)
        if backing is None:
            raise ValueError("CapitalCommitment: no backing for pool+asset")
        active = self.actives.get(key, "0")
        if int(active) + int(amount) > int(backing):
            raise ValueError("CapitalCommitment: reserve exceeds available capacity")
        record = self._record(
            commitment_id, pool_id, asset, beneficiary, amount, valid_until, "RESERVED"
        )
        self.commitments[commitment_id] = self._canon(record)
        self.actives[key] = str(int(active) + int(amount))
        return self._canon(record)

    @gl.public.write
    def commit(self, commitment_id: str) -> str:
        self._check_id(commitment_id, "commitment_id")
        record = self._load(commitment_id)
        if record["status"] != "RESERVED":
            raise ValueError("CapitalCommitment: only RESERVED commitments can be committed")
        record["status"] = "COMMITTED"
        self.commitments[commitment_id] = self._canon(record)
        return self._canon(record)

    @gl.public.write
    def release(self, commitment_id: str) -> str:
        self._check_id(commitment_id, "commitment_id")
        record = self._load(commitment_id)
        if record["status"] not in ("RESERVED", "COMMITTED"):
            raise ValueError("CapitalCommitment: commitment already released or expired")
        record["status"] = "RELEASED"
        self.commitments[commitment_id] = self._canon(record)
        self._free_capacity(record["pool_id"], record["asset"], record["amount"])
        return self._canon(record)

    @gl.public.write
    def expire(self, commitment_id: str, at: str) -> str:
        self._check_id(commitment_id, "commitment_id")
        at = self._uint(at, "at")
        record = self._load(commitment_id)
        if record["status"] not in ("RESERVED", "COMMITTED"):
            raise ValueError("CapitalCommitment: commitment already released or expired")
        if int(at) < int(record["valid_until"]):
            raise ValueError("CapitalCommitment: cannot expire before valid_until")
        record["status"] = "EXPIRED"
        self.commitments[commitment_id] = self._canon(record)
        self._free_capacity(record["pool_id"], record["asset"], record["amount"])
        return self._canon(record)

    @gl.public.view
    def get_commitment(self, commitment_id: str) -> str:
        raw = self.commitments.get(commitment_id)
        return raw if raw is not None else ""

    @gl.public.view
    def active_commitments(self, pool_id: str, asset: str) -> str:
        return self.actives.get(self._key(pool_id, asset), "0")

    @gl.public.view
    def available_capacity(self, pool_id: str, asset: str) -> str:
        key = self._key(pool_id, asset)
        backing = self.backings.get(key)
        if backing is None:
            return ""
        return str(int(backing) - int(self.actives.get(key, "0")))