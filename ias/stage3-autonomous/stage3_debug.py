# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
"""IAS Stage 3 DEBUG build - minimal check_monitor for Studio diagnosis.

Isolates the nondet flow: web render -> exec_prompt -> comparative validator.
Each step records a status string so the failure point is visible in
Studio's execution output. Paste into studio.genlayer.com, deploy, run
initialize, then check_monitor with the same args used on Bradbury:
  ["BTC-TRIG", "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"]
"""

import json
import typing

from genlayer import *


def _norm(a: str) -> str:
    return (a or "").lower().removeprefix("0x")


class Stage3Debug(gl.Contract):
    owner: TreeMap[str, str]
    results: TreeMap[str, str]

    def __init__(self) -> None:
        pass

    @gl.public.write
    def initialize(self, owner: str) -> str:
        self.owner["owner"] = _norm(owner)
        return "initialized"

    @gl.public.write
    def check_monitor(self, monitor_id: str, data_source: str) -> typing.Any:
        steps = []

        def leader_fn() -> typing.Any:
            # STEP 1: web render
            try:
                web_data = gl.nondet.web.render(data_source, mode="text")
                web_len = len(web_data) if web_data else 0
            except Exception as e:
                return {"step": "web_render_failed", "error": str(e)[:200]}

            if not web_data or web_len < 10:
                return {"step": "web_empty", "len": web_len}

            prompt = (
                f'Extract price from this page. WEBPAGE:\n{web_data[:3000]}\n'
                'Respond ONLY as JSON: {"value":"<number>","found":true} '
                'or {"found":false,"value":"0"}'
            )

            # STEP 2: LLM extraction
            try:
                res = gl.nondet.exec_prompt(prompt, response_format="json")
            except Exception as e:
                return {"step": "exec_prompt_failed", "error": str(e)[:200]}

            if res is None:
                return {"step": "llm_returned_none", "web_len": web_len}
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
            if bool(ld.get("found")) != bool(my.get("found")):
                return False
            try:
                ln = float(ld.get("value", "0"))
                vn = float(my.get("value", "0"))
                return abs(ln - vn) <= abs(ln * 0.15)
            except (TypeError, ValueError):
                return str(ld.get("value")) == str(my.get("value"))

        result = gl.vm.run_nondet(leader_fn, validator_fn)

        out = {
            "consensus": "reached" if isinstance(result, dict) else "FAILED",
            "result": result if isinstance(result, dict) else None,
        }
        self.results[monitor_id + ":" + gl.message_raw["datetime"]] = json.dumps(out)
        return out

    @gl.public.view
    def get_result(self, key: str) -> typing.Any:
        raw = self.results.get(key)
        if not raw:
            raise ValueError("no result")
        return json.loads(raw)

    @gl.public.view
    def get_owner(self) -> typing.Any:
        return {"owner": self.owner.get("owner")}
