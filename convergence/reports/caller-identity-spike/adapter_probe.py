# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
import json
import typing

from genlayer import *
import genlayer.gl as gl


class AdapterProbe(gl.Contract):
    core_address: str
    last_observed: TreeMap[str, str]

    @gl.public.write
    def initialize(self, core_address: str) -> str:
        self.core_address = core_address
        return core_address

    @gl.public.view
    def whoami(self) -> str:
        return gl.message.contract_address.as_hex.lower().removeprefix('0x')

    @gl.public.write
    def forward(self, label: str, declared_source: str, amount: str) -> str:
        me = gl.message.sender_address.as_hex.lower().removeprefix('0x')
        self.last_observed[label] = me
        core = gl.get_contract_at(Address(self.core_address))
        core.emit(on='accepted').execute(label, declared_source, amount)
        return 'queued'
