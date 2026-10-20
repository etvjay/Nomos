# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
import json

from genlayer import *


class CoreEnforce(gl.Contract):
    adapters: TreeMap[str, str]
    log: TreeMap[str, str]
    cap: TreeMap[str, str]

    @gl.public.write
    def register_adapter(self, addr: str) -> str:
        self.adapters[addr.lower().removeprefix('0x')] = 'ACTIVE'
        return 'ACTIVE'

    @gl.public.write
    def set_cap(self, account: str, max_amount: str) -> str:
        self.cap[account] = max_amount
        return max_amount

    @gl.public.write
    def execute_proposal(self, label: str, account: str, amount: str) -> str:
        caller = gl.message.sender_address.as_hex.lower().removeprefix('0x')
        v = {'caller': caller, 'account': account, 'amount': amount}
        if self.adapters.get(caller) != 'ACTIVE':
            v['verdict'] = 'REJECTED_CALLER_NOT_REGISTERED_ADAPTER'
            self.log[label] = json.dumps(v)
            return v['verdict']
        cap = self.cap.get(account)
        if cap is not None and int(amount) > int(cap):
            v['verdict'] = 'REJECTED_WIDENS_BEYOND_CAP'
            self.log[label] = json.dumps(v)
            return v['verdict']
        v['verdict'] = 'EXECUTED'
        self.log[label] = json.dumps(v)
        return v['verdict']

    @gl.public.view
    def get_log(self, label: str) -> str:
        raw = self.log.get(label)
        if not raw:
            raise ValueError('CoreEnforce: no log')
        return raw
