# {
#   "Seq": [{ "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }]
# }
"""SDA — Price variant. One treasury + one price monitor + tick(). ~7KB"""
import json, typing
from genlayer import *
def _now_iso() -> str:
    dt=getattr(gl.message,"datetime",None)
    return dt if dt else gl.message_raw["datetime"]
def _ts(s:str)->int:
    import datetime; return int(datetime.datetime.fromisoformat(s.strip().replace("Z","+00:00")).timestamp())
def _norm(a:str)->str: return (a or "").lower().removeprefix("0x")
def _valid(a:str)->bool: return isinstance(a,str) and a.startswith("0x") and len(a)==42
class PriceAccount(gl.Contract):
    owner: TreeMap[str,str]
    accounts: TreeMap[str,str]
    monitor: TreeMap[str,str]
    ticks: TreeMap[str,str]
    payments: TreeMap[str,str]
    kill: TreeMap[str,str]
    policy: TreeMap[str,str]
    def __init__(self): pass
    @gl.public.write
    def initialize(self, owner:str)->str:
        if self.owner.get("owner"): raise ValueError("inited")
        if not _valid(owner): raise ValueError("bad owner")
        self.owner["owner"]=_norm(owner); self.owner["created"]=_now_iso()
        self.kill["autonomous"]="OFF"; self.policy["global"]=json.dumps({"max_daily":"1000","enabled":"false"})
        return "initialized"
    @gl.public.write
    def set_autonomous(self, enabled:str, max_daily:str="1000")->str:
        me=gl.message.sender_address.as_hex.lower().removeprefix("0x")
        if me!=self.owner.get("owner"): raise ValueError("not owner")
        if enabled not in ("ON","OFF"): raise ValueError("bad")
        self.kill["autonomous"]=enabled; self.policy["global"]=json.dumps({"max_daily":max_daily,"enabled":enabled})
        return f"autonomous_{enabled}"
    @gl.public.write
    def create_account(self, account_id:str, rules_json:str)->str:
        me=gl.message.sender_address.as_hex.lower().removeprefix("0x")
        if me!=self.owner.get("owner"): raise ValueError("not owner")
        if self.accounts.get(account_id): raise ValueError("exists")
        r=json.loads(rules_json)
        for k in ("daily_limit","per_tx_limit","currency"):
            if k not in r: raise ValueError(k)
        self.accounts[account_id]=json.dumps({"account_id":account_id,"rules":r,"balance":"0","daily_spent":"0","daily_window_start":_now_iso(),"status":"ACTIVE","created":_now_iso()})
        return "account_created"
    @gl.public.write
    def deposit(self, account_id:str, amount:str)->str:
        me=gl.message.sender_address.as_hex.lower().removeprefix("0x")
        if me!=self.owner.get("owner"): raise ValueError("not owner")
        raw=self.accounts.get(account_id)
        if not raw: raise ValueError("no acct")
        if not amount.isdigit() or int(amount)<=0: raise ValueError("amt")
        rec=json.loads(raw); rec["balance"]=str(int(rec["balance"])+int(amount)); self.accounts[account_id]=json.dumps(rec); return "deposited"
    @gl.public.view
    def get_account(self, account_id:str)->typing.Any:
        raw=self.accounts.get(account_id)
        if not raw: raise ValueError("no acct")
        return json.loads(raw)
    @gl.public.write
    def set_price_monitor(self, url:str, clause:str, per_action:str="150", recipient:str="", source_account:str="ops")->str:
        me=gl.message.sender_address.as_hex.lower().removeprefix("0x")
        if me!=self.owner.get("owner"): raise ValueError("not owner")
        if not _valid(recipient): raise ValueError("bad recipient")
        self.monitor["cfg"]=json.dumps({"url":url,"clause":clause,"per_action":per_action,"recipient":recipient,"source_account":source_account,"created":_now_iso()})
        return "monitor_set"
    @gl.public.write
    def tick_price(self, tick_id:str)->typing.Any:
        if self.kill.get("autonomous")!="ON": return {"success":False,"status":"AUTONOMOUS_OFF"}
        ep=json.loads(self.policy.get("global") or '{"max_daily":"1000","enabled":"ON"}')
        if ep.get("enabled")!="ON": return {"success":False,"status":"POLICY_DISABLED"}
        raw=self.monitor.get("cfg")
        if not raw: raise ValueError("no monitor")
        mon=json.loads(raw)
        if self.ticks.get(tick_id): raise ValueError("tick_id exists")
        url=mon["url"]; clause=mon["clause"]
        def leader_fn()->typing.Any:
            web_data=gl.nondet.web.render(url, mode="text")
            prompt = "Evidence from outside world (URL " + url + "):\n" + web_data[:5000] + "\n\nClause to judge: " + clause + "\n\nDecide if evidence satisfies clause. Respond ONLY as JSON: {\"satisfied\": true/false, \"confidence\": \"high|medium|low\", \"reason\": \"<1 sentence>\"}. If missing/unclear, satisfied=false confidence=low."
            return gl.nondet.exec_prompt(prompt, response_format="json")
        def validator_fn(leaders_res)->bool:
            my=leader_fn()
            try: ld=leaders_res.calldata
            except: return False
            if not isinstance(my,dict) or not isinstance(ld,dict): return False
            if my.get("satisfied")!=ld.get("satisfied"): return False
            good={"medium","high"}
            if ld.get("satisfied") is True and (ld.get("confidence") not in good or my.get("confidence") not in good): return False
            return True
        res=gl.vm.run_nondet(leader_fn, validator_fn)
        tick_rec={"tick_id":tick_id,"url":url,"clause":clause,"adjudication":res if isinstance(res,dict) else {"error":"consensus_unreachable","raw":str(res)},"at":_now_iso()}
        if not isinstance(res,dict):
            tick_rec["status"]="UNDETERMINED"; self.ticks[tick_id]=json.dumps(tick_rec); return {"success":False,"status":"UNDETERMINED","tick_id":tick_id}
        satisfied=res.get("satisfied") is True; conf=str(res.get("confidence","low"))
        if not satisfied: tick_rec["status"]="REJECTED"; self.ticks[tick_id]=json.dumps(tick_rec); return {"success":False,"status":"REJECTED","confidence":conf,"tick_id":tick_id}
        if conf not in ("medium","high"): tick_rec["status"]="REJECTED_LOW_CONFIDENCE"; self.ticks[tick_id]=json.dumps(tick_rec); return {"success":False,"status":"REJECTED_LOW_CONFIDENCE","tick_id":tick_id}
        source=mon["source_account"]; to=mon["recipient"]; amount=mon["per_action"]
        raw_acc=self.accounts.get(source)
        if not raw_acc: tick_rec["status"]="DENIED_NO_ACCOUNT"; self.ticks[tick_id]=json.dumps(tick_rec); return {"success":False,"status":"DENIED_NO_ACCOUNT","tick_id":tick_id}
        rec=json.loads(raw_acc)
        day=_now_iso()[:10]; spent_today=int(self.ticks.get(f"__spent_{day}") or "0"); max_daily=int(ep.get("max_daily","1000"))
        if spent_today+int(amount)>max_daily: tick_rec["status"]="DENIED_DAILY_AUTONOMOUS_CAP"; self.ticks[tick_id]=json.dumps(tick_rec); return {"success":False,"status":"DENIED_DAILY_AUTONOMOUS_CAP","tick_id":tick_id}
        rules=rec["rules"]; allow=[a.lower().replace("0x","") for a in rules.get("allowlist",[])]
        if allow and to.lower().replace("0x","") not in allow: tick_rec["status"]="DENIED_ALLOWLIST"; self.ticks[tick_id]=json.dumps(tick_rec); return {"success":False,"status":"DENIED_ALLOWLIST","tick_id":tick_id}
        if int(amount)>int(rules["per_tx_limit"]): tick_rec["status"]="DENIED_PER_TX"; self.ticks[tick_id]=json.dumps(tick_rec); return {"success":False,"status":"DENIED_PER_TX","tick_id":tick_id}
        now=_ts(_now_iso()); start=_ts(rec["daily_window_start"])
        if now-start>=86400: rec["daily_spent"]="0"; rec["daily_window_start"]=_now_iso()
        spent=int(rec["daily_spent"]); daily=int(rules["daily_limit"])
        if spent+int(amount)>daily: self.accounts[source]=json.dumps(rec); tick_rec["status"]="DENIED_DAILY"; self.ticks[tick_id]=json.dumps(tick_rec); return {"success":False,"status":"DENIED_DAILY","tick_id":tick_id}
        if int(amount)>int(rec["balance"]): tick_rec["status"]="DENIED_INSUFFICIENT"; self.ticks[tick_id]=json.dumps(tick_rec); return {"success":False,"status":"DENIED_INSUFFICIENT","tick_id":tick_id}
        rec["daily_spent"]=str(spent+int(amount)); rec["balance"]=str(int(rec["balance"])-int(amount)); self.accounts[source]=json.dumps(rec)
        pid=f"pay-{tick_id}"; self.payments[pid]=json.dumps({"payment_id":pid,"tick_id":tick_id,"to":to,"amount":amount,"at":_now_iso()}); self.ticks[f"__spent_{day}"]=str(spent_today+int(amount))
        tick_rec["status"]="SETTLED"; tick_rec["payment_id"]=pid; self.ticks[tick_id]=json.dumps(tick_rec)
        return {"success":True,"status":"SETTLED","payment_id":pid,"amount":amount,"to":to,"tick_id":tick_id}
    @gl.public.view
    def get_tick(self, tick_id:str)->typing.Any:
        raw=self.ticks.get(tick_id)
        if not raw: raise ValueError("no tick")
        return json.loads(raw)
