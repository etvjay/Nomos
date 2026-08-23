# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
"""IAS Stage 2 — Coordinator Account (GenLayer Intelligent Contract).

Second tier: Layer 1 (monitor) + Layer 2 (coordinator).

Everything Stage 1 does, plus:
- Multi-signal correlation: a coordinator policy requires N-of-M monitors in
  the same signal group to breach within a correlation window before the
  account escalates from OBSERVED to CONFIRMED.
- Confidence scoring: deterministic scoring from agreement count, tolerance
  margins, and monitor weights.
- Confirmed signals escalate to ESCALATED proposals with higher conviction
  payload; unconfirmed breaches stay PROPOSED for human review.

JUDGMENT BOUNDARY unchanged: judgment extracts and correlates; it never settles.
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


class CoordinatorAccount(gl.Contract):
    """Stage 2: monitors, correlates multi-signal breaches, scores confidence."""

    owner: TreeMap[str, str]

    monitors: TreeMap[str, str]
    breaches: TreeMap[str, str]
    proposals: TreeMap[str, str]

    # --- L2 additions ---
    groups: TreeMap[str, str]        # group_id -> {monitor_ids, n_of_m, window_sec}
    correlations: TreeMap[str, str]  # correlation_id -> record

    def __init__(self) -> None:
        pass

    @gl.public.write
    def initialize(self, owner: str) -> str:
        if self.owner.get("owner"):
            raise ValueError("IAS2: already initialized")
        self.owner["owner"] = _norm(owner)
        self.owner["created"] = _now_iso()
        return "initialized"

    def _assert_owner(self) -> None:
        me = gl.message.sender_address.as_hex.lower().removeprefix("0x")
        if me != self.owner.get("owner"):
            raise ValueError("IAS2: caller is not owner")

    # ---------- monitors (same as Stage 1) ----------
    @gl.public.write
    def create_monitor(self, monitor_id: str, name: str, data_source: str,
                       metric_type: str, threshold_value: str,
                       condition: str, tolerance_percent: str,
                       signal_group: str = "",
                       weight: str = "1",
                       proposal_template: str = "") -> str:
        self._assert_owner()
        if self.monitors.get(monitor_id):
            raise ValueError("IAS2: monitor id exists")
        if condition not in ("above", "below"):
            raise ValueError("IAS2: invalid condition")
        cfg = {
            "monitor_id": monitor_id, "name": name,
            "data_source": data_source, "metric_type": metric_type,
            "threshold_value": threshold_value, "condition": condition,
            "tolerance_percent": tolerance_percent,
            "signal_group": signal_group,
            "weight": weight,
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
            raise ValueError("IAS2: monitor not found")
        return json.loads(raw)

    # ---------- signal groups (L2) ----------
    @gl.public.write
    def create_signal_group(self, group_id: str, monitor_ids_json: str,
                            n_of_m: int, window_seconds: int) -> str:
        """Correlation policy: at least n_of_m of these monitors must breach
        within window_seconds for the signal to be CONFIRMED."""
        self._assert_owner()
        if self.groups.get(group_id):
            raise ValueError("IAS2: group exists")
        ids = json.loads(monitor_ids_json)
        if not isinstance(ids, list) or len(ids) == 0:
            raise ValueError("IAS2: empty group")
        if n_of_m < 1 or n_of_m > len(ids):
            raise ValueError("IAS2: invalid n_of_m")
        g = {"group_id": group_id, "monitor_ids": ids,
             "n_of_m": n_of_m, "window_seconds": window_seconds,
             "created": _now_iso()}
        self.groups[group_id] = json.dumps(g)
        return "group_created"

    @gl.public.view
    def get_group(self, group_id: str) -> typing.Any:
        raw = self.groups.get(group_id)
        if not raw:
            raise ValueError("IAS2: group not found")
        return json.loads(raw)

    # ---------- observation (L1) ----------
    @gl.public.write
    def check_monitor(self, monitor_id: str) -> typing.Any:
        raw = self.monitors.get(monitor_id)
        if not raw:
            raise ValueError("IAS2: monitor not found")
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
                'Respond ONLY as JSON: {"value":"<number>","confidence":"high|medium|low","found":true}\n'
                'If not clearly present: {"found":false,"value":"0","confidence":"none"}'
            )

            def validator_fn(leaders_res) -> bool:
                my = leader_fn()
                if not hasattr(leaders_res, "calldata"):
                    return False
                ld = leaders_res.calldata
                if not my.get("found") or not ld.get("found"):
                    return my.get("found") == ld.get("found")
                try:
                    ln, vn = float(ld.get("value", "0")), float(my.get("value", "0"))
                    ok = abs(ln - vn) <= abs(ln * (tolerance / 100.0))
                except (TypeError, ValueError):
                    ok = str(ld.get("value", "")) == str(my.get("value", ""))
                return ok

            res = gl.vm.run_nondet(leader_fn, validator_fn)
            return res

        result = leader_fn()

        m["last_check"] = _now_iso()
        m["last_value"] = str(result.get("value", ""))
        m["last_status"] = "success" if result.get("found") else "extraction_failed"

        if not result.get("found"):
            self.monitors[monitor_id] = json.dumps(m)
            return {"success": False, "error": "extraction_failed"}

        value_str = str(result.get("value", "0"))
        try:
            v, t = float(value_str), float(threshold)
        except (TypeError, ValueError):
            self.monitors[monitor_id] = json.dumps(m)
            return {"success": False, "error": "parse_failed"}

        breach = (v > t) if condition == "above" else (v < t)
        out = {"success": True, "monitor_id": monitor_id,
               "value": value_str, "breach": breach}

        if breach:
            breach_id = f"BR-{monitor_id}-{_ts(_now_iso())}"
            rec = {"breach_id": breach_id, "monitor_id": monitor_id,
                   "signal_group": m["signal_group"], "weight": m["weight"],
                   "value": value_str, "threshold": threshold,
                   "detected": _now_iso(), "status": "OPEN"}
            self.breaches[breach_id] = json.dumps(rec)

            template = m.get("proposal_template", "")
            payload = template.replace("{value}", value_str) if template else ""
            proposal_id = f"PROP-{breach_id}"
            prop = {"proposal_id": proposal_id, "breach_id": breach_id,
                    "monitor_id": monitor_id,
                    "signal_group": m["signal_group"],
                    "kind": "threshold_breach",
                    "observed_value": value_str,
                    "status": "OBSERVED",   # L1 verdict only
                    "action_payload": payload,
                    "proposed_at": _now_iso()}
            self.proposals[proposal_id] = json.dumps(prop)
            out["proposal_id"] = proposal_id

        self.monitors[monitor_id] = json.dumps(m)
        return out

    # ---------- correlation (L2 engine) ----------
    @gl.public.write
    def evaluate_signal_group(self, group_id: str) -> typing.Any:
        """Correlate recent breaches across the group's monitors within the
        time window. If n_of_m reached: create an ESCALATED (confirmed)
        proposal with aggregated confidence score. Deterministic arithmetic
        over recorded breaches; no additional judgment call needed here."""
        self._resolve_actor()
        raw = self.groups.get(group_id)
        if not raw:
            raise ValueError("IAS2: group not found")
        g = json.loads(raw)
        now = _ts(_now_iso())
        window_start = now - int(g["window_seconds"])

        breached_in_window = []
        total_weight = 0
        hit_weight = 0
        for mid in g["monitor_ids"]:
            mraw = self.monitors.get(mid)
            if not mraw:
                continue
            m = json.loads(mraw)
            w = float(m.get("weight", "1"))
            total_weight += w
            # find latest OPEN breach for this monitor inside window
            found = False
            for k in self.breaches.keys():
                b = json.loads(self.breaches[k])
                if b["monitor_id"] == mid and b["status"] == "OPEN":
                    if _ts(b["detected"]) >= window_start:
                        found = True
                        break
            if found:
                breached_in_window.append(mid)
                hit_weight += w

        n = len(breached_in_window)
        confirmed = n >= g["n_of_m"]
        confidence = round(hit_weight / total_weight, 4) if total_weight > 0 else 0.0

        corr_id = f"CORR-{group_id}-{now}"
        rec = {"correlation_id": corr_id, "group_id": group_id,
               "breached_monitors": breached_in_window,
               "n_breached": n, "n_required": g["n_of_m"],
               "window_seconds": g["window_seconds"],
               "confidence": confidence,
               "verdict": "CONFIRMED" if confirmed else "INSUFFICIENT_SIGNAL",
               "evaluated": _now_iso()}
        self.correlations[corr_id] = json.dumps(rec)

        escalated_id = None
        if confirmed:
            # merge action payloads from contributing proposals
            merged = []
            for mid in breached_in_window:
                for k in self.proposals.keys():
                    p = json.loads(self.proposals[k])
                    if p["monitor_id"] == mid and p["status"] == "OBSERVED":
                        p["status"] = "ESCALATED"
                        p["correlation_id"] = corr_id
                        self.proposals[k] = json.dumps(p)
                        if p.get("action_payload"):
                            merged.append(p["action_payload"])

            escalated_id = f"ESC-{corr_id}"
            esc = {"proposal_id": escalated_id,
                   "kind": "confirmed_signal",
                   "group_id": group_id,
                   "correlation_id": corr_id,
                   "confidence": confidence,
                   "contributing_proposals": [
                       json.loads(self.proposals[k])["proposal_id"]
                       for k in self.proposals.keys()
                       if json.loads(self.proposals[k]).get("correlation_id") == corr_id],
                   "merged_action_payloads": merged,
                   "status": "ESCALATED",
                   "escalated_at": _now_iso()}
            self.proposals[escalated_id] = json.dumps(esc)

        return {"correlation_id": corr_id, "n_breached": n,
                "n_required": g["n_of_m"], "confidence": confidence,
                "confirmed": confirmed, "escalated_proposal": escalated_id}

    def _resolve_actor(self) -> None:
        me = gl.message.sender_address.as_hex.lower().removeprefix("0x")
        if me != self.owner.get("owner"):
            raise ValueError("IAS2: caller is not owner")

    # ---------- views ----------
    @gl.public.view
    def get_proposal(self, proposal_id: str) -> typing.Any:
        raw = self.proposals.get(proposal_id)
        if not raw:
            raise ValueError("IAS2: proposal not found")
        return json.loads(raw)

    @gl.public.view
    def get_correlation(self, correlation_id: str) -> typing.Any:
        raw = self.correlations.get(correlation_id)
        if not raw:
            raise ValueError("IAS2: correlation not found")
        return json.loads(raw)

    @gl.public.write
    def mark_executed(self, proposal_id: str, execution_note: str = "") -> str:
        self._assert_owner()
        raw = self.proposals.get(proposal_id)
        if not raw:
            raise ValueError("IAS2: proposal not found")
        p = json.loads(raw)
        p["status"] = "EXECUTED"
        p["execution_note"] = execution_note
        self.proposals[proposal_id] = json.dumps(p)
        return "marked_executed"
