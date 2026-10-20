# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }

import json
import typing
from genlayer import *

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

class ProgrammablePaymentAccount(gl.Contract):
    meta: TreeMap[str, str]
    accounts: TreeMap[str, str]
    payments: TreeMap[str, str]
    attestations: TreeMap[str, str]
    receipts: TreeMap[str, str]
    proposals: TreeMap[str, str]
    adjudicators: TreeMap[str, str]

    def __init__(self) -> None:
        pass
    RECEIPT_FIELDS = ('decision_id', 'source_contract', 'authority_fingerprint', 'question_hash', 'evidence_hash', 'decision_status', 'equivalence_mode', 'policy_version', 'created_at', 'expires_at')
    TERMINAL = ('ACCEPTED', 'REJECTED', 'UNDETERMINED')
    EQ_MODES = ('comparative', 'non_comparative', 'custom', 'strict')
    PROPOSAL_FIELDS = ('proposal_id', 'decision_id', 'account_id', 'payment_id', 'to', 'amount', 'policy_version')
    ADJ_FIELDS = ('source_contract', 'authority_fingerprint', 'policy_version', 'created_at', 'expires_at')

    @gl.public.write
    def initialize(self, owner: str) -> str:
        if self.meta.get('owner'):
            raise ValueError('PPA: already initialized')
        if not _valid_addr(owner):
            raise ValueError('PPA: invalid owner address')
        self.meta['owner'] = self._norm(owner)
        self.meta['created'] = _now_iso()
        return 'initialized'

    def _norm(self, a):
        return (a or '').lower().removeprefix('0x')

    def _sender(self):
        return gl.message.sender_address.as_hex.lower().removeprefix('0x')

    def _assert_owner(self):
        if self._sender() != self._norm(self.meta.get('owner')):
            raise ValueError('PPA: caller is not the account owner')

    def _resolve_actor(self, account_id=''):
        sender = self._sender()
        if sender == self._norm(self.meta.get('owner')):
            return 'owner'
        raise ValueError('PPA: caller has no authority on this account')

    def _delegate_limits(self):
        return None

    @gl.public.write
    def create_account(self, account_id: str, rules_json: str) -> str:
        self._assert_owner()
        if not _valid_id(account_id):
            raise ValueError('PPA: invalid account id')
        if self.accounts.get(account_id):
            raise ValueError('PPA: account id exists')
        rules = json.loads(rules_json)
        for req in ('daily_limit', 'per_tx_limit', 'currency'):
            if req not in rules:
                raise ValueError(f'PPA: rules missing {req}')
        rec = {'account_id': account_id, 'rules': rules, 'balance': '0', 'committed': '0', 'daily_spent': '0', 'daily_window_start': _now_iso(), 'status': 'ACTIVE', 'created': _now_iso()}
        self.accounts[account_id] = json.dumps(rec)
        return 'account_created'

    @gl.public.write
    def update_rules(self, account_id: str, rules_json: str) -> str:
        self._assert_owner()
        rec = self._get_account(account_id)
        rec['rules'] = json.loads(rules_json)
        self.accounts[account_id] = json.dumps(rec)
        return 'rules_updated'

    @gl.public.view
    def get_account(self, account_id: str) -> typing.Any:
        return self._get_account(account_id)

    def _get_account(self, account_id):
        raw = self.accounts.get(account_id)
        if not raw:
            raise ValueError('PPA: account not found')
        return json.loads(raw)

    @gl.public.write
    def deposit(self, account_id: str, amount: str) -> str:
        self._resolve_actor()
        rec = self._get_account(account_id)
        if rec['status'] != 'ACTIVE':
            raise ValueError('PPA: account not active')
        if not amount.isdigit() or int(amount) <= 0:
            raise ValueError('PPA: invalid amount')
        rec['balance'] = str(int(rec['balance']) + int(amount))
        self.accounts[account_id] = json.dumps(rec)
        return 'deposited'

    @gl.public.write
    def withdraw(self, account_id: str, amount: str) -> str:
        self._assert_owner()
        rec = self._get_account(account_id)
        available = int(rec['balance']) - int(rec['committed'])
        if int(amount) > available:
            raise ValueError('PPA: insufficient uncommitted balance')
        rec['balance'] = str(int(rec['balance']) - int(amount))
        self.accounts[account_id] = json.dumps(rec)
        return 'withdrawn'

    @gl.public.write
    def send(self, account_id: str, payment_id: str, to: str, amount: str, evidence_hash: str='', memo: str='') -> typing.Any:
        actor = self._resolve_actor()
        rec = self._get_account(account_id)
        if rec['status'] != 'ACTIVE':
            raise ValueError('PPA: account not active')
        prior = self.payments.get(payment_id)
        if prior and json.loads(prior)['status'] != 'DENIED':
            raise ValueError('PPA: payment id exists')
        if not _valid_addr(to):
            raise ValueError('PPA: invalid recipient')
        if not amount.isdigit() or int(amount) <= 0:
            raise ValueError('PPA: invalid amount')
        rules = rec['rules']
        allowlist = [a.lower().replace('0x', '') for a in rules.get('allowlist', [])]
        if allowlist and to.lower().replace('0x', '') not in allowlist:
            return self._deny(payment_id, account_id, 'POLICY_DENYLIST')
        per_tx = int(rules['per_tx_limit'])
        if int(amount) > per_tx:
            return self._deny(payment_id, account_id, 'POLICY_PER_TX_LIMIT')
        dl = self._delegate_limits()
        if dl is not None:
            d_per_tx, d_daily = dl
            if int(amount) > min(per_tx, d_per_tx):
                return self._deny(payment_id, account_id, 'DELEGATE_PER_TX_LIMIT')
        daily = int(rules['daily_limit'])
        spent, window_start = self._roll_daily_window(rec)
        effective_daily = daily if dl is None else min(daily, dl[1])
        if spent + int(amount) > effective_daily:
            self.accounts[account_id] = json.dumps(rec)
            reason = 'POLICY_DAILY_LIMIT' if dl is None else 'DELEGATE_DAILY_LIMIT'
            return self._deny(payment_id, account_id, reason)
        attest_reason = self._attestation_gate(rec, to)
        if attest_reason is not None:
            return self._deny(payment_id, account_id, attest_reason)
        available = int(rec['balance']) - int(rec['committed'])
        if int(amount) > available:
            return self._deny(payment_id, account_id, 'INSUFFICIENT_COMMITMENT')
        rec['daily_spent'] = str(spent + int(amount))
        rec['balance'] = str(int(rec['balance']) - int(amount))
        self.accounts[account_id] = json.dumps(rec)
        payment = {'payment_id': payment_id, 'account_id': account_id, 'to': to, 'amount': amount, 'evidence_hash': evidence_hash, 'memo': memo, 'actor': actor, 'status': 'SETTLED', 'created': _now_iso()}
        self.payments[payment_id] = json.dumps(payment)
        return {'success': True, 'status': 'SETTLED', 'payment_id': payment_id, 'amount': amount, 'to': to}

    @gl.public.view
    def get_payment(self, payment_id: str) -> typing.Any:
        raw = self.payments.get(payment_id)
        if not raw:
            raise ValueError('PPA: payment not found')
        return json.loads(raw)

    def _deny(self, payment_id, account_id, reason):
        self.payments[payment_id] = json.dumps({'payment_id': payment_id, 'account_id': account_id, 'status': 'DENIED', 'reason': reason, 'created': _now_iso()})
        return {'success': False, 'status': 'DENIED', 'reason': reason}

    def _roll_daily_window(self, rec):
        now = _ts(_now_iso())
        start = _ts(rec['daily_window_start'])
        if now - start >= 86400:
            rec['daily_spent'] = '0'
            rec['daily_window_start'] = _now_iso()
            return (0, now)
        return (int(rec['daily_spent']), start)
    ATTESTATION_FIELDS = ('subject', 'issuer', 'status', 'issued_at', 'expires_at', 'evidence_hash', 'policy_version')

    @gl.public.write
    def register_attestation(self, attestation_id: str, attestation_json: str) -> str:
        self._assert_owner()
        if not _valid_id(attestation_id) or self.attestations.get(attestation_id):
            raise ValueError('PPA: invalid or duplicate attestation id')
        data = json.loads(attestation_json)
        if not isinstance(data, dict) or set(data.keys()) != set(self.ATTESTATION_FIELDS):
            raise ValueError('PPA: attestation schema violation (fixed fields only, no PII)')
        if not _valid_addr(data['subject']) or not _valid_addr(data['issuer']):
            raise ValueError('PPA: attestation subject/issuer must be valid addresses')
        if data['status'] not in ('VALID', 'REVOKED'):
            raise ValueError('PPA: attestation status must be VALID or REVOKED')
        for f in ('issued_at', 'expires_at'):
            if not isinstance(data[f], str):
                raise ValueError(f'PPA: attestation {f} must be an ISO timestamp string')
        issued = _ts(data['issued_at'])
        expires = _ts(data['expires_at'])
        if issued > expires:
            raise ValueError('PPA: attestation expires_at precedes issued_at')
        if not isinstance(data['evidence_hash'], str) or not 0 < len(data['evidence_hash']) <= 128:
            raise ValueError('PPA: attestation evidence_hash required (1..128 chars)')
        if not isinstance(data['policy_version'], str) or not 0 < len(data['policy_version']) <= 64:
            raise ValueError('PPA: attestation policy_version required (1..64 chars)')
        rec = {'attestation_id': attestation_id, 'subject': self._norm(data['subject']), 'issuer': self._norm(data['issuer']), 'status': data['status'], 'issued_at': data['issued_at'], 'expires_at': data['expires_at'], 'evidence_hash': data['evidence_hash'], 'policy_version': data['policy_version'], 'created': _now_iso()}
        self.attestations[attestation_id] = json.dumps(rec)
        return 'attestation_registered'

    @gl.public.write
    def revoke_attestation(self, attestation_id: str) -> str:
        self._assert_owner()
        raw = self.attestations.get(attestation_id)
        if not raw:
            raise ValueError('PPA: attestation not found')
        rec = json.loads(raw)
        rec['status'] = 'REVOKED'
        rec['revoked'] = _now_iso()
        self.attestations[attestation_id] = json.dumps(rec)
        return 'attestation_revoked'

    @gl.public.view
    def get_attestation(self, attestation_id: str) -> typing.Any:
        raw = self.attestations.get(attestation_id)
        if not raw:
            raise ValueError('PPA: attestation not found')
        return json.loads(raw)

    def _attestation_gate(self, rec, to):
        rules = rec['rules']
        if not rules.get('require_attestation'):
            return None
        to_n = to.lower().replace('0x', '')
        required_policy = rules.get('attestation_policy_version', '')
        authorized = set()
        for i in rules.get('attestation_issuers', []):
            authorized.add(str(i).lower().replace('0x', ''))
        ids = sorted(self.attestations.keys())
        if not ids:
            return 'ATTESTATION_MISSING'
        bound = []
        for k in ids:
            a = json.loads(self.attestations[k])
            s = a.get('subject')
            if isinstance(s, str) and s.lower().replace('0x', '') == to_n:
                bound.append(a)
        if not bound:
            return 'ATTESTATION_SUBJECT_MISMATCH'
        now = _ts(_now_iso())
        reason = None
        for a in bound:
            status = a.get('status')
            if status == 'REVOKED':
                r = 'ATTESTATION_REVOKED'
            elif status != 'VALID':
                r = 'ATTESTATION_INVALID_STATUS'
            elif a.get('issuer') not in authorized:
                r = 'ATTESTATION_ISSUER_UNAUTHORIZED'
            elif not isinstance(a.get('issued_at'), str) or not isinstance(a.get('expires_at'), str):
                r = 'ATTESTATION_INVALID'
            else:
                try:
                    issued = _ts(a['issued_at'])
                    expires = _ts(a['expires_at'])
                except Exception:
                    issued = expires = None
                if issued is None or issued > now:
                    r = 'ATTESTATION_INVALID'
                elif expires <= now:
                    r = 'ATTESTATION_EXPIRED'
                elif not a.get('evidence_hash'):
                    r = 'ATTESTATION_INVALID'
                elif not a.get('policy_version') or a['policy_version'] != required_policy:
                    r = 'ATTESTATION_POLICY_MISMATCH'
                else:
                    return None
            if reason is None:
                reason = r
        return reason

    def _validate_receipt(self, data):
        if not isinstance(data, dict) or set(data.keys()) != set(self.RECEIPT_FIELDS):
            raise ValueError('PPA: receipt schema violation')
        for k in self.RECEIPT_FIELDS:
            v = data[k]
            if not isinstance(v, str) or not v.strip():
                raise ValueError('PPA: receipt field invalid')
        if data['decision_status'] not in self.TERMINAL:
            raise ValueError('PPA: invalid decision_status')
        if data['equivalence_mode'] not in self.EQ_MODES:
            raise ValueError('PPA: invalid equivalence_mode')
        created = _ts(data['created_at'])
        expires = _ts(data['expires_at'])
        if expires <= created:
            raise ValueError('PPA: receipt expires_at must follow created_at')
        now = _ts(_now_iso())
        expired = now >= expires
        actionable = data['decision_status'] == 'ACCEPTED' and (not expired)
        return {'expired': expired, 'actionable': actionable}

    def _origin_status(self, data):
        src = self._norm(self._sender())
        raw = self.adjudicators.get(src)
        if not raw:
            return 'UNREGISTERED', 'RECEIPT_SOURCE_UNREGISTERED'
        adj = json.loads(raw)
        if adj.get('status') != 'ACTIVE':
            return 'REVOKED', 'RECEIPT_SOURCE_REVOKED'
        if _ts(_now_iso()) >= _ts(adj['expires_at']):
            return 'EXPIRED', 'RECEIPT_SOURCE_EXPIRED'
        if self._norm(data['source_contract']) != src:
            return 'MISMATCH', 'RECEIPT_SOURCE_MISMATCH'
        if self._norm(data['authority_fingerprint']) != self._norm(adj['authority_fingerprint']):
            return 'AUTHORITY_MISMATCH', 'RECEIPT_AUTHORITY_MISMATCH'
        return 'BOUND', ''

    @gl.public.write
    def register_adjudicator(self, adjudicator_json: str) -> typing.Any:
        self._assert_owner()
        data = json.loads(adjudicator_json)
        if not isinstance(data, dict) or set(data.keys()) != set(self.ADJ_FIELDS):
            raise ValueError('PPA: adjudicator schema violation')
        for k in self.ADJ_FIELDS:
            if not isinstance(data[k], str) or not data[k].strip():
                raise ValueError('PPA: adjudicator field invalid')
        if not _valid_addr(data['source_contract']):
            raise ValueError('PPA: invalid adjudicator address')
        src = self._norm(data['source_contract'])
        if self.adjudicators.get(src):
            raise ValueError('PPA: adjudicator already registered')
        if _ts(data['expires_at']) <= _ts(data['created_at']):
            raise ValueError('PPA: adjudicator expiry must follow creation')
        rec = dict(data)
        rec['source_contract'] = src
        rec['status'] = 'ACTIVE'
        self.adjudicators[src] = json.dumps(rec)
        return {'success': True, 'source_contract': src, 'status': 'ACTIVE'}

    @gl.public.write
    def revoke_adjudicator(self, source_contract: str) -> typing.Any:
        self._assert_owner()
        src = self._norm(source_contract)
        raw = self.adjudicators.get(src)
        if not raw:
            raise ValueError('PPA: adjudicator not registered')
        rec = json.loads(raw)
        rec['status'] = 'REVOKED'
        self.adjudicators[src] = json.dumps(rec)
        return {'success': True, 'source_contract': src, 'status': 'REVOKED'}

    @gl.public.view
    def get_adjudicator(self, source_contract: str) -> typing.Any:
        raw = self.adjudicators.get(self._norm(source_contract))
        if not raw:
            raise ValueError('PPA: adjudicator not registered')
        return json.loads(raw)

    @gl.public.write
    def submit_decision_receipt(self, receipt_json: str) -> typing.Any:
        """Record a GenLayer adjudication receipt. REJECTED/UNDETERMINED/expired are stored but non-actionable."""
        data = json.loads(receipt_json)
        meta = self._validate_receipt(data)
        did = data['decision_id']
        if not _valid_id(did):
            raise ValueError('PPA: invalid decision_id')
        if self.receipts.get(did):
            raise ValueError('PPA: decision_id exists')
        rec = dict(data)
        rec['recorded'] = _now_iso()
        ostatus, oreason = self._origin_status(data)
        rec['origin_status'] = ostatus
        rec['actionability'] = 'ACTIONABLE' if (meta['actionable'] and not oreason) else 'NON_ACTIONABLE'
        if oreason:
            rec['fail_reason'] = oreason
        elif meta['expired']:
            rec['fail_reason'] = 'RECEIPT_EXPIRED'
        elif data['decision_status'] != 'ACCEPTED':
            rec['fail_reason'] = 'NOT_ACCEPTED'
        self.receipts[did] = json.dumps(rec)
        return {'success': True, 'decision_id': did, 'decision_status': data['decision_status'], 'actionability': rec['actionability'], 'origin_status': ostatus}

    @gl.public.view
    def get_receipt(self, decision_id: str) -> typing.Any:
        raw = self.receipts.get(decision_id)
        if not raw:
            raise ValueError('PPA: receipt not found')
        return json.loads(raw)

    @gl.public.write
    def admit_proposal(self, proposal_json: str) -> typing.Any:
        """Create an executable proposal only from a stored ACTIONABLE ACCEPTED receipt."""
        self._resolve_actor()
        data = json.loads(proposal_json)
        if not isinstance(data, dict) or set(data.keys()) != set(self.PROPOSAL_FIELDS):
            raise ValueError('PPA: proposal schema violation')
        for k in self.PROPOSAL_FIELDS:
            if not isinstance(data[k], str) or not data[k].strip():
                raise ValueError('PPA: proposal field invalid')
        pid = data['proposal_id']
        if not _valid_id(pid) or self.proposals.get(pid):
            raise ValueError('PPA: invalid or duplicate proposal_id')
        raw = self.receipts.get(data['decision_id'])
        if not raw:
            raise ValueError('PPA: receipt not found')
        receipt = json.loads(raw)
        if receipt.get('actionability') != 'ACTIONABLE' or receipt.get('decision_status') != 'ACCEPTED':
            return {'success': False, 'status': 'REJECTED_PROPOSAL', 'reason': 'RECEIPT_NOT_ACTIONABLE'}
        if _ts(_now_iso()) >= _ts(receipt['expires_at']):
            receipt['actionability'] = 'NON_ACTIONABLE'
            receipt['fail_reason'] = 'RECEIPT_EXPIRED'
            self.receipts[data['decision_id']] = json.dumps(receipt)
            return {'success': False, 'status': 'REJECTED_PROPOSAL', 'reason': 'RECEIPT_EXPIRED'}
        if data['policy_version'] != receipt['policy_version']:
            return {'success': False, 'status': 'REJECTED_PROPOSAL', 'reason': 'POLICY_MISMATCH'}
        if data['decision_id'] != receipt['decision_id']:
            return {'success': False, 'status': 'REJECTED_PROPOSAL', 'reason': 'DECISION_MISMATCH'}
        if not data['amount'].isdigit() or int(data['amount']) <= 0:
            raise ValueError('PPA: invalid amount')
        if not _valid_addr(data['to']):
            raise ValueError('PPA: invalid recipient')
        prop = dict(data)
        prop['status'] = 'ADMITTED'
        prop['evidence_hash'] = receipt['evidence_hash']
        prop['created'] = _now_iso()
        self.proposals[pid] = json.dumps(prop)
        return {'success': True, 'status': 'ADMITTED', 'proposal_id': pid, 'decision_id': data['decision_id']}

    @gl.public.view
    def get_proposal(self, proposal_id: str) -> typing.Any:
        raw = self.proposals.get(proposal_id)
        if not raw:
            raise ValueError('PPA: proposal not found')
        return json.loads(raw)

    @gl.public.write
    def execute_proposal(self, proposal_id: str) -> typing.Any:
        """Execute an ADMITTED proposal through existing send gates. Judgment never moves funds directly."""
        self._resolve_actor()
        raw = self.proposals.get(proposal_id)
        if not raw:
            raise ValueError('PPA: proposal not found')
        prop = json.loads(raw)
        if prop.get('status') != 'ADMITTED':
            return {'success': False, 'status': 'REJECTED_EXECUTION', 'reason': 'PROPOSAL_NOT_ADMITTED'}
        rraw = self.receipts.get(prop['decision_id'])
        if not rraw:
            return {'success': False, 'status': 'REJECTED_EXECUTION', 'reason': 'RECEIPT_MISSING'}
        receipt = json.loads(rraw)
        if receipt.get('decision_status') != 'ACCEPTED' or receipt.get('actionability') != 'ACTIONABLE':
            return {'success': False, 'status': 'REJECTED_EXECUTION', 'reason': 'RECEIPT_NOT_ACTIONABLE'}
        if _ts(_now_iso()) >= _ts(receipt['expires_at']):
            return {'success': False, 'status': 'REJECTED_EXECUTION', 'reason': 'RECEIPT_EXPIRED'}
        out = self.send(prop['account_id'], prop['payment_id'], prop['to'], prop['amount'], receipt.get('evidence_hash', ''), 'proposal:' + proposal_id)
        if isinstance(out, dict) and out.get('status') == 'SETTLED':
            prop['status'] = 'EXECUTED'
            prop['executed'] = _now_iso()
            pay = json.loads(self.payments[prop['payment_id']])
            pay['decision_id'] = prop['decision_id']
            pay['proposal_id'] = proposal_id
            self.payments[prop['payment_id']] = json.dumps(pay)
        else:
            prop['status'] = 'EXECUTION_DENIED'
            prop['deny'] = out
            prop['executed'] = _now_iso()
        self.proposals[proposal_id] = json.dumps(prop)
        return {'proposal_id': proposal_id, 'proposal_status': prop['status'], 'payment': out}
