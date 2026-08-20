# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6", "py-lib-genlayer-std": "11rhn002yfajawsz7fai6mykznbxkxs6l91iskj5cm82c92qhy3v" }
"""Capital Commitment primitive (GenLayer). Deterministic, EXACT convergence.

Canonical JSON serialization: json.dumps(obj, sort_keys=True, separators=(",", ":")).
All amounts and timestamps are uint-strings (ASCII decimal digits, 1..39 chars,
no leading zeros, value > 0).
"""
import json

from genlayer import *


def _pool_key(pool_id: str, asset: str) -> str:
    return pool_id + "\x00" + asset


def _check_uint(value, field: str) -> None:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"CapitalCommitment: {field} must be a non-empty uint-string")
    if not value.isascii() or not value.isdigit():
        raise ValueError(f"CapitalCommitment: {field} must be an ASCII uint-string")
    if len(value) > 39:
        raise ValueError(f"CapitalCommitment: {field} exceeds 39 digits")
    if value[0] == "0":
        raise ValueError(f"CapitalCommitment: {field} must be greater than zero")


def _check_nonempty(value, field: str) -> None:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"CapitalCommitment: {field} must be a non-empty string")


def _serialize(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _record_field(raw_json: str, field: str) -> str:
    return json.loads(raw_json)[field]


class CapitalCommitment(gl.Contract):
    commitments: TreeMap[str, str]
    backings: TreeMap[str, str]
    active_sums: TreeMap[str, str]

    def __init__(self):
        pass

    @gl.public.write
    def set_backing(self, pool_id: str, asset: str, amount: str) -> str:
        _check_nonempty(pool_id, "pool_id")
        _check_nonempty(asset, "asset")
        _check_uint(amount, "amount")
        key = _pool_key(pool_id, asset)
        if key in self.backings:
            raise ValueError("CapitalCommitment: backing already set for pool+asset")
        record = {"pool_id": pool_id, "asset": asset, "amount": amount}
        self.backings[key] = _serialize(record)
        self.active_sums[key] = "0"
        return _serialize(record)

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
        _check_nonempty(commitment_id, "commitment_id")
        _check_nonempty(pool_id, "pool_id")
        _check_nonempty(asset, "asset")
        _check_nonempty(beneficiary, "beneficiary")
        _check_uint(amount, "amount")
        _check_uint(valid_until, "valid_until")
        if commitment_id in self.commitments:
            raise ValueError("CapitalCommitment: commitment_id already used")
        key = _pool_key(pool_id, asset)
        if key not in self.backings:
            raise ValueError("CapitalCommitment: pool+asset has no backing capacity")
        backing = int(_record_field(self.backings[key], "amount"))
        active = int(self.active_sums.get(key, "0"))
        new_active = active + int(amount)
        if new_active > backing:
            raise ValueError("CapitalCommitment: reservation exceeds available backing capacity")
        record = {
            "commitment_id": commitment_id,
            "pool_id": pool_id,
            "asset": asset,
            "beneficiary": beneficiary,
            "amount": amount,
            "valid_until": valid_until,
            "status": "RESERVED",
        }
        self.commitments[commitment_id] = _serialize(record)
        self.active_sums[key] = str(new_active)
        return _serialize(record)

    @gl.public.write
    def commit(self, commitment_id: str) -> str:
        _check_nonempty(commitment_id, "commitment_id")
        record = self._get_record(commitment_id)
        if record["status"] != "RESERVED":
            raise ValueError("CapitalCommitment: only RESERVED commitments can be committed")
        record["status"] = "COMMITTED"
        self.commitments[commitment_id] = _serialize(record)
        return _serialize(record)

    @gl.public.write
    def release(self, commitment_id: str) -> str:
        _check_nonempty(commitment_id, "commitment_id")
        record = self._get_record(commitment_id)
        if record["status"] not in ("RESERVED", "COMMITTED"):
            raise ValueError("CapitalCommitment: commitment already released or expired")
        record["status"] = "RELEASED"
        self.commitments[commitment_id] = _serialize(record)
        self._decrement_active(record["pool_id"], record["asset"], record["amount"])
        return _serialize(record)

    @gl.public.write
    def expire(self, commitment_id: str, at: str) -> str:
        _check_nonempty(commitment_id, "commitment_id")
        _check_uint(at, "at")
        record = self._get_record(commitment_id)
        if record["status"] not in ("RESERVED", "COMMITTED"):
            raise ValueError("CapitalCommitment: commitment already expired or released")
        if int(at) < int(record["valid_until"]):
            raise ValueError("CapitalCommitment: expiry time precedes valid_until")
        record["status"] = "EXPIRED"
        self.commitments[commitment_id] = _serialize(record)
        self._decrement_active(record["pool_id"], record["asset"], record["amount"])
        return _serialize(record)

    @gl.public.view
    def get_commitment(self, commitment_id: str) -> str:
        if not isinstance(commitment_id, str) or commitment_id == "":
            return ""
        return self.commitments.get(commitment_id, "")

    @gl.public.view
    def active_commitments(self, pool_id: str, asset: str) -> str:
        return self.active_sums.get(_pool_key(pool_id, asset), "0")

    @gl.public.view
    def available_capacity(self, pool_id: str, asset: str) -> str:
        key = _pool_key(pool_id, asset)
        if key not in self.backings:
            return ""
        backing = int(_record_field(self.backings[key], "amount"))
        active = int(self.active_sums.get(key, "0"))
        return str(backing - active)

    def _get_record(self, commitment_id: str) -> dict:
        raw = self.commitments.get(commitment_id, "")
        if raw == "":
            raise ValueError("CapitalCommitment: unknown commitment_id")
        return json.loads(raw)

    def _decrement_active(self, pool_id: str, asset: str, amount: str) -> None:
        key = _pool_key(pool_id, asset)
        cur = int(self.active_sums.get(key, "0"))
        self.active_sums[key] = str(max(0, cur - int(amount)))