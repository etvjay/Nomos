# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
"""Self-Driving Nomos Account — single contract that reads the outside world, adjudicates, and pays through own gates.

This is the showcase contract for the Research Foundry finding:
- Spend gates are commodity (7710/4337/Safe do them)
- The delta is adjudication inside the same account tx: natural-language condition over external evidence → validator quorum (Equivalence) → only then policy → encumbrance → claim → settle

Design: PPA semantics + Stage1 nondet pattern merged into one gl.Contract.
- Treasury: sub-accounts with allowlist/perTx/daily (same as PPA)
- Adjudication: gl.nondet.web.render(url) + gl.nondet.exec_prompt(clause) under comparative tolerance consensus (same as IAS Stage1 leader_fn/validator_fn)
- Liveness: permissionless tick() — anyone can call; judgment and money stay gated
- Safety: kill_switch OFF by default, max_daily_autonomous_spend, DENIED stored, UNDETERMINED → no pay

No external oracle/TEE trust beyond GenLayer quorum. Keeper only provides liveness.
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


def _valid_addr(a: str) -> bool:
    return isinstance(a, str) and a.startswith("0x") and len(a) == 42


class SelfDrivingAccount(gl.Contract):
    owner: TreeMap[str, str]
    accounts: TreeMap[str, str]      # account_id -> {balance, rules, daily_spent, window_start, status}
    monitors: TreeMap[str, str]      # monitor_id -> {url, clause, tolerance, per_action, recipient, source_account}
    ticks: TreeMap[str, str]         # tick_id -> adjudication record
    payments: TreeMap[str, str]      # payment_id -> settled record
    kill_switch: TreeMap[str, str]   # autonomous -> ON/OFF
    exec_policy: TreeMap[str, str]   # global -> {max_daily, enabled}

    def __init__(self) -> None:
        pass

    @gl.public.write
    def initialize(self, owner: str) -> str:
        if self.owner.get("owner"):
            raise ValueError("SDA: already initialized")
        if not _valid_addr(owner):
            raise ValueError("SDA: invalid owner")
        self.owner["owner"] = _norm(owner)
        self.owner["created"] = _now_iso()
        self.kill_switch["autonomous"] = "OFF"
        self.exec_policy["global"] = json.dumps({"max_daily": "1000", "enabled": "false"})
        return "initialized"

    @gl.public.write
    def set_autonomous(self, enabled: str, max_daily: str = "1000") -> str:
        me = gl.message.sender_address.as_hex.lower().removeprefix("0x")
        if me != self.owner.get("owner"):
            raise ValueError("SDA: not owner")
        if enabled not in ("ON", "OFF"):
            raise ValueError("SDA: enabled must be ON/OFF")
        self.kill_switch["autonomous"] = enabled
        self.exec_policy["global"] = json.dumps({"max_daily": max_daily, "enabled": enabled})
        return f"autonomous_{enabled}"

    # ---------- treasury (PPA subset) ----------

    @gl.public.write
    def create_account(self, account_id: str, rules_json: str) -> str:
        me = gl.message.sender_address.as_hex.lower().removeprefix("0x")
        if me != self.owner.get("owner"):
            raise ValueError("SDA: not owner")
        if self.accounts.get(account_id):
            raise ValueError("SDA: account exists")
        rules = json.loads(rules_json)
        for k in ("daily_limit", "per_tx_limit", "currency"):
            if k not in rules:
                raise ValueError(f"SDA: rules missing {k}")
        rec = {
            "account_id": account_id,
            "rules": rules,
            "balance": "0",
            "daily_spent": "0",
            "daily_window_start": _now_iso(),
            "status": "ACTIVE",
            "created": _now_iso(),
        }
        self.accounts[account_id] = json.dumps(rec)
        return "account_created"

    @gl.public.write
    def deposit(self, account_id: str, amount: str) -> str:
        me = gl.message.sender_address.as_hex.lower().removeprefix("0x")
        if me != self.owner.get("owner"):
            raise ValueError("SDA: not owner")
        raw = self.accounts.get(account_id)
        if not raw:
            raise ValueError("SDA: account not found")
        if not amount.isdigit() or int(amount) <= 0:
            raise ValueError("SDA: invalid amount")
        rec = json.loads(raw)
        rec["balance"] = str(int(rec["balance"]) + int(amount))
        self.accounts[account_id] = json.dumps(rec)
        return "deposited"

    @gl.public.view
    def get_account(self, account_id: str) -> typing.Any:
        raw = self.accounts.get(account_id)
        if not raw:
            raise ValueError("SDA: account not found")
        return json.loads(raw)

    # ---------- monitor: what outside world to read ----------

    @gl.public.write
    def set_monitor(self, monitor_id: str, url: str, clause: str, tolerance: str = "5.0", per_action: str = "150", recipient: str = "", source_account: str = "ops") -> str:
        me = gl.message.sender_address.as_hex.lower().removeprefix("0x")
        if me != self.owner.get("owner"):
            raise ValueError("SDA: not owner")
        if not _valid_addr(recipient):
            raise ValueError("SDA: invalid recipient")
        cfg = {
            "monitor_id": monitor_id,
            "url": url,
            "clause": clause,
            "tolerance": tolerance,
            "per_action": per_action,
            "recipient": recipient,
            "source_account": source_account,
            "created": _now_iso(),
        }
        self.monitors[monitor_id] = json.dumps(cfg)
        return "monitor_set"

    @gl.public.view
    def get_monitor(self, monitor_id: str) -> typing.Any:
        raw = self.monitors.get(monitor_id)
        if not raw:
            raise ValueError("SDA: monitor not found")
        return json.loads(raw)

    # ---------- self-driving tick: read world + adjudicate + gated pay ----------

    @gl.public.write
    def tick(self, monitor_id: str, tick_id: str) -> typing.Any:
        """Permissionless keeper calls this. Inside, validators fetch outside world and judge.
        Only then do deterministic gates decide to pay.
        """
        if self.kill_switch.get("autonomous") != "ON":
            return {"success": False, "status": "AUTONOMOUS_OFF"}
        ep_raw = self.exec_policy.get("global")
        ep = json.loads(ep_raw) if ep_raw else {"max_daily": "1000", "enabled": "ON"}
        if ep.get("enabled") != "ON":
            return {"success": False, "status": "POLICY_DISABLED"}
        mon_raw = self.monitors.get(monitor_id)
        if not mon_raw:
            raise ValueError("SDA: monitor not found")
        mon = json.loads(mon_raw)
        if self.ticks.get(tick_id):
            raise ValueError("SDA: tick_id exists")

        # ---- nondeterministic adjudication (same pattern as IAS Stage1) ----
        url = mon["url"]
        clause = mon["clause"]
        try:
            tolerance = float(mon.get("tolerance", "5.0"))
        except:
            tolerance = 5.0

        def leader_fn() -> typing.Any:
            web_data = gl.nondet.web.render(url, mode="text")
            task = (
                f"Evidence from outside world (URL {url}):\n{web_data[:5000]}\n\n"
                f"Clause to judge: {clause}\n\n"
                "Decide if the evidence satisfies the clause. "
                'Respond ONLY as JSON: {"satisfied": true/false, "confidence": "high|medium|low", "reason": "<1 sentence>"}. '
                "If evidence is missing or unclear, satisfied=false confidence=low."
            )
            res = gl.nondet.exec_prompt(task, response_format="json")
            return res

        def validator_fn(leaders_res) -> bool:
            # comparative: validator re-judges independently, same satisfied must match
            my = leader_fn()
            try:
                ld = leaders_res.calldata
            except Exception:
                return False
            if not isinstance(my, dict) or not isinstance(ld, dict):
                return False
            # both must agree on satisfied boolean; confidence must be >= medium to accept
            good = {"medium", "high"}
            if my.get("satisfied") != ld.get("satisfied"):
                return False
            if ld.get("confidence") not in good or my.get("confidence") not in good:
                # if either validator says low confidence, treat as not agreeing to satisfy
                # for satisfied=true we require medium+, for satisfied=false low is okay to agree on failure
                if ld.get("satisfied") is True:
                    return False
            return True

        res = gl.vm.run_nondet(leader_fn, validator_fn)
        tick_rec = {
            "tick_id": tick_id,
            "monitor_id": monitor_id,
            "url": url,
            "clause": clause,
            "adjudication": res if isinstance(res, dict) else {"error": "consensus_unreachable", "raw": str(res)},
            "at": _now_iso(),
        }

        if not isinstance(res, dict):
            tick_rec["status"] = "UNDETERMINED"
            self.ticks[tick_id] = json.dumps(tick_rec)
            return {"success": False, "status": "UNDETERMINED", "reason": "consensus_unreachable", "tick_id": tick_id}

        satisfied = res.get("satisfied") is True
        confidence = str(res.get("confidence", "low"))
        if not satisfied:
            tick_rec["status"] = "REJECTED"
            self.ticks[tick_id] = json.dumps(tick_rec)
            return {"success": False, "status": "REJECTED", "confidence": confidence, "tick_id": tick_id}

        if confidence not in ("medium", "high"):
            tick_rec["status"] = "REJECTED_LOW_CONFIDENCE"
            self.ticks[tick_id] = json.dumps(tick_rec)
            return {"success": False, "status": "REJECTED_LOW_CONFIDENCE", "tick_id": tick_id}

        # ---- deterministic gates (PPA pipeline in same tx) ----
        source = mon["source_account"]
        to = mon["recipient"]
        amount = mon["per_action"]
        raw_acc = self.accounts.get(source)
        if not raw_acc:
            tick_rec["status"] = "DENIED_NO_ACCOUNT"
            self.ticks[tick_id] = json.dumps(tick_rec)
            return {"success": False, "status": "DENIED_NO_ACCOUNT", "tick_id": tick_id}
        rec = json.loads(raw_acc)

        # daily autonomous cap (global)
        day_key = _now_iso()[:10]
        spent_today = int(self.ticks.get(f"__spent_{day_key}") or "0")
        max_daily = int(ep.get("max_daily", "1000"))
        if spent_today + int(amount) > max_daily:
            tick_rec["status"] = "DENIED_DAILY_AUTONOMOUS_CAP"
            self.ticks[tick_id] = json.dumps(tick_rec)
            return {"success": False, "status": "DENIED_DAILY_AUTONOMOUS_CAP", "tick_id": tick_id}

        # PPA gates: allowlist / perTx / daily / encumbrance
        rules = rec["rules"]
        allow = [a.lower().replace("0x", "") for a in rules.get("allowlist", [])]
        if allow and to.lower().replace("0x", "") not in allow:
            tick_rec["status"] = "DENIED_ALLOWLIST"
            self.ticks[tick_id] = json.dumps(tick_rec)
            return {"success": False, "status": "DENIED_ALLOWLIST", "tick_id": tick_id}
        per_tx = int(rules["per_tx_limit"])
        if int(amount) > per_tx:
            tick_rec["status"] = "DENIED_PER_TX"
            self.ticks[tick_id] = json.dumps(tick_rec)
            return {"success": False, "status": "DENIED_PER_TX", "tick_id": tick_id}
        # daily window
        now_s = _ts(_now_iso())
        start_s = _ts(rec["daily_window_start"])
        if now_s - start_s >= 86400:
            rec["daily_spent"] = "0"
            rec["daily_window_start"] = _now_iso()
        spent = int(rec["daily_spent"])
        daily = int(rules["daily_limit"])
        if spent + int(amount) > daily:
            self.accounts[source] = json.dumps(rec)
            tick_rec["status"] = "DENIED_DAILY"
            self.ticks[tick_id] = json.dumps(tick_rec)
            return {"success": False, "status": "DENIED_DAILY", "tick_id": tick_id}
        available = int(rec["balance"]) - 0  # no separate committed in SDA; simple
        if int(amount) > available:
            tick_rec["status"] = "DENIED_INSUFFICIENT"
            self.ticks[tick_id] = json.dumps(tick_rec)
            return {"success": False, "status": "DENIED_INSUFFICIENT", "tick_id": tick_id}

        # settle
        rec["daily_spent"] = str(spent + int(amount))
        rec["balance"] = str(int(rec["balance"]) - int(amount))
        self.accounts[source] = json.dumps(rec)
        payment_id = f"pay-{tick_id}"
        self.payments[payment_id] = json.dumps({
            "payment_id": payment_id, "tick_id": tick_id, "to": to, "amount": amount, "at": _now_iso()
        })
        self.ticks[f"__spent_{day_key}"] = str(spent_today + int(amount))
        tick_rec["status"] = "SETTLED"
        tick_rec["payment_id"] = payment_id
        self.ticks[tick_id] = json.dumps(tick_rec)
        return {"success": True, "status": "SETTLED", "payment_id": payment_id, "amount": amount, "to": to, "tick_id": tick_id}

    @gl.public.view
    def get_tick(self, tick_id: str) -> typing.Any:
        raw = self.ticks.get(tick_id)
        if not raw:
            raise ValueError("SDA: tick not found")
        return json.loads(raw)
