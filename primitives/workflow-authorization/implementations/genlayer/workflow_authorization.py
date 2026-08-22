# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
"""Deterministic Workflow Authorization primitive (GenLayer) v0.1.

Composes Path (standing bounded delegated authority) and Pact (specific
accepted economic relation) around a propose/accept/execute chain.

JUDGMENT_BOUNDARY = NONE for the v0.1 canonical slice. Reference continuity,
capability membership, quantitative bounds, expiry, revocation, and exact
Pact binding are fully deterministic. Substantive purpose-fit judgment is
delegated to Policy Envelope's interpret_clause surface (or a future
declared judgment step); it can never relax the deterministic gates here.

Authority separation (Article V): Path does not allocate capital; Pact does
not guarantee backing capital or create standing delegation. The only
output is an authorization decision for a specific action.
"""

from genlayer import *
import json

_MAX_TERMS_BYTES = 4096


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


class WorkflowAuthorization(gl.Contract):
    paths: TreeMap[str, str]
    pacts: TreeMap[str, str]

    def __init__(self) -> None:
        pass

    # ---------- Path: standing bounded authority ----------

    @gl.public.write
    def grant_path(
        self,
        path_id: str,
        principal: str,
        agent: str,
        purpose_scope: str,
        max_per_action: str,
        asset: str,
        valid_after: str,
        valid_until: str,
    ) -> str:
        if not path_id or not principal or not agent or not purpose_scope or not asset:
            raise ValueError("WorkflowAuthorization: empty required field")
        if principal == agent:
            raise ValueError("WorkflowAuthorization: self-delegation is not permitted")
        if not _valid_uint(max_per_action):
            raise ValueError("WorkflowAuthorization: max_per_action must be positive uint-string")
        if not _valid_int_ts(valid_after) or not _valid_int_ts(valid_until):
            raise ValueError("WorkflowAuthorization: invalid validity timestamps")
        if int(valid_after) > int(valid_until):
            raise ValueError("WorkflowAuthorization: valid_after exceeds valid_until")
        if path_id in self.paths:
            raise ValueError("WorkflowAuthorization: path already exists")
        record = {
            "path_id": path_id,
            "principal": principal,
            "agent": agent,
            "purpose_scope": purpose_scope,
            "max_per_action": max_per_action,
            "asset": asset,
            "valid_after": str(int(valid_after)),
            "valid_until": str(int(valid_until)),
            "status": "ACTIVE",
        }
        canonical = _canonical(record)
        self.paths[path_id] = canonical
        return canonical

    @gl.public.write
    def revoke_path(self, path_id: str) -> str:
        path = self._get_path_record(path_id)
        if path["status"] != "ACTIVE":
            raise ValueError("WorkflowAuthorization: path not active")
        path["status"] = "REVOKED"
        canonical = _canonical(path)
        self.paths[path_id] = canonical
        return canonical

    # ---------- Pact: specific accepted economic relation ----------

    @gl.public.write
    def propose_pact(
        self,
        pact_id: str,
        path_id: str,
        workflow_ref: str,
        terms_json: str,
        proposed_at: str,
    ) -> str:
        path = self._live_path(path_id, proposed_at)
        if not pact_id:
            raise ValueError("WorkflowAuthorization: pact_id must not be empty")
        if not workflow_ref:
            raise ValueError("WorkflowAuthorization: workflow_ref must not be empty")
        if pact_id in self.pacts:
            raise ValueError("WorkflowAuthorization: pact already exists")
        if len(terms_json.encode("utf-8")) > _MAX_TERMS_BYTES:
            raise ValueError("WorkflowAuthorization: terms too large")
        try:
            terms = json.loads(terms_json)
        except Exception:
            raise ValueError("WorkflowAuthorization: malformed terms JSON")
        if not isinstance(terms, dict):
            raise ValueError("WorkflowAuthorization: terms must be an object")
        record = {
            "pact_id": pact_id,
            "path_id": path_id,
            "principal": path["principal"],
            "workflow_ref": workflow_ref,
            "terms": terms,
            "status": "PROPOSED",
        }
        canonical = _canonical(record)
        self.pacts[pact_id] = canonical
        return canonical

    @gl.public.write
    def accept_pact(self, pact_id: str) -> str:
        pact = self._get_pact_record(pact_id)
        # Only the Path principal may accept: exact authority continuity.
        # Addresses normalized to bare lowercase hex (0x-prefix and EIP-55
        # checksum agnostic).
        sender = gl.message.sender_address.as_hex.lower().removeprefix("0x")
        if sender != pact["principal"].lower().removeprefix("0x"):
            raise ValueError("WorkflowAuthorization: only the path principal may accept")
        if pact["status"] != "PROPOSED":
            raise ValueError("WorkflowAuthorization: pact not proposable")
        # A blocked decision cannot produce an executable Pact: the underlying
        # Path must still be live at acceptance time.
        path = self._get_path_record(pact["path_id"])
        if path["status"] != "ACTIVE":
            raise ValueError("WorkflowAuthorization: path is not active")
        pact["status"] = "ACCEPTED"
        canonical = _canonical(pact)
        self.pacts[pact_id] = canonical
        return canonical

    @gl.public.write
    def void_pact(self, pact_id: str) -> str:
        pact = self._get_pact_record(pact_id)
        if pact["status"] in ("EXECUTED", "VOID"):
            raise ValueError("WorkflowAuthorization: pact already terminal")
        pact["status"] = "VOID"
        canonical = _canonical(pact)
        self.pacts[pact_id] = canonical
        return canonical

    # ---------- Execution gate ----------

    @gl.public.write
    def execute_pact(self, pact_id: str, action_amount: str, at_timestamp: str) -> str:
        """Deterministic authorization decision for one concrete action.

        Returns an AUTHORIZE decision only when every deterministic gate holds.
        This does NOT move capital; downstream primitives (DAL, settlement)
        consume the decision.
        """
        pact = self._get_pact_record(pact_id)
        path = self._get_path_record(pact["path_id"])
        if not _valid_uint(action_amount):
            raise ValueError("WorkflowAuthorization: amount must be positive uint-string")
        if not _valid_int_ts(at_timestamp):
            raise ValueError("WorkflowAuthorization: invalid timestamp")

        # Fail-closed gate ordering.
        if pact["status"] == "VOID" or pact["status"] == "EXECUTED":
            raise ValueError("WorkflowAuthorization: pact is terminal")
        if pact["status"] != "ACCEPTED":
            return self._deny(pact_id, action_amount, "PACT_NOT_ACCEPTED")
        if path["status"] != "ACTIVE":
            return self._deny(pact_id, action_amount, "PATH_NOT_ACTIVE")
        ts = int(at_timestamp)
        if ts < int(path["valid_after"]) or ts > int(path["valid_until"]):
            return self._deny(pact_id, action_amount, "PATH_EXPIRED")
        if int(action_amount) > int(path["max_per_action"]):
            return self._deny(pact_id, action_amount, "EXCEEDS_PATH_BOUND")

        pact["status"] = "EXECUTED"
        self.pacts[pact_id] = _canonical(pact)
        record = {
            "pact_id": pact_id,
            "decision": "AUTHORIZE",
            "reason_code": "WITHIN_DELEGATED_AUTHORITY",
            "amount": action_amount,
        }
        return _canonical(record)

    def _deny(self, pact_id: str, amount: str, reason_code: str) -> str:
        return _canonical(
            {"pact_id": pact_id, "decision": "DENY", "reason_code": reason_code, "amount": amount}
        )

    # ---------- views ----------

    @gl.public.view
    def get_path(self, path_id: str) -> str:
        return self.paths.get(path_id, "")

    @gl.public.view
    def get_pact(self, pact_id: str) -> str:
        return self.pacts.get(pact_id, "")

    def _get_path_record(self, path_id: str) -> dict:
        record = self.paths.get(path_id, "")
        if not record:
            raise ValueError("WorkflowAuthorization: unknown path")
        return json.loads(record)

    def _get_pact_record(self, pact_id: str) -> dict:
        record = self.pacts.get(pact_id, "")
        if not record:
            raise ValueError("WorkflowAuthorization: unknown pact")
        return json.loads(record)

    def _live_path(self, path_id: str, at_timestamp: str = None) -> dict:
        path = self._get_path_record(path_id)
        if path["status"] != "ACTIVE":
            raise ValueError("WorkflowAuthorization: path is not active")
        if at_timestamp is not None:
            ts = int(at_timestamp)
            if ts < int(path["valid_after"]) or ts > int(path["valid_until"]):
                raise ValueError("WorkflowAuthorization: path is outside validity window")
        return path
