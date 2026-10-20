# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
import json

from genlayer import *


class CoreProbe(gl.Contract):
    observations: TreeMap[str, str]

    @gl.public.write
    def record_const(self, label: str) -> str:
        self.observations[label] = 'const-ok'
        return 'const-ok'

    @gl.public.write
    def record_sender(self, label: str) -> str:
        observed = gl.message.sender_address.as_hex.lower().removeprefix('0x')
        self.observations[label] = observed
        return observed

    @gl.public.write
    def execute(self, label: str, declared_source: str, amount: str) -> str:
        observed = gl.message.sender_address.as_hex.lower().removeprefix('0x')
        rec = {'label': label, 'observed_sender': observed,
               'declared_source': declared_source, 'amount': amount}
        self.observations[label] = json.dumps(rec)
        return json.dumps(rec)

    @gl.public.view
    def get_observation(self, label: str) -> str:
        raw = self.observations.get(label)
        if not raw:
            raise ValueError('CoreProbe: no observation')
        return raw
