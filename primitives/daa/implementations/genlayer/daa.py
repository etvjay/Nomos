# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
"""Dynamic Authority Allocation (DAA) primitive (GenLayer) v0.1.

Deterministic authority-allocation state machine: a request for bounded
authority over a resource is either awarded (within the requested bound),
rejected, or left undetermined. Awards are immutable grants that expire or
may be revoked, and expose exactly one downstream surface: verify_authority.

JUDGMENT_BOUNDARY = NONE for the v0.1 canonical slice. The allocation of
authority itself is expressed here through deterministic predicates supplied
by the authority source; qualitative mandate interpretation belongs to
upstream Policy Envelope / Claim Verification consumed before requesting.

Article V separation enforced by construction: an award does not reserve
capital, encumber claims, assign replay lanes, or move value. Its only
output is an authorization decision.
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


class Daa(gl.Contract):
    requests: TreeMap[str, str]
    awards: TreeMap[str, str]

    def __init__(self) -> None:
        pass

    # ---------- request ----------

    @gl.public.write
    def request_allocation(
        self,
        request_id: str,
        resource: str,
        asset: str,
        beneficiary: str,
        purpose: str,
        requested_bound: str,
        policy_hash: str,
        valid_after: str,
        valid_until: str,
    ) -> str:
        if not request_id or not resource or not asset or not beneficiary or not purpose:
            raise ValueError("DAA: empty required field")
        if not policy_hash:
            raise ValueError("DAA: policy_hash must not be empty")
        if not _valid_uint(requested_bound):
            raise ValueError("DAA: requested_bound must be positive uint-string")
        if not _valid_int_ts(valid_after) or not _valid_int_ts(valid_until):
            raise ValueError("DAA: invalid validity timestamps")
        if int(valid_after) > int(valid_until):
            raise ValueError("DAA: valid_after exceeds valid_until")
        if request_id in self.requests:
            raise ValueError("DAA: request already exists")
        record = {
            "request_id": request_id,
            "authority_source": gl.message.sender_address.as_hex.lower(),
            "resource": resource,
            "asset": asset,
            "beneficiary": beneficiary,
            "purpose": purpose,
            "requested_bound": requested_bound,
            "policy_hash": policy_hash,
            "valid_after": str(int(valid_after)),
            "valid_until": str(int(valid_until)),
            "status": "REQUESTED",
        }
        canonical = _canonical(record)
        self.requests[request_id] = canonical
        return canonical

    # ---------- decision ----------

    @gl.public.write
    def award(self, request_id: str, allocation_id: str, max_authority: str, awarded_at: str) -> str:
        req = self._get_request(request_id)
        if req["status"] != "REQUESTED":
            raise ValueError("DAA: request not awardable")
        # Only the recorded authority source may award.
        if gl.message.sender_address.as_hex.lower() != req["authority_source"]:
            raise ValueError("DAA: only the authority source may award")
        if not allocation_id:
            raise ValueError("DAA: allocation_id must not be empty")
        if allocation_id in self.awards:
            raise ValueError("DAA: allocation_id already exists")
        if not _valid_uint(max_authority):
            raise ValueError("DAA: max_authority must be positive uint-string")
        if not _valid_uint(awarded_at.replace("-", "") if awarded_at.startswith("-") else awarded_at) and not _valid_int_ts(awarded_at):
            raise ValueError("DAA: invalid awarded_at timestamp")
        ts = int(awarded_at)
        if ts < int(req["valid_after"]) or ts > int(req["valid_until"]):
            raise ValueError("DAA: award time outside request validity window")
        # Bound escalation is structurally impossible.
        if int(max_authority) > int(req["requested_bound"]):
            raise ValueError("DAA: award exceeds requested bound")

        record = {
            "allocation_id": allocation_id,
            "request_id": request_id,
            "authority_source": req["authority_source"],
            "beneficiary": req["beneficiary"],
            "resource": req["resource"],
            "asset": req["asset"],
            "purpose": req["purpose"],
            "max_authority": max_authority,
            "policy_hash": req["policy_hash"],
            "valid_after": req["valid_after"],
            "valid_until": req["valid_until"],
            "status": "AWARDED",
        }
        canonical = _canonical(record)
        self.awards[allocation_id] = canonical

        req["status"] = "AWARDED"
        self.requests[request_id] = _canonical(req)
        return canonical

    @gl.public.write
    def reject_request(self, request_id: str) -> str:
        req = self._get_request(request_id)
        if gl.message.sender_address.as_hex.lower() != req["authority_source"]:
            raise ValueError("DAA: only the authority source may reject")
        if req["status"] != "REQUESTED":
            raise ValueError("DAA: request not rejectable")
        req["status"] = "REJECTED"
        self.requests[request_id] = _canonical(req)
        return _canonical(req)

    @gl.public.write
    def undetermine_request(self, request_id: str) -> str:
        """Record that the authority could not decide. Creates no authority."""
        req = self._get_request(request_id)
        if gl.message.sender_address.as_hex.lower() != req["authority_source"]:
            raise ValueError("DAA: only the authority source may undetermine")
        if req["status"] != "REQUESTED":
            raise ValueError("DAA: request not undeterminable")
        req["status"] = "UNDETERMINED"
        self.requests[request_id] = _canonical(req)
        return _canonical(req)

    @gl.public.write
    def revoke_award(self, allocation_id: str) -> str:
        award = self._get_award(allocation_id)
        if award["status"] != "AWARDED":
            raise ValueError("DAA: award not revocable")
        if gl.message.sender_address.as_hex.lower() != award["authority_source"]:
            raise ValueError("DAA: only the authority source may revoke")
        award["status"] = "REVOKED"
        self.awards[allocation_id] = _canonical(award)
        return _canonical(award)

    # ---------- downstream verification (the only consumer surface) ----------

    @gl.public.view
    def verify_authority(
        self,
        allocation_id: str,
        actor: str,
        resource: str,
        purpose: str,
        action_amount: str,
        at_timestamp: str,
    ) -> str:
        """Deterministic check that one concrete action lies inside an award."""
        award = self._get_award(allocation_id)
        if not _valid_uint(action_amount):
            raise ValueError("DAA: amount must be positive uint-string")
        if not _valid_int_ts(at_timestamp):
            raise ValueError("DAA: invalid timestamp")

        if award["status"] == "REVOKED":
            return self._deny(allocation_id, action_amount, "AWARD_REVOKED")
        ts = int(at_timestamp)
        if ts > int(award["valid_until"]) or ts < int(award["valid_after"]):
            return self._deny(allocation_id, action_amount, "AWARD_EXPIRED")
        if actor.lower().removeprefix("0x") != award["beneficiary"].lower().removeprefix("0x"):
            return self._deny(allocation_id, action_amount, "BENEFICIARY_MISMATCH")
        if resource != award["resource"]:
            return self._deny(allocation_id, action_amount, "RESOURCE_MISMATCH")
        if purpose != award["purpose"]:
            return self._deny(allocation_id, action_amount, "PURPOSE_MISMATCH")
        if int(action_amount) > int(award["max_authority"]):
            return self._deny(allocation_id, action_amount, "EXCEEDS_AWARD_BOUND")

        return _canonical({
            "allocation_id": allocation_id,
            "decision": "AUTHORIZE",
            "reason_code": "WITHIN_AWARD",
            "amount": action_amount,
        })

    def _deny(self, allocation_id: str, amount: str, reason_code: str) -> str:
        return _canonical({
            "allocation_id": allocation_id,
            "decision": "DENY",
            "reason_code": reason_code,
            "amount": amount,
        })

    # ---------- views ----------

    @gl.public.view
    def get_request(self, request_id: str) -> str:
        return self.requests.get(request_id, "")

    @gl.public.view
    def get_award(self, allocation_id: str) -> str:
        return self.awards.get(allocation_id, "")

    def _get_request(self, request_id: str) -> dict:
        record = self.requests.get(request_id, "")
        if not record:
            raise ValueError("DAA: unknown request")
        return json.loads(record)

    def _get_award(self, allocation_id: str) -> dict:
        record = self.awards.get(allocation_id, "")
        if not record:
            raise ValueError("DAA: unknown award")
        return json.loads(record)
