# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }

import json
import typing
from genlayer import *
_E0 = 'REJECTED_CALLER_NOT_REGISTERED_ADAPTER'

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

class PPACore(gl.Contract):
    meta: TreeMap[str, str]
    accounts: TreeMap[str, str]
    payments: TreeMap[str, str]
    attestations: TreeMap[str, str]
    adapters: TreeMap[str, str]
    consequences: TreeMap[str, str]

    def __init__(self) -> None:
        pass

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
        return self._settle(account_id, payment_id, to, amount, evidence_hash, memo, actor)

    def _settle(self, account_id, payment_id: str, to: str, amount: str, evidence_hash: str, memo: str, actor: str):
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
    @gl.public.write
    def register_adapter(self, adapter_address: str) -> typing.Any:
        self._assert_owner()
        a = self._norm(adapter_address)
        if not a or len(a) != 40:
            return {'status': 'REJECTED_RECIPIENT', 'reason_code': 'INVALID_ADAPTER_ADDRESS'}
        rec = {'adapter_caller': a, 'status': 'ACTIVE',
               'created_at': _now_iso(), 'expires_at': '2099-01-01T00:00:00+00:00'}
        self.adapters[a] = json.dumps(rec)
        return {'status': 'REGISTERED', 'adapter_caller': a}

    @gl.public.write
    def revoke_adapter(self, adapter_address: str) -> typing.Any:
        self._assert_owner()
        a = self._norm(adapter_address)
        raw = self.adapters.get(a)
        if not raw:
            return {'status': 'REJECTED', 'reason_code': _E0}
        rec = json.loads(raw)
        rec['status'] = 'REVOKED'
        self.adapters[a] = json.dumps(rec)
        return {'status': 'REVOKED', 'adapter_caller': a}

    @gl.public.view
    def get_adapter(self, adapter_address: str) -> typing.Any:
        raw = self.adapters.get(self._norm(adapter_address))
        if not raw:
            raise ValueError('PPA Core: adapter not registered')
        return json.loads(raw)

    @gl.public.write
    def register_adapter_window(self, adapter_address: str, expires_at: str) -> typing.Any:
        self._assert_owner()
        a = self._norm(adapter_address)
        raw = self.adapters.get(a)
        if not raw:
            return {'status': 'REJECTED', 'reason_code': _E0}
        rec = json.loads(raw)
        if _ts(expires_at) <= _ts(_now_iso()):
            return {'status': 'REJECTED', 'reason_code': 'REJECTED_EXPIRED'}
        rec['expires_at'] = expires_at
        self.adapters[a] = json.dumps(rec)
        return {'status': 'RENEWED', 'adapter_caller': a, 'expires_at': expires_at}

    def _record(self, pid, rec):
        if pid in self.consequences:
            return 'ALREADY_TERMINAL'
        self.consequences[pid] = json.dumps(rec)
        return 'RECORDED'

    def _consequence(self, pid, did: str, pay: str, caller: str, reason: str,
                     amount: str, to: str, pv: str, status: str, extra: dict) -> typing.Any:
        rec = {'proposal_id': pid, 'decision_id': did, 'payment_id': pay,
               'adapter_caller': caller, 'reason_code': reason,
               'requested_amount': amount, 'requested_recipient': to,
               'policy_version': pv, 'created_at': _now_iso(), 'status': status}
        rec.update(extra)
        self._record(pid, rec)
        return rec

    @gl.public.write
    def execute_proposal(self, proposal_json: str) -> typing.Any:
        caller = self._norm(self._sender())
        p = json.loads(proposal_json)
        pid = p.get('proposal_id', '')
        did = p.get('decision_id', '')
        pay = p.get('payment_id', '')
        acct = p.get('account_id', '')
        to = p.get('to', '')
        amt = p.get('amount', '')
        pv = p.get('policy_version', '')
        exp = p.get('expires_at', '')
        raw = self.adapters.get(caller)
        if not raw:
            r = self._consequence(pid, did, pay, caller, _E0, amt, to, pv, 'REJECTED', {})
            return r
        arec = json.loads(raw)
        if arec.get('status') != 'ACTIVE':
            return self._consequence(pid, did, pay, caller, 'REJECTED_ADAPTER_REVOKED', amt, to, pv, 'REJECTED', {})
        if _ts(_now_iso()) >= _ts(arec['expires_at']):
            return self._consequence(pid, did, pay, caller, 'REJECTED_EXPIRED', amt, to, pv, 'REJECTED', {})
        if not _valid_id(pid) or not _valid_id(did) or not _valid_id(pay):
            return self._consequence(pid, did, pay, caller, 'REJECTED_PROPOSAL_REPLAY', amt, to, pv, 'REJECTED', {})
        if self.consequences.get(pid):
            return json.loads(self.consequences[pid])
        if not exp or _ts(_now_iso()) >= _ts(exp):
            return self._consequence(pid, did, pay, caller, 'REJECTED_EXPIRED', amt, to, pv, 'REJECTED', {'expires_at': exp})
        if not _valid_addr(to):
            return self._consequence(pid, did, pay, caller, 'REJECTED_RECIPIENT', amt, to, pv, 'REJECTED', {})
        if not amt.isdigit() or int(amt) <= 0:
            return self._consequence(pid, did, pay, caller, 'REJECTED_AMOUNT', amt, to, pv, 'REJECTED', {})
        acc = self.accounts.get(acct)
        if not acc:
            return self._consequence(pid, did, pay, caller, 'REJECTED_POLICY', amt, to, pv, 'REJECTED', {'detail': 'NO_ACCOUNT'})
        rec = json.loads(acc)
        if rec['status'] != 'ACTIVE':
            return self._consequence(pid, did, pay, caller, 'REJECTED_POLICY', amt, to, pv, 'REJECTED', {'detail': 'ACCOUNT_NOT_ACTIVE'})
        if rec['rules'].get('policy_version', pv) != pv:
            return self._consequence(pid, did, pay, caller, 'REJECTED_POLICY', amt, to, pv, 'REJECTED', {'detail': 'POLICY_VERSION_DRIFT'})
        allow = [a.lower().replace('0x', '') for a in rec['rules'].get('allowlist', [])]
        if allow and to.lower().replace('0x', '') not in allow:
            return self._consequence(pid, did, pay, caller, 'REJECTED_RECIPIENT', amt, to, pv, 'REJECTED', {'detail': 'NOT_ALLOWLISTED'})
        if int(amt) > int(rec['rules']['per_tx_limit']):
            return self._consequence(pid, did, pay, caller, 'REJECTED_AMOUNT', amt, to, pv, 'REJECTED', {'detail': 'PER_TX_LIMIT'})
        prior = self.payments.get(pay)
        if prior and json.loads(prior)['status'] != 'DENIED':
            return self._consequence(pid, did, pay, caller, 'REJECTED_REPLAY', amt, to, pv, 'REJECTED', {'detail': 'PAYMENT_ID_EXISTS'})
        reason = self._attestation_gate(rec, to)
        if reason:
            return self._consequence(pid, did, pay, caller, 'REJECTED_ATTESTATION', amt, to, pv, 'REJECTED', {'detail': reason})
        if int(amt) > int(rec['balance']) - int(rec['committed']):
            return self._consequence(pid, did, pay, caller, 'REJECTED_CAPITAL', amt, to, pv, 'REJECTED', {'detail': 'INSUFFICIENT_UNCOMMITTED'})
        out = self._settle(acct, pay, to, amt, p.get('evidence_hash', ''), 'proposal:' + pid, 'adapter:' + caller)
        if isinstance(out, dict) and out.get('status') == 'SETTLED':
            pr = json.loads(self.payments[pay])
            pr['decision_id'] = did
            pr['proposal_id'] = pid
            self.payments[pay] = json.dumps(pr)
            return self._consequence(pid, did, pay, caller, 'EXECUTED', amt, to, pv, 'EXECUTED', {'payment_status': 'SETTLED'})
        return self._consequence(pid, did, pay, caller, out.get('reason', 'REJECTED_POLICY'), amt, to, pv, 'DENIED', {'payment_status': out.get('status', 'DENIED')})

    @gl.public.view
    def get_consequence(self, proposal_id: str) -> typing.Any:
        raw = self.consequences.get(proposal_id)
        if not raw:
            raise ValueError('PPA Core: no consequence recorded')
        return json.loads(raw)
