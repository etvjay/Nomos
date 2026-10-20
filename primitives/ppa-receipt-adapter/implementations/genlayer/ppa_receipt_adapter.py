# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }

import json
import typing
from genlayer import *
import genlayer.gl as gl

def _now_iso():
    dt = getattr(gl.message, 'datetime', None)
    if dt:
        return dt
    return gl.message_raw['datetime']

def _ts(iso):
    import datetime
    txt = iso.strip().replace('Z', '+00:00')
    return int(datetime.datetime.fromisoformat(txt).timestamp())

def _valid_addr(a):
    return isinstance(a, str) and a.startswith('0x') and (len(a) == 42)

def _valid_id(i):
    return isinstance(i, str) and 0 < len(i) <= 64


class PPAReceiptAdapter(gl.Contract):
    core: str
    meta: TreeMap[str, str]
    adjudicators: TreeMap[str, str]
    receipts: TreeMap[str, str]
    proposals: TreeMap[str, str]

    RECEIPT_FIELDS = ('decision_id', 'source_contract', 'authority_fingerprint', 'question_hash', 'evidence_hash', 'decision_status', 'equivalence_mode', 'policy_version', 'created_at', 'expires_at')
    TERMINAL = ('ACCEPTED', 'REJECTED', 'UNDETERMINED')
    EQ_MODES = ('comparative', 'non_comparative', 'custom', 'strict')
    ADJ_FIELDS = ('source_contract', 'authority_fingerprint', 'policy_version', 'created_at', 'expires_at')

    @gl.public.write
    def initialize(self, owner: str, core_address: str) -> typing.Any:
        if self.meta.get('owner'):
            raise ValueError('PPA Adapter: already initialized')
        self.meta['owner'] = self._norm(owner)
        self.core = core_address
        return {'status': 'INITIALIZED', 'core': core_address}

    def _norm(self, a):
        return (a or '').lower().removeprefix('0x')

    def _sender(self):
        return gl.message.sender_address.as_hex.lower().removeprefix('0x')

    def _assert_owner(self):
        if self._sender() != self._norm(self.meta.get('owner')):
            raise ValueError('PPA Adapter: caller is not owner')

    @gl.public.write
    def register_adjudicator(self, adjudicator_json: str) -> typing.Any:
        self._assert_owner()
        data = json.loads(adjudicator_json)
        if not isinstance(data, dict) or set(data.keys()) != set(self.ADJ_FIELDS):
            raise ValueError('PPA Adapter: adjudicator schema violation')
        for k in self.ADJ_FIELDS:
            if not isinstance(data[k], str) or not data[k].strip():
                raise ValueError('PPA Adapter: adjudicator field invalid')
        if not _valid_addr(data['source_contract']):
            raise ValueError('PPA Adapter: invalid adjudicator address')
        src = self._norm(data['source_contract'])
        if self.adjudicators.get(src):
            raise ValueError('PPA Adapter: adjudicator already registered')
        if _ts(data['expires_at']) <= _ts(data['created_at']):
            raise ValueError('PPA Adapter: expiry must follow creation')
        rec = dict(data)
        rec['source_contract'] = src
        rec['status'] = 'ACTIVE'
        self.adjudicators[src] = json.dumps(rec)
        return {'status': 'REGISTERED', 'source_contract': src}

    @gl.public.write
    def revoke_adjudicator(self, source_contract: str) -> typing.Any:
        self._assert_owner()
        src = self._norm(source_contract)
        raw = self.adjudicators.get(src)
        if not raw:
            return {'status': 'REJECTED', 'reason_code': 'REJECTED_SOURCE_NOT_REGISTERED'}
        rec = json.loads(raw)
        rec['status'] = 'REVOKED'
        self.adjudicators[src] = json.dumps(rec)
        return {'status': 'REVOKED', 'source_contract': src}

    @gl.public.view
    def get_adjudicator(self, source_contract: str) -> typing.Any:
        raw = self.adjudicators.get(self._norm(source_contract))
        if not raw:
            raise ValueError('PPA Adapter: adjudicator not registered')
        return json.loads(raw)

    def _origin_status(self, data):
        src = self._norm(self._sender())
        raw = self.adjudicators.get(src)
        if not raw:
            return 'UNREGISTERED', 'REJECTED_SOURCE_NOT_REGISTERED'
        adj = json.loads(raw)
        if adj.get('status') != 'ACTIVE':
            return 'REVOKED', 'REJECTED_SOURCE_NOT_REGISTERED'
        if _ts(_now_iso()) >= _ts(adj['expires_at']):
            return 'EXPIRED', 'REJECTED_EXPIRED'
        if self._norm(data['source_contract']) != src:
            return 'MISMATCH', 'REJECTED_SOURCE_NOT_REGISTERED'
        if self._norm(data['authority_fingerprint']) != self._norm(adj['authority_fingerprint']):
            return 'AUTHORITY_MISMATCH', 'REJECTED_SOURCE_FINGERPRINT_MISMATCH'
        return 'BOUND', ''

    @gl.public.write
    def submit_decision_receipt(self, receipt_json: str) -> typing.Any:
        data = json.loads(receipt_json)
        if not isinstance(data, dict) or set(data.keys()) != set(self.RECEIPT_FIELDS):
            raise ValueError('PPA Adapter: receipt schema violation')
        for k in self.RECEIPT_FIELDS:
            if not isinstance(data[k], str) or not data[k].strip():
                raise ValueError('PPA Adapter: receipt field invalid')
        if data['decision_status'] not in self.TERMINAL:
            raise ValueError('PPA Adapter: invalid decision_status')
        if data['equivalence_mode'] not in self.EQ_MODES:
            raise ValueError('PPA Adapter: invalid equivalence_mode')
        if _ts(data['expires_at']) <= _ts(data['created_at']):
            raise ValueError('PPA Adapter: expiry must follow creation')
        did = data['decision_id']
        if not _valid_id(did):
            raise ValueError('PPA Adapter: invalid decision_id')
        if self.receipts.get(did):
            return {'status': 'REJECTED', 'reason_code': 'REJECTED_PROPOSAL_REPLAY', 'decision_id': did}
        expired = _ts(_now_iso()) >= _ts(data['expires_at'])
        ostatus, oreason = self._origin_status(data)
        rec = dict(data)
        rec['recorded'] = _now_iso()
        rec['origin_status'] = ostatus
        actionable = (data['decision_status'] == 'ACCEPTED') and (not expired) and (not oreason)
        rec['actionability'] = 'ACTIONABLE' if actionable else 'NON_ACTIONABLE'
        if oreason:
            rec['fail_reason'] = oreason
        elif data['decision_status'] == 'UNDETERMINED':
            rec['fail_reason'] = 'REJECTED_UNDETERMINED'
        elif expired:
            rec['fail_reason'] = 'REJECTED_EXPIRED'
        elif not actionable:
            rec['fail_reason'] = 'REJECTED_PROPOSAL_REPLAY'
        self.receipts[did] = json.dumps(rec)
        return {'decision_id': did, 'decision_status': data['decision_status'],
                'actionability': rec['actionability'], 'origin_status': ostatus,
                'reason_code': rec.get('fail_reason', '')}

    @gl.public.view
    def get_receipt(self, decision_id: str) -> typing.Any:
        raw = self.receipts.get(decision_id)
        if not raw:
            raise ValueError('PPA Adapter: receipt not found')
        return json.loads(raw)

    @gl.public.write
    def admit_proposal(self, proposal_json: str) -> typing.Any:
        data = json.loads(proposal_json)
        for k in ('proposal_id', 'decision_id', 'account_id', 'payment_id', 'to', 'amount', 'policy_version'):
            if not isinstance(data.get(k), str) or not data[k].strip():
                raise ValueError('PPA Adapter: proposal field invalid')
        pid = data['proposal_id']
        if not _valid_id(pid) or self.proposals.get(pid):
            return {'status': 'REJECTED', 'reason_code': 'REJECTED_PROPOSAL_REPLAY', 'proposal_id': pid}
        raw = self.receipts.get(data['decision_id'])
        if not raw:
            return {'status': 'REJECTED', 'reason_code': 'REJECTED_SOURCE_NOT_REGISTERED', 'proposal_id': pid}
        r = json.loads(raw)
        if r.get('actionability') != 'ACTIONABLE':
            return {'status': 'REJECTED', 'reason_code': r.get('fail_reason', 'REJECTED_SOURCE_NOT_REGISTERED'), 'proposal_id': pid}
        if not data['amount'].isdigit() or int(data['amount']) <= 0:
            return {'status': 'REJECTED', 'reason_code': 'REJECTED_AMOUNT', 'proposal_id': pid}
        if not _valid_addr(data['to']):
            return {'status': 'REJECTED', 'reason_code': 'REJECTED_RECIPIENT', 'proposal_id': pid}
        if data['policy_version'] != r['policy_version']:
            return {'status': 'REJECTED', 'reason_code': 'REJECTED_POLICY', 'proposal_id': pid}
        prop = dict(data)
        prop['status'] = 'ADMITTED'
        prop['evidence_hash'] = r['evidence_hash']
        prop['expires_at'] = r['expires_at']
        prop['created'] = _now_iso()
        self.proposals[pid] = json.dumps(prop)
        return {'status': 'ADMITTED', 'proposal_id': pid, 'decision_id': data['decision_id']}

    @gl.public.view
    def get_proposal(self, proposal_id: str) -> typing.Any:
        raw = self.proposals.get(proposal_id)
        if not raw:
            raise ValueError('PPA Adapter: proposal not found')
        return json.loads(raw)

    @gl.public.write
    def dispatch_proposal(self, proposal_id: str) -> typing.Any:
        raw = self.proposals.get(proposal_id)
        if not raw:
            return {'status': 'REJECTED', 'reason_code': 'REJECTED_PROPOSAL_REPLAY', 'proposal_id': proposal_id}
        prop = json.loads(raw)
        if prop.get('status') == 'DISPATCHED':
            return {'status': 'REJECTED', 'reason_code': 'REJECTED_PROPOSAL_REPLAY', 'proposal_id': proposal_id}
        prop['status'] = 'DISPATCHED'
        prop['dispatched'] = _now_iso()
        self.proposals[proposal_id] = json.dumps(prop)
        core = gl.get_contract_at(Address(self.core))
        core.emit(on='accepted').execute_proposal(json.dumps({
            'proposal_id': prop['proposal_id'],
            'decision_id': prop['decision_id'],
            'payment_id': prop['payment_id'],
            'account_id': prop['account_id'],
            'to': prop['to'],
            'amount': prop['amount'],
            'policy_version': prop['policy_version'],
            'evidence_hash': prop['evidence_hash'],
            'expires_at': prop['expires_at'],
        }))
        return {'status': 'DISPATCHED', 'proposal_id': proposal_id,
                'note': 'Core executes asynchronously; outcome is recorded in Core consequences'}
