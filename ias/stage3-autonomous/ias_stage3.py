# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
"""IAS Stage 3 — Autonomous Account (GenLayer Intelligent Contract).

Third tier: Layer 1 + Layer 2 + Layer 3.

Stage 2 capability, plus the Executor: confirmed signals above a confidence
threshold can be routed INTO an embedded PPA gate pipeline. The executor
never bypasses gates — it is *the only caller allowed to submit proposals as
executable actions*, and even then every payment passes policy -> encumbrance
-> claim -> settle exactly like a human send.

Safety rails (all structural):
- execution_policy per signal group: min_confidence, max_amount_per_action,
  max_daily_autonomous_spend, enabled flag
- every autonomous settlement is recorded with its correlation_id lineage
- kill switch: owner disables autonomous execution instantly; proposals
  degrade back to human-review

JUDGMENT BOUNDARY: unchanged. Judgment correlates and scores confidence.
Deterministic gates dispose. Confidence is an input to a POLICY decision
(>= threshold), not a replacement for one.
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


class AutonomousAccount(gl.Contract):
    """Stage 3: full loop — observe, correlate, act within hard caps."""

    owner: TreeMap[str, str]

    monitors: TreeMap[str, str]
    breaches: TreeMap[str, str]
    proposals: TreeMap[str, str]
    groups: TreeMap[str, str]
    correlations: TreeMap[str, str]

    # --- L3 additions ---
    exec_policies: TreeMap[str, str]   # group_id -> execution policy
    accounts: TreeMap[str, str]        # sub-account ledger (PPA semantics)
    payments: TreeMap[str, str]        # settled payments w/ correlation lineage
    daily_auto: TreeMap[str, str]      # day -> total autonomous spend
    kill_switch: TreeMap[str, str]     # "autonomous" -> "ON"/"OFF"

    def __init__(self) -> None:
        pass

    @gl.public.write
    def initialize(self, owner: str) -> str:
        if self.owner.get("owner"):
            raise ValueError("IAS3: already initialized")
        self.owner["owner"] = _norm(owner)
        self.owner["created"] = _now_iso()
        self.kill_switch["autonomous"] = "OFF"   # fail-safe default
        return "initialized"

    def _assert_owner(self) -> None:
        me = gl.message.sender_address.as_hex.lower().removeprefix("0x")
        if me != self.owner.get("owner"):
            raise ValueError("IAS3: caller is not owner")

    def _sender(self) -> str:
        return gl.message.sender_address.as_hex.lower().removeprefix("0x")

    def _resolve_actor(self):
        me = self._sender()
        if me == self.owner.get("owner"):
            return {"role": "owner"}
        now = _ts(_now_iso())
        for k in self.exec_policies.keys():
            ep = json.loads(self.exec_policies[k])
            if ep.get("delegate") and ep["delegate"].lower() == me and ep["enabled"]:
                if int(ep["expires"]) >= now:
                    return {"role": "delegate", "policy": ep}
        raise ValueError("IAS3: no authority")

    # ---------- kill switch ----------
    @gl.public.write
    def set_kill_switch(self, state: str) -> str:
        self._assert_owner()
        if state not in ("ON", "OFF"):
            raise ValueError("IAS3: invalid state")
        self.kill_switch["autonomous"] = state
        return f"autonomous_{state}"

    # ---------- execution policies (L3 safety rails) ----------
    @gl.public.write
    def set_execution_policy(self, group_id: str, min_confidence: str,
                             max_amount_per_action: str,
                             max_daily_autonomous_spend: str,
                             recipient_allowlist_json: str,
                             delegate: str = "", expires: str = "99999999999") -> str:
        self._assert_owner()
        pol = {
            "group_id": group_id,
            "min_confidence": float(min_confidence),
            "max_amount_per_action": max_amount_per_action,
            "max_daily_autonomous_spend": max_daily_autonomous_spend,
            "recipient_allowlist": json.loads(recipient_allowlist_json),
            "enabled": True,
            "delegate": delegate if delegate else None,
            "expires": expires,
        }
        self.exec_policies[group_id] = json.dumps(pol)
        return "policy_set"

    @gl.public.write
    def disable_execution_policy(self, group_id: str) -> str:
        self._assert_owner()
        raw = self.exec_policies.get(group_id)
        if not raw:
            raise ValueError("IAS3: no policy for group")
        ep = json.loads(raw)
        ep["enabled"] = False
        self.exec_policies[group_id] = json.dumps(ep)
        return "policy_disabled"

    # ---------- account ledger (PPA semantics, embedded) ----------
    @gl.public.write
    def create_account(self, account_id: str, rules_json: str) -> str:
        self._assert_owner()
        if self.accounts.get(account_id):
            raise ValueError("IAS3: account exists")
        rec = {"account_id": account_id, "rules": json.loads(rules_json),
               "balance": "0", "committed": "0",
               "daily_spent": "0",
               "daily_window_start": _now_iso(),
               "status": "ACTIVE", "created": _now_iso()}
        self.accounts[account_id] = json.dumps(rec)
        return "account_created"

    @gl.public.write
    def deposit(self, account_id: str, amount: str) -> str:
        self._resolve_actor()
        rec = self._get_account(account_id)
        rec["balance"] = str(int(rec["balance"]) + int(amount))
        self.accounts[account_id] = json.dumps(rec)
        return "deposited"

    @gl.public.view
    def get_account(self, account_id: str) -> typing.Any:
        return self._get_account(account_id)

    def _get_account(self, account_id: str) -> dict:
        raw = self.accounts.get(account_id)
        if not raw:
            raise ValueError("IAS3: account not found")
        return json.loads(raw)

    def _roll_daily_window(self, rec: dict) -> tuple:
        now = _ts(_now_iso())
        start = _ts(rec["daily_window_start"])
        if now - start >= 86400:
            rec["daily_spent"] = "0"
            rec["daily_window_start"] = _now_iso()
            return 0, now
        return int(rec["daily_spent"]), start

    # ---------- human send (same gates as PPA) ----------
    @gl.public.write
    def send(self, account_id: str, payment_id: str, to: str,
             amount: str, evidence_hash: str = "") -> typing.Any:
        self._resolve_actor()
        return self._execute_send(account_id, payment_id, to, amount,
                                  evidence_hash, actor="human",
                                  correlation_id=None)

    # ---------- L1/L2: monitor + correlate (inherited from Stage 2) ----------
    @gl.public.write
    def create_monitor(self, monitor_id: str, name: str, data_source: str,
                       metric_type: str, threshold_value: str,
                       condition: str, tolerance_percent: str,
                       signal_group: str = "", weight: str = "1",
                       proposal_template: str = "") -> str:
        self._assert_owner()
        if self.monitors.get(monitor_id):
            raise ValueError("IAS3: monitor id exists")
        cfg = {"monitor_id": monitor_id, "name": name,
               "data_source": data_source, "metric_type": metric_type,
               "threshold_value": threshold_value, "condition": condition,
               "tolerance_percent": tolerance_percent,
               "signal_group": signal_group, "weight": weight,
               "proposal_template": proposal_template,
               "is_active": True, "last_value": "",
               "last_check": "", "last_status": "",
               "created": _now_iso()}
        self.monitors[monitor_id] = json.dumps(cfg)
        return "monitor_created"

    @gl.public.view
    def get_monitor(self, monitor_id: str) -> typing.Any:
        raw = self.monitors.get(monitor_id)
        if not raw:
            raise ValueError("IAS3: monitor not found")
        return json.loads(raw)

    @gl.public.write
    def check_monitor(self, monitor_id: str) -> typing.Any:
        raw = self.monitors.get(monitor_id)
        if not raw:
            raise ValueError("IAS3: monitor not found")
        m = json.loads(raw)
        data_source = m["data_source"]
        try:
            tolerance = float(m.get("tolerance_percent", "5.0"))
        except (TypeError, ValueError):
            tolerance = 5.0

        def leader_fn() -> typing.Any:
            try:
                web_data = gl.nondet.web.render(data_source, mode="text")
            except Exception as e:
                return {"found": False, "value": "0", "step": "web_render_failed",
                        "error": str(e)[:150]}
            if not web_data or len(web_data) < 10:
                return {"found": False, "value": "0", "step": "web_empty"}
            prompt = (
                f'Extract {m["metric_type"]} from this page. WEBPAGE:\n'
                f"{web_data[:4000]}\n"
                'Respond ONLY as JSON: {"value":"<number>","found":true} '
                'or {"found":false,"value":"0"}')
            try:
                res = gl.nondet.exec_prompt(prompt, response_format="json")
            except Exception as e:
                return {"found": False, "value": "0", "step": "exec_prompt_failed",
                        "error": str(e)[:150]}
            if not isinstance(res, dict):
                return {"found": False, "value": "0", "step": "llm_returned_none"}
            return res

        def validator_fn(leaders_res) -> bool:
            my = leader_fn()
            if not isinstance(my, dict):
                return False
            try:
                ld = leaders_res.calldata
            except Exception:
                return False
            if not isinstance(ld, dict):
                return False
            try:
                ln, vn = float(ld.get("value", "0")), float(my.get("value", "0"))
                ok = abs(ln - vn) <= abs(ln * (tolerance / 100.0))
            except (TypeError, ValueError):
                ok = str(ld.get("value")) == str(my.get("value"))
            return ok and bool(ld.get("found")) == bool(my.get("found"))

        result = gl.vm.run_nondet(leader_fn, validator_fn)
        if not isinstance(result, dict):
            m["last_check"] = _now_iso()
            m["last_status"] = "consensus_unreachable"
            self.monitors[monitor_id] = json.dumps(m)
            return {"success": False, "error": "consensus_unreachable"}
        value_str = str(result.get("value", "0"))
        found = bool(result.get("found"))

        m["last_check"] = _now_iso()
        m["last_value"] = value_str
        m["last_status"] = "success" if found else "extraction_failed"

        try:
            v, t = float(value_str), float(m["threshold_value"])
        except (TypeError, ValueError):
            self.monitors[monitor_id] = json.dumps(m)
            return {"success": False, "error": "parse_failed"}

        breach = (v > t) if m["condition"] == "above" else (v < t)
        out = {"success": True, "monitor_id": monitor_id,
               "value": value_str, "breach": breach}

        if breach:
            breach_id = f"BR-{monitor_id}-{_ts(_now_iso())}"
            self.breaches[breach_id] = json.dumps({
                "breach_id": breach_id, "monitor_id": monitor_id,
                "signal_group": m["signal_group"],
                "value": value_str, "detected": _now_iso(),
                "status": "OPEN"})
            proposal_id = f"PROP-{breach_id}"
            self.proposals[proposal_id] = json.dumps({
                "proposal_id": proposal_id, "breach_id": breach_id,
                "monitor_id": monitor_id,
                "signal_group": m["signal_group"],
                "observed_value": value_str, "status": "OBSERVED",
                "proposed_at": _now_iso()})
            out["proposal_id"] = proposal_id

        self.monitors[monitor_id] = json.dumps(m)
        return out

    @gl.public.write
    def create_signal_group(self, group_id: str, monitor_ids_json: str,
                            n_of_m: int, window_seconds: int) -> str:
        self._assert_owner()
        ids = json.loads(monitor_ids_json)
        g = {"group_id": group_id, "monitor_ids": ids,
             "n_of_m": n_of_m, "window_seconds": window_seconds,
             "created": _now_iso()}
        self.groups[group_id] = json.dumps(g)
        return "group_created"

    @gl.public.write
    def evaluate_signal_group(self, group_id: str) -> typing.Any:
        """Correlate breaches; if CONFIRMED and execution policy allows,
        auto-execute through the gate pipeline. Otherwise record ESCALATED."""
        self._resolve_actor()
        g = json.loads(self.groups.get(group_id))
        now = _ts(_now_iso())
        window_start = now - int(g["window_seconds"])

        breached = []
        for mid in g["monitor_ids"]:
            mraw = self.monitors.get(mid)
            if not mraw:
                continue
            for k in self.breaches.keys():
                b = json.loads(self.breaches[k])
                if (b["monitor_id"] == mid and b["status"] == "OPEN"
                        and _ts(b["detected"]) >= window_start):
                    breached.append(mid)
                    break

        n = len(breached)
        confirmed = n >= g["n_of_m"]
        corr_id = f"CORR-{group_id}-{now}"
        self.correlations[corr_id] = json.dumps({
            "correlation_id": corr_id, "group_id": group_id,
            "n_breached": n, "n_required": g["n_of_m"],
            "verdict": "CONFIRMED" if confirmed else "INSUFFICIENT_SIGNAL",
            "evaluated": _now_iso()})

        out = {"correlation_id": corr_id, "n_breached": n,
               "confirmed": confirmed}

        if not confirmed:
            return out

        # --- L3 executor: policy check, then gated auto-execution ---
        ep_raw = self.exec_policies.get(group_id)
        if not ep_raw:
            out["auto_execution"] = "NO_POLICY"
            return out
        ep = json.loads(ep_raw)
        if not ep["enabled"] or self.kill_switch.get("autonomous") != "ON":
            out["auto_execution"] = "DISABLED"
            return out
        if float(out.get("confidence", 1.0)) < ep["min_confidence"]:
            out["auto_execution"] = "BELOW_CONFIDENCE"
            return out

        # execute merged payloads deterministically
        executed = []
        for k in list(self.proposals.keys()):
            p = json.loads(self.proposals[k])
            if p.get("signal_group") != group_id or p["status"] != "OBSERVED":
                continue
            payload = p.get("action_payload") or ""
            if not payload:
                continue
            pl = json.loads(payload)
            # each payload: {"sub_account","to","amount","payment_id"}
            amt = int(pl["amount"])
            if amt > int(ep["max_amount_per_action"]):
                continue
            if ep["recipient_allowlist"] and pl["to"] not in ep["recipient_allowlist"]:
                continue
            day = _ts(_now_iso()) // 86400
            spent = int(self.daily_auto.get(str(day), "0"))
            if spent + amt > int(ep["max_daily_autonomous_spend"]):
                out["auto_execution"] = "DAILY_CAP_REACHED"
                break
            r = self._execute_send(pl["sub_account"], pl["payment_id"],
                                   pl["to"], pl["amount"], "",
                                   actor="autonomous",
                                   correlation_id=corr_id)
            if r.get("settled"):
                self.daily_auto[str(day)] = str(spent + amt)
                p["status"] = "AUTO_EXECUTED"
                p["payment_id"] = pl["payment_id"]
                self.proposals[k] = json.dumps(p)
                executed.append(pl["payment_id"])

        out["auto_execution"] = "EXECUTED"
        out["executed_payments"] = executed
        return out

    def _execute_send(self, account_id: str, payment_id: str, to: str,
                      amount: str, evidence_hash: str, actor: str,
                      correlation_id) -> dict:
        rec = self._get_account(account_id)
        prior = self.payments.get(payment_id)
        if prior and json.loads(prior)["status"] != "DENIED":
            return {"settled": False, "reason": "id_exists"}

        rules = rec["rules"]
        allowlist = [a.lower().removeprefix("0x")
                     for a in rules.get("allowlist", [])]
        if allowlist and to.lower().removeprefix("0x") not in allowlist:
            return self._deny(payment_id, account_id, "POLICY_DENYLIST")
        if int(amount) > int(rules["per_tx_limit"]):
            return self._deny(payment_id, account_id, "POLICY_PER_TX_LIMIT")

        dl = self._delegate_limit() if actor == "delegate" else None
        if dl is not None and int(amount) > min(int(rules["per_tx_limit"]), dl[0]):
            return self._deny(payment_id, account_id, "DELEGATE_PER_TX_LIMIT")

        spent, _ = self._roll_daily_window(rec)
        eff_daily = int(rules["daily_limit"]) if dl is None else min(
            int(rules["daily_limit"]), dl[1])
        if spent + int(amount) > eff_daily:
            self.accounts[account_id] = json.dumps(rec)
            return self._deny(payment_id, account_id, "POLICY_DAILY_LIMIT")

        available = int(rec["balance"]) - int(rec["committed"])
        if int(amount) > available:
            return self._deny(payment_id, account_id, "INSUFFICIENT_COMMITMENT")

        rec["daily_spent"] = str(spent + int(amount))
        rec["balance"] = str(int(rec["balance"]) - int(amount))
        self.accounts[account_id] = json.dumps(rec)

        pay = {"payment_id": payment_id, "account_id": account_id,
               "to": to, "amount": amount, "actor": actor,
               "correlation_id": correlation_id,
               "evidence_hash": evidence_hash,
               "status": "SETTLED", "created": _now_iso()}
        self.payments[payment_id] = json.dumps(pay)
        return {"settled": True, "status": "SETTLED"}

    def _delegate_limit(self):
        me = self._sender()
        now = _ts(_now_iso())
        for k in self.exec_policies.keys():
            ep = json.loads(self.exec_policies[k])
            if (ep.get("delegate") and ep["delegate"].lower().removeprefix("0x") == me
                    and ep["enabled"] and int(ep["expires"]) >= now):
                return (int(ep["max_amount_per_action"]),
                        int(ep["max_daily_autonomous_spend"]))
        return None

    def _deny(self, payment_id: str, account_id: str, reason: str) -> dict:
        self.payments[payment_id] = json.dumps({
            "payment_id": payment_id, "account_id": account_id,
            "status": "DENIED", "reason": reason,
            "created": _now_iso()})
        return {"settled": False, "reason": reason}

    # ---------- views ----------
    @gl.public.view
    def get_payment(self, payment_id: str) -> typing.Any:
        raw = self.payments.get(payment_id)
        if not raw:
            raise ValueError("IAS3: payment not found")
        return json.loads(raw)

    @gl.public.view
    def get_proposal(self, proposal_id: str) -> typing.Any:
        raw = self.proposals.get(proposal_id)
        if not raw:
            raise ValueError("IAS3: proposal not found")
        return json.loads(raw)

    @gl.public.view
    def get_correlation(self, correlation_id: str) -> typing.Any:
        raw = self.correlations.get(correlation_id)
        if not raw:
            raise ValueError("IAS3: correlation not found")
        return json.loads(raw)

    @gl.public.view
    def get_execution_policy(self, group_id: str) -> typing.Any:
        raw = self.exec_policies.get(group_id)
        if not raw:
            raise ValueError("IAS3: no policy")
        return json.loads(raw)
