# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
"""Dynamic Authorization Lanes (DAL) primitive (GenLayer) v0.1.

Authorization-scoped replay-domain allocation over a keyed nonce mechanism.
Each (issuer, domain_id) pair owns an independent replay domain with its own
monotonic nonce, so independently valid authorizations from the same issuer
never artificially invalidate each other through a shared counter.

JUDGMENT_BOUNDARY = NONE. Nonce correctness and replay safety are fully
deterministic. Revocation and expiry are explicit and testable.

Article V separation: replay independence does NOT imply independence of
balances, capacity, policy state, or other shared economic dependencies -
DAL exposes no such state at all.
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


class Dal(gl.Contract):
    lanes: TreeMap[str, str]

    def __init__(self) -> None:
        pass

    def _key(self, issuer: str, domain_id: str) -> str:
        return issuer + "/" + domain_id

    @gl.public.write
    def open_lane(self, issuer: str, domain_id: str, expiry_window: str) -> str:
        """Open a fresh replay domain for issuer+domain usable until expiry."""
        if not issuer or not domain_id:
            raise ValueError("DAL: issuer and domain_id must not be empty")
        if not _valid_int_ts(expiry_window):
            raise ValueError("DAL: invalid expiry timestamp")
        key = self._key(issuer, domain_id)
        if key in self.lanes:
            raise ValueError("DAL: lane already exists")
        record = {
            "issuer": issuer,
            "domain_id": domain_id,
            "nonce": "1",
            "expiry": str(int(expiry_window)),
            "status": "ACTIVE",
        }
        canonical = _canonical(record)
        self.lanes[key] = canonical
        return canonical

    @gl.public.write
    def exercise(self, issuer: str, domain_id: str, nonce: str, at_timestamp: str) -> str:
        """Authorize one execution inside a lane's replay domain.

        AUTHORIZE is returned only when the lane is ACTIVE, unexpired, and the
        supplied nonce equals the lane's expected next nonce; success advances
        the nonce atomically. Any denial mutates nothing.
        """
        key = self._key(issuer, domain_id)
        record = self.lanes.get(key, "")
        if not record:
            raise ValueError("DAL: unknown lane")
        if not _valid_int_ts(at_timestamp):
            raise ValueError("DAL: invalid timestamp")

        lane = json.loads(record)

        # Fail-closed ordering: status first, then time, then nonce.
        if lane["status"] != "ACTIVE":
            reason = "LANE_REVOKED" if lane["status"] == "REVOKED" else "LANE_INACTIVE"
            return self._deny(key, nonce, reason)
        if int(at_timestamp) > int(lane["expiry"]):
            return self._deny(key, nonce, "LANE_EXPIRED")
        expected = int(lane["nonce"])
        supplied = int(nonce)
        if supplied < 1:
            return self._deny(key, nonce, "NONCE_INVALID")
        if supplied < expected:
            return self._deny(key, nonce, "NONCE_REUSED")
        if supplied > expected:
            return self._deny(key, nonce, "NONCE_INVALID")

        lane["nonce"] = str(expected + 1)
        self.lanes[key] = _canonical(lane)
        return _canonical({
            "lane_key": key,
            "decision": "AUTHORIZE",
            "reason_code": "NONCE_VALID",
            "used_nonce": str(supplied),
        })

    @gl.public.write
    def revoke_lane(self, issuer: str, domain_id: str) -> str:
        key = self._key(issuer, domain_id)
        record = self.lanes.get(key, "")
        if not record:
            raise ValueError("DAL: unknown lane")
        lane = json.loads(record)
        if lane["status"] != "ACTIVE":
            raise ValueError("DAL: lane not active")
        lane["status"] = "REVOKED"
        self.lanes[key] = _canonical(lane)
        return _canonical(lane)

    def _deny(self, key: str, nonce: str, reason_code: str) -> str:
        return _canonical({
            "lane_key": key,
            "decision": "DENY",
            "reason_code": reason_code,
            "supplied_nonce": nonce,
        })

    @gl.public.view
    def get_lane(self, issuer: str, domain_id: str) -> str:
        return self.lanes.get(self._key(issuer, domain_id), "")
