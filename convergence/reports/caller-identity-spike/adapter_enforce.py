# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
from genlayer import *
import genlayer.gl as gl


class AdapterEnforce(gl.Contract):
    core: str
    adjudicator_seen: TreeMap[str, str]

    @gl.public.write
    def initialize(self, core: str) -> str:
        self.core = core
        return core

    @gl.public.write
    def submit_and_forward(self, label: str, account: str, amount: str) -> str:
        caller = gl.message.sender_address.as_hex.lower().removeprefix('0x')
        self.adjudicator_seen[label] = caller
        core = gl.get_contract_at(Address(self.core))
        core.emit(on='accepted').execute_proposal(label, account, amount)
        return 'queued'

    @gl.public.view
    def seen(self, label: str) -> str:
        raw = self.adjudicator_seen.get(label)
        if not raw:
            raise ValueError('AdapterEnforce: nothing seen')
        return raw
