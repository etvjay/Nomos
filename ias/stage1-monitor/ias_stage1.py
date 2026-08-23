# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
"""IAS Stage 1 — Monitor Account (GenLayer Intelligent Contract).

The first tier of the three-stage Intelligent Account ladder.

Capability: OBSERVE + PROPOSE.
- Embeds SimpleMonitorV3 semantics: direct web fetch, LLM metric extraction
  under comparative-equivalence consensus (tolerance-based), threshold breach
  detection.
- Breaches create PROPOSALS in a registry. The account NEVER moves money:
  the owner reads proposals and executes them through their PPA's gates.

JUDGMENT BOUNDARY: judgment extracts and classifies; it never settles.
Execution is entirely outside this contract, by design.
"""

import json
import typing

from genlayer import *


def _now_iso() -> str:
    dt = getattr(gl.message, "datetime", None)
    if dt:
        return dt
    return gl.message_raw["datetime"]


def _ts(iso: str) -> int:
    import datetime
    txt = iso.strip().replace("Z", "+00:00")
    return int(datetime.datetime.fromisoformat(txt).timestamp())


def _norm(a: str) -> str:
    return (a or "").lower().removeprefix("0x")


class MonitorAccount(gl.Contract):
    """Stage 1: watches the web, proposes when thresholds breach."""

    owner: TreeMap[str, str]

    monitors: TreeMap[str, str]     # monitor_id -> config+state json
    breaches: TreeMap[str, str]     # breach_id -> record
    proposals: TreeMap[str, str]    # proposal_id -> action payload for owner/PPA

    def __init__(self) -> None:
        pass

    @gl.public.write
    def initialize(self, owner: str) -> str:
        if self.owner.get("owner"):
            raise ValueError("IAS1: already initialized")
        if not isinstance(owner, str) or not owner.startswith("0x") or len(owner) != 42:
            raise ValueError("IAS1: invalid owner")
        self.owner["owner"] = _norm(owner)
        self.owner["created"] = _now_iso()
        return "initialized"

    def _assert_owner(self) -> None:
        me = gl.message.sender_address.as_hex.lower().removeprefix("0x")
        if me != self.owner.get("owner"):
            raise ValueError("IAS1: caller is not owner")

    # ---------- monitors ----------
    @gl.public.write
    def create_monitor(self, monitor_id: str, name: str, data_source: str,
                       metric_type: str, threshold_value: str,
                       condition: str, tolerance_percent: str,
                       min_confidence: str = "medium",
                       proposal_template: str = "") -> str:
        """Register an observation. proposal_template is a JSON skeleton with
        {value} placeholder — what the owner's PPA should do on breach."""
        self._assert_owner()
        if self.monitors.get(monitor_id):
            raise ValueError("IAS1: monitor id exists")
        if condition not in ("above", "below", "outside_range"):
            raise ValueError("IAS1: invalid condition")
        cfg = {
            "monitor_id": monitor_id, "name": name,
            "data_source": data_source, "metric_type": metric_type,
            "threshold_value": threshold_value, "condition": condition,
            "tolerance_percent": tolerance_percent,
            "min_confidence": min_confidence,
            "proposal_template": proposal_template,
            "is_active": True,
            "last_value": "", "last_check": "", "last_status": "",
            "created": _now_iso(),
        }
        self.monitors[monitor_id] = json.dumps(cfg)
        return "monitor_created"

    @gl.public.view
    def get_monitor(self, monitor_id: str) -> typing.Any:
        raw = self.monitors.get(monitor_id)
        if not raw:
            raise ValueError("IAS1: monitor not found")
        return json.loads(raw)

    @gl.public.write
    def toggle_monitor(self, monitor_id: str) -> str:
        self._assert_owner()
        raw = self.monitors.get(monitor_id)
        if not raw:
            raise ValueError("IAS1: monitor not found")
        m = json.loads(raw)
        m["is_active"] = not m["is_active"]
        self.monitors[monitor_id] = json.dumps(m)
        return "toggled"

    # ---------- observation (the L1 engine) ----------
    @gl.public.write
    def check_monitor(self, monitor_id: str) -> typing.Any:
        """Fetch source, extract metric via LLM under comparative consensus,
        evaluate threshold, record breach + proposal if breached."""
        raw = self.monitors.get(monitor_id)
        if not raw:
            raise ValueError("IAS1: monitor not found")
        m = json.loads(raw)
        if not m["is_active"]:
            return {"success": False, "error": "monitor inactive"}

        data_source = m["data_source"]
        metric_type = m["metric_type"]
        threshold = m["threshold_value"]
        condition = m["condition"]
        try:
            tolerance = float(m.get("tolerance_percent", "5.0"))
        except (TypeError, ValueError):
            tolerance = 5.0

        def leader_fn() -> typing.Any:
            web_data = gl.nondet.web.render(data_source, mode="text")
            task = (
                f"You are extracting {metric_type} data from a webpage.\n\n"
                f"WEBPAGE CONTENT:\n{web_data[:4000]}\n\n"
                "Extract ONLY the numeric value of the main/current figure.\n"
                "Remove symbols ($, EUR etc), commas, spaces.\n"
                'Respond ONLY as JSON: {"value":"<number>","confidence":"high|medium|low","found":true}\n'
                'If not clearly present: {"found":false,"value":"0","confidence":"none"}'
            )

            _CONF_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3}

        def validator_fn(leaders_res) -> bool:
            my = leader_fn()
            if not hasattr(leaders_res, "calldata"):
                return False
            ld = leaders_res.calldata
            if not my.get("found") or not ld.get("found"):
                return my.get("found") == ld.get("found")
            conf_rank = {"none": 0, "low": 1, "medium": 2, "high": 3}
            floor = conf_rank.get(str(m.get("min_confidence", "medium")), 2)
            if (conf_rank.get(str(ld.get("confidence", "none")), 0) < floor
                    or conf_rank.get(str(my.get("confidence", "none")), 0) < floor):
                return False
            try:
                ln, vn = float(ld.get("value", "0")), float(my.get("value", "0"))
                delta_ok = abs(ln - vn) <= abs(ln * (tolerance / 100.0))
            except (TypeError, ValueError):
                delta_ok = str(ld.get("value", "")).strip() == str(my.get("value", "")).strip()
            return delta_ok

            res = gl.vm.run_nondet(leader_fn, validator_fn)
            return res

        result = leader_fn()

        m["last_check"] = _now_iso()
        m["last_value"] = str(result.get("value", ""))
        m["last_confidence"] = str(result.get("confidence", "none"))
        m["last_status"] = "success" if result.get("found") else "extraction_failed"

        if not result.get("found"):
            self.monitors[monitor_id] = json.dumps(m)
            return {"success": False, "error": "extraction_failed",
                    "monitor_id": monitor_id}

        value_str = str(result.get("value", "0"))
        breach = self._check_breach(value_str, threshold, condition)

        out = {"success": True, "monitor_id": monitor_id,
               "value": value_str, "breach": breach}

        if breach:
            breach_id = f"BR-{monitor_id}-{_ts(_now_iso())}"
            rec = {"breach_id": breach_id, "monitor_id": monitor_id,
                   "name": m["name"], "value": value_str,
                   "confidence": str(result.get("confidence", "none")),
                   "threshold": threshold, "condition": condition,
                   "detected": _now_iso(), "status": "OPEN"}
            self.breaches[breach_id] = json.dumps(rec)

            # Proposal: what should happen next — payload only. Execution
            # happens OUTSIDE this account, through the owner's PPA gates.
            template = m.get("proposal_template", "")
            payload = template.replace("{value}", value_str) if template else ""
            proposal_id = f"PROP-{breach_id}"
            prop = {"proposal_id": proposal_id, "breach_id": breach_id,
                    "monitor_id": monitor_id, "kind": "threshold_breach",
                    "observed_value": value_str, "threshold": threshold,
                    "action_payload": payload, "status": "PROPOSED",
                    "proposed_at": _now_iso()}
            self.proposals[proposal_id] = json.dumps(prop)
            out["proposal_id"] = proposal_id

        self.monitors[monitor_id] = json.dumps(m)
        return out

    def _check_breach(self, value: str, threshold: str, condition: str) -> bool:
        try:
            v, t = float(value), float(threshold)
        except (TypeError, ValueError):
            return False
        if condition == "above":
            return v > t
        if condition == "below":
            return v < t
        if condition == "outside_range":
            parts = threshold.split("|")
            if len(parts) != 2:
                return False
            lo, hi = float(parts[0]), float(parts[1])
            return v < lo or v > hi
        return False

    # ---------- proposals & breaches ----------
    @gl.public.view
    def get_proposal(self, proposal_id: str) -> typing.Any:
        raw = self.proposals.get(proposal_id)
        if not raw:
            raise ValueError("IAS1: proposal not found")
        return json.loads(raw)

    @gl.public.write
    def mark_executed(self, proposal_id: str, execution_note: str = "") -> str:
        """Owner records that they executed this proposal via their PPA.
        The account cannot execute; it can only remember."""
        self._assert_owner()
        raw = self.proposals.get(proposal_id)
        if not raw:
            raise ValueError("IAS1: proposal not found")
        p = json.loads(raw)
        p["status"] = "EXECUTED"
        p["execution_note"] = execution_note
        self.proposals[proposal_id] = json.dumps(p)
        return "marked_executed"

    @gl.public.view
    def get_breach(self, breach_id: str) -> typing.Any:
        raw = self.breaches.get(breach_id)
        if not raw:
            raise ValueError("IAS1: breach not found")
        return json.loads(raw)
