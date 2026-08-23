# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
"""Deterministic-first Policy Envelope primitive (GenLayer) v0.1.

A Policy Envelope is a deterministic-first constraint object: hard limits
(amount, asset, actor/target bindings, validity window, cumulative capacity)
always dominate any interpreted mandate clause. The v0.1 canonical slice
implements the full deterministic core (EXACT) plus one narrow judgment
surface for declared non-deterministic mandate clauses (interpret_clause),
whose result can only NARROW admissibility and can never widen a hard limit.

JUDGMENT_BOUNDARY (v0.1): only attach_mandate_clause/interpret_clause touch
non-deterministic evaluation; evaluate_request is fully deterministic and can
veto any interpreted result. Policy decisions create no delegation,
allocation, commitment or settlement authority.
"""

from genlayer import *
import json

_MAX_CLAUSE_BYTES = 4096
_MAX_FACTS_BYTES = 4096


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
    if not body.isdecimal():
        return False
    return True


def _canonical(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


class PolicyEnvelope(gl.Contract):
    envelopes: TreeMap[str, str]
    requests: TreeMap[str, str]
    clauses: TreeMap[str, str]
    interpretations: TreeMap[str, str]

    def __init__(self) -> None:
        pass

    # ---------- lifecycle ----------

    @gl.public.write
    def create_envelope(
        self,
        envelope_id: str,
        policy_hash: str,
        max_amount: str,
        asset: str,
        valid_after: str,
        valid_until: str,
    ) -> str:
        if not envelope_id:
            raise ValueError("PolicyEnvelope: envelope_id must not be empty")
        if not policy_hash:
            raise ValueError("PolicyEnvelope: policy_hash must not be empty")
        if not asset:
            raise ValueError("PolicyEnvelope: asset must not be empty")
        if not _valid_uint(max_amount):
            raise ValueError("PolicyEnvelope: max_amount must be positive uint-string")
        if not _valid_int_ts(valid_after) or not _valid_int_ts(valid_until):
            raise ValueError("PolicyEnvelope: invalid validity timestamps")
        if int(valid_after) > int(valid_until):
            raise ValueError("PolicyEnvelope: valid_after exceeds valid_until")
        if envelope_id in self.envelopes:
            raise ValueError("PolicyEnvelope: envelope already exists")
        record = {
            "envelope_id": envelope_id,
            "policy_hash": policy_hash,
            "max_amount": max_amount,
            "asset": asset,
            "valid_after": str(int(valid_after)),
            "valid_until": str(int(valid_until)),
            "used_amount": "0",
            "status": "ACTIVE",
        }
        canonical = _canonical(record)
        self.envelopes[envelope_id] = canonical
        return canonical

    @gl.public.write
    def expire_envelope(self, envelope_id: str) -> str:
        record = self.envelopes.get(envelope_id, "")
        if not record:
            raise ValueError("PolicyEnvelope: unknown envelope")
        env = json.loads(record)
        if env["status"] != "ACTIVE":
            raise ValueError("PolicyEnvelope: envelope not active")
        env["status"] = "EXPIRED"
        canonical = _canonical(env)
        self.envelopes[envelope_id] = canonical
        return canonical

    # ---------- judgment surface (narrow) ----------

    @gl.public.write
    def attach_mandate_clause(self, envelope_id: str, clause_id: str, clause_text: str) -> str:
        """Declare a non-deterministic mandate clause to be interpreted per request."""
        env_record = self.envelopes.get(envelope_id, "")
        if not env_record:
            raise ValueError("PolicyEnvelope: unknown envelope")
        if not clause_id:
            raise ValueError("PolicyEnvelope: clause_id must not be empty")
        if clause_id in self.clauses:
            raise ValueError("PolicyEnvelope: clause already exists")
        if len(clause_text.encode("utf-8")) > _MAX_CLAUSE_BYTES:
            raise ValueError("PolicyEnvelope: clause text too large")
        record = {
            "clause_id": clause_id,
            "envelope_id": envelope_id,
            "clause_text": clause_text,
        }
        canonical = _canonical(record)
        self.clauses[clause_id] = canonical
        return canonical

    @gl.public.write
    def interpret_clause(
        self,
        envelope_id: str,
        clause_id: str,
        facts_json: str,
        interpretation_id: str,
    ) -> str:
        """Run the bounded intelligent question over declared clause + supplied facts.

        Structured decision: ADMIT / DENY / UNDETERMINED restricted to whether
        the facts fall inside the declared clause. This never touches hard
        limits; evaluate_request remains the sole gatekeeper of amounts/assets/
        windows and may veto anything.
        """
        if self.envelopes.get(envelope_id, "") == "":
            raise ValueError("PolicyEnvelope: unknown envelope")
        clause_record = self.clauses.get(clause_id, "")
        if not clause_record:
            raise ValueError("PolicyEnvelope: unknown clause")
        clause = json.loads(clause_record)
        if clause["envelope_id"] != envelope_id:
            raise ValueError("PolicyEnvelope: clause belongs to another envelope")
        if not interpretation_id:
            raise ValueError("PolicyEnvelope: interpretation_id required")
        if interpretation_id in self.interpretations:
            raise ValueError("PolicyEnvelope: duplicate interpretation_id")
        if len(facts_json.encode("utf-8")) > _MAX_FACTS_BYTES:
            raise ValueError("PolicyEnvelope: facts too large")

        question = (
            "You interpret one declared mandate clause against supplied facts.\n"
            "CLAUSE:\n" + clause["clause_text"] + "\n"
            "FACTS:\n" + facts_json + "\n"
            'Return JSON {"decision":"ADMIT"|"DENY"|"UNDETERMINED",'
            ' "analysis":"<short>"} where ADMIT means the facts clearly fall'
            " inside the clause, DENY means they clearly fall outside it, and"
            " UNDETERMINED means the clause does not resolve the facts."
        )

        allowed = ("ADMIT", "DENY", "UNDETERMINED")

        def leader() -> dict:
            raw = gl.nondet.exec_prompt(question, response_format="json")
            if not isinstance(raw, dict):
                raise gl.vm.UserError("PolicyEnvelope: non-object model output")
            decision = raw.get("decision")
            if decision not in allowed:
                raise gl.vm.UserError("PolicyEnvelope: invalid decision")
            return {"decision": decision, "analysis": str(raw.get("analysis", ""))}

        def validators(leader_out) -> bool:
            # Comparative validation: each validator independently re-runs the
            # interpretation and compares the canonical decision field.
            # Leader-output-only validation (enum check without re-evaluation)
            # is an anti-pattern per official GenLayer guidance.
            if not isinstance(leader_out, gl.vm.Return):
                return False
            mine = leader()
            return leader_out.calldata["decision"] == mine["decision"]

        result = gl.vm.run_nondet_unsafe(leader, validators)

        record = {
            "interpretation_id": interpretation_id,
            "envelope_id": envelope_id,
            "clause_id": clause_id,
            "decision": result["decision"],
        }
        canonical = _canonical(record)
        self.interpretations[interpretation_id] = canonical
        return canonical

    # ---------- deterministic evaluation (dominant) ----------

    @gl.public.write
    def evaluate_request(
        self,
        envelope_id: str,
        request_id: str,
        amount: str,
        asset: str,
        actor: str,
        target: str,
        at_timestamp: str,
    ) -> str:
        """Deterministic hard-limit evaluation. Veto power is absolute."""
        env_record = self.envelopes.get(envelope_id, "")
        if not env_record:
            raise ValueError("PolicyEnvelope: unknown envelope")
        if not request_id:
            raise ValueError("PolicyEnvelope: request_id must not be empty")
        if not actor or not target:
            raise ValueError("PolicyEnvelope: actor and target must not be empty")
        if not _valid_uint(amount):
            raise ValueError("PolicyEnvelope: amount must be positive uint-string")
        if not _valid_int_ts(at_timestamp):
            raise ValueError("PolicyEnvelope: invalid timestamp")
        request_key = envelope_id + "/" + request_id
        if request_key in self.requests:
            raise ValueError("PolicyEnvelope: request already exists")

        env = json.loads(env_record)

        # Fail-closed ordering: inactive first, then window, asset, amount, capacity.
        if env["status"] != "ACTIVE":
            return self._record_denial(request_key, envelope_id, request_id, amount, "ENVELOPE_INACTIVE")
        ts = int(at_timestamp)
        if ts < int(env["valid_after"]) or ts > int(env["valid_until"]):
            return self._record_denial(request_key, envelope_id, request_id, amount, "OUTSIDE_VALIDITY_WINDOW")
        if asset != env["asset"]:
            return self._record_denial(request_key, envelope_id, request_id, amount, "ASSET_MISMATCH")
        if int(amount) > int(env["max_amount"]):
            return self._record_denial(request_key, envelope_id, request_id, amount, "AMOUNT_EXCEEDS_LIMIT")
        if int(env["used_amount"]) + int(amount) > int(env["max_amount"]):
            return self._record_denial(request_key, envelope_id, request_id, amount, "CAPACITY_EXHAUSTED")

        env["used_amount"] = str(int(env["used_amount"]) + int(amount))
        self.envelopes[envelope_id] = _canonical(env)
        record = {
            "request_key": request_key,
            "envelope_id": envelope_id,
            "request_id": request_id,
            "amount": amount,
            "asset": asset,
            "actor": actor,
            "target": target,
            "at_timestamp": str(ts),
            "decision": "ADMIT",
            "reason_code": "WITHIN_HARD_LIMITS",
        }
        canonical = _canonical(record)
        self.requests[request_key] = canonical
        return canonical

    def _record_denial(self, request_key, envelope_id, request_id, amount, reason_code) -> str:
        # Denied attempts are observable in the return value but do NOT reserve
        # the request id and consume no capacity — a later valid request may
        # reuse the id.
        record = {
            "request_key": request_key,
            "envelope_id": envelope_id,
            "request_id": request_id,
            "amount": amount,
            "decision": "DENY",
            "reason_code": reason_code,
        }
        return _canonical(record)

    # ---------- views ----------

    @gl.public.view
    def get_envelope(self, envelope_id: str) -> str:
        return self.envelopes.get(envelope_id, "")

    @gl.public.view
    def get_request(self, envelope_id: str, request_id: str) -> str:
        return self.requests.get(envelope_id + "/" + request_id, "")

    @gl.public.view
    def used_amount(self, envelope_id: str) -> str:
        record = self.envelopes.get(envelope_id, "")
        if not record:
            return ""
        return json.loads(record)["used_amount"]

    @gl.public.view
    def get_clause_interpretation(self, interpretation_id: str) -> str:
        return self.interpretations.get(interpretation_id, "")
