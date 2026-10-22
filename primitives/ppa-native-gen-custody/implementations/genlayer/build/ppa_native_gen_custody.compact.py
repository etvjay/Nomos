# {
#   "Seq": [
#     { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
#   ]
# }
_A4='transfer_seq'
_A3='vault_after'
_A2='vault_before'
_A1='settled_at'
_A0='REJECTED_ALREADY_EMITTED'
_z='REJECTED_INVALID_RECIPIENT'
_y='REJECTED_INVALID_AMOUNT'
_x='balance_after'
_w='next_refund'
_v='next_deposit'
_u='detail'
_t='+00:00'
_s='execution'
_r='REJECTED_VAULT_PAUSED'
_q='created'
_p='SETTLEABLE'
_o='REJECTED_INTENT_EXPIRED'
_n='EXPIRED'
_m='PENDING_FINALITY'
_l='core_created_at'
_k='REJECTED_INVALID_TTL'
_j='seq'
_i=True
_h='NONE'
_g='last_reason_code'
_f='proposal_id'
_e='self'
_d=False
_c='intent'
_b='REJECTED_CORE_BINDING'
_a='last_attempt_at'
_Z='AUTHORIZED'
_Y='payment_id'
_X='expires_at'
_W='core'
_V='0x'
_U='core_snapshot_hash'
_T='consequence_id'
_S='adapter'
_R='max_ttl'
_Q='policy_version'
_P='decision_id'
_O='adapter_caller'
_N='total_refunded'
_M='total_emitted'
_L='total_deposited'
_K='REJECTED'
_J='owner'
_I='paused'
_H='attempts'
_G='currency'
_F=None
_E='recipient'
_D='reason_code'
_C='amount'
_B='0'
_A='status'
import datetime,hashlib,json,typing
from genlayer import*
import genlayer.gl as gl
NATIVE_CURRENCY='GEN'
MAX_TTL=604800
ZERO_ADDRESS=_B*40
def _now_iso():
	A='datetime';dt=getattr(gl.message,A,_F)
	if dt:return dt
	return gl.message_raw[A]
def _ts(iso):txt=iso.strip().replace('Z',_t);return int(datetime.datetime.fromisoformat(txt).timestamp())
def _iso(epoch):return datetime.datetime.fromtimestamp(int(epoch),datetime.timezone.utc).isoformat().replace(_t,'Z')
def _sha(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()
def _norm_addr(value):
	if not isinstance(value,str):return''
	return value.lower().removeprefix(_V)
def _valid_addr(value):
	if not isinstance(value,str):return _d
	text=value.lower()
	if not text.startswith(_V)or len(text)!=42:return _d
	try:int(text[2:],16)
	except ValueError:return _d
	return _i
def _valid_id(value):return isinstance(value,str)and 0<len(value)<=128
def _positive_uint(value):
	if not isinstance(value,str)or not value.isdigit():return
	n=int(value)
	if n<=0:return
	return n
def _as_dict(value):
	if isinstance(value,dict):return value
	if isinstance(value,str):
		try:parsed=json.loads(value)
		except Exception:return
		return parsed if isinstance(parsed,dict)else _F
class PPANativeGenCustody(gl.Contract):
	meta:TreeMap[str,str];intents:TreeMap[str,str];deposits:TreeMap[str,str];refunds:TreeMap[str,str]
	def __init__(self)->_F:0
	def _sender(self):return gl.message.sender_address.as_hex.lower().removeprefix(_V)
	def _own_address(self):
		ca=gl.message.contract_address
		if isinstance(ca,(bytes,bytearray)):return bytes(ca).hex()
		h=ca.as_hex if hasattr(ca,'as_hex')else str(ca);return h.lower().removeprefix(_V)
	def _assert_initialized(self):
		if not self.meta.get(_J):raise ValueError('Custody: not initialized')
	def _assert_owner(self):
		self._assert_initialized()
		if self._sender()!=self.meta.get(_J):raise ValueError('Custody: caller is not owner')
	def _paused(self):return self.meta.get(_I)=='1'
	def _max_ttl(self):
		try:return int(self.meta.get(_R,str(MAX_TTL)))
		except Exception:return MAX_TTL
	def _total(self,key):
		try:return int(self.meta.get(key,_B))
		except Exception:return 0
	def _set_total(self,key,value):self.meta[key]=str(int(value))
	def _next_seq(self,key):
		try:seq=int(self.meta.get(key,'1'))
		except Exception:seq=1
		self.meta[key]=str(seq+1);return seq
	def _refusal(self,base,reason,detail=''):
		record=dict(base);record[_A]='UNDETERMINED'if reason.startswith('UNDETERMINED_')else _K;record[_D]=reason
		if detail:record[_u]=detail
		return record
	def _get_intent(self,consequence_id):
		raw=self.intents.get(consequence_id)
		if not raw:return
		return _as_dict(raw)
	@gl.public.write
	def initialize(self,owner:str,core_address:str,adapter_address:str,max_ttl_seconds:str)->typing.Any:
		if self.meta.get(_J):raise ValueError('Custody: already initialized')
		for value in(owner,core_address,adapter_address):
			if not _valid_addr(value):raise ValueError('Custody: invalid address')
		ttl=_positive_uint(max_ttl_seconds)
		if ttl is _F or ttl>MAX_TTL:raise ValueError('Custody: invalid max_ttl_seconds')
		self.meta[_J]=_norm_addr(owner);self.meta[_W]=_norm_addr(core_address);self.meta[_S]=_norm_addr(adapter_address);self.meta[_G]=NATIVE_CURRENCY;self.meta[_R]=str(ttl);self.meta[_I]=_B;self.meta[_q]=_now_iso();self.meta[_e]=self._own_address();self.meta[_v]='1';self.meta[_w]='1';self.meta[_L]=_B;self.meta[_M]=_B;self.meta[_N]=_B;return{_A:'INITIALIZED',_J:self.meta[_J],_W:self.meta[_W],_S:self.meta[_S],_G:NATIVE_CURRENCY,_R:str(ttl),_e:self.meta[_e]}
	@gl.public.write.payable
	def deposit(self)->typing.Any:
		self._assert_initialized();value=int(gl.message.value)
		if value<=0:raise ValueError('Custody: deposit value required')
		seq=self._next_seq(_v);record={_j:str(seq),'sender':self._sender(),_C:str(value),_x:str(int(self.balance)),'at':_now_iso()};self.deposits[str(seq)]=json.dumps(record);self._set_total(_L,self._total(_L)+value);return record
	def _evaluate(self,consequence_id,ttl_seconds):
		N='invalid-created_at';M='memo';L='actor';K='requested_amount';J='requested_recipient';I='REJECTED_PAYMENT_NOT_SETTLED';H='SETTLED';G='payment_status';F='EXECUTED';E='created_at';D='account_id';C='REJECTED_CORE_UNAVAILABLE';B='UNDETERMINED_DEPENDENCY';A='REJECTED_PAYMENT_BINDING';now_iso=_now_iso()
		try:now=_ts(now_iso)
		except Exception:now=0
		base={_T:consequence_id,_f:consequence_id,_G:NATIVE_CURRENCY,_E:'',_C:_B,'evaluated_at':now_iso,_X:_iso(now+ttl_seconds)}
		if not _valid_id(consequence_id):return self._refusal(base,'REJECTED_INVALID_CONSEQUENCE_ID')
		if ttl_seconds<=0 or ttl_seconds>self._max_ttl():return self._refusal(base,_k)
		core_hex=self.meta.get(_W,'')
		if not core_hex:return self._refusal(base,B,'core-not-configured')
		try:core=gl.get_contract_at(Address(_V+core_hex))
		except Exception as exc:return self._refusal(base,C,str(exc)[:200])
		try:consequence=_as_dict(core.view().get_consequence(consequence_id))
		except Exception as exc:
			message=str(exc).lower()
			if'no consequence'in message or'not found'in message:return self._refusal(base,'REJECTED_NO_CONSEQUENCE',str(exc)[:200])
			return self._refusal(base,C,str(exc)[:200])
		if consequence is _F:return self._refusal(base,B,'consequence-not-object')
		if consequence.get(_f)!=consequence_id:return self._refusal(base,A,'consequence-proposal-mismatch')
		if consequence.get(_A)!=F or consequence.get(_D)!=F:return self._refusal(base,'REJECTED_CONSEQUENCE_NOT_EXECUTED',str(consequence.get(_A,'')))
		if consequence.get(G)!=H:return self._refusal(base,I,str(consequence.get(G,'')))
		if _norm_addr(consequence.get(_O,''))!=self.meta.get(_S,''):return self._refusal(base,'REJECTED_WRONG_ADAPTER',_norm_addr(consequence.get(_O,'')))
		payment_id=consequence.get(_Y,'')
		if not _valid_id(payment_id):return self._refusal(base,A,'invalid-payment-id')
		try:payment=_as_dict(core.view().get_payment(payment_id));account_id=(payment or{}).get(D,'');account=_as_dict(core.view().get_account(account_id))if account_id else _F
		except Exception as exc:return self._refusal(base,C,str(exc)[:200])
		if payment is _F or account is _F:return self._refusal(base,B,'payment-or-account-not-object')
		if payment.get(_Y)!=payment_id:return self._refusal(base,A,'payment-id-mismatch')
		if payment.get(_f)!=consequence_id:return self._refusal(base,A,'payment-proposal-mismatch')
		if payment.get(_P)!=consequence.get(_P):return self._refusal(base,A,'payment-decision-mismatch')
		if payment.get(_A)!=H:return self._refusal(base,I,str(payment.get(_A,'')))
		if _norm_addr(payment.get('to',''))!=_norm_addr(consequence.get(J,'')):return self._refusal(base,A,'recipient-mismatch')
		if str(payment.get(_C,''))!=str(consequence.get(K,'')):return self._refusal(base,A,'amount-mismatch')
		if payment.get(L)!='adapter:'+self.meta.get(_S,''):return self._refusal(base,A,'actor-mismatch')
		if payment.get(M)!='proposal:'+consequence_id:return self._refusal(base,A,'memo-mismatch')
		if payment.get(D)!=account.get(D):return self._refusal(base,A,'account-mismatch')
		if account.get(_A)!='ACTIVE':return self._refusal(base,'REJECTED_ACCOUNT_NOT_ACTIVE',str(account.get(_A,'')))
		rules=account.get('rules',{})
		if not isinstance(rules,dict):return self._refusal(base,A,'rules-not-object')
		currency=rules.get(_G)
		if currency!=NATIVE_CURRENCY:return self._refusal(base,'REJECTED_CURRENCY_MISMATCH',str(currency))
		policy_version=consequence.get(_Q,'')
		if rules.get(_Q)and rules.get(_Q)!=policy_version:return self._refusal(base,'REJECTED_POLICY_VERSION',str(rules.get(_Q)))
		amount_text=str(consequence.get(K,''))
		if not amount_text.isdigit()or int(amount_text)<=0:return self._refusal(base,_y,amount_text)
		recipient=consequence.get(J,'')
		if not _valid_addr(recipient)or _norm_addr(recipient)==ZERO_ADDRESS:return self._refusal(base,_z,str(recipient))
		try:created_at=_ts(consequence.get(E,''))
		except Exception:return self._refusal(base,A,N)
		if created_at<=0:return self._refusal(base,A,N)
		snapshot={_f:consequence_id,_Y:payment_id,_P:consequence.get(_P,''),_O:_norm_addr(consequence.get(_O,'')),_G:currency,_E:_norm_addr(recipient),_C:amount_text,_Q:policy_version,_l:consequence.get(E,''),'payment_actor':payment.get(L,''),'payment_memo':payment.get(M,'')};base.update({_E:_norm_addr(recipient),_C:amount_text,_Y:payment_id,_P:consequence.get(_P,''),_O:_norm_addr(consequence.get(_O,'')),_Q:policy_version,_l:consequence.get(E,''),_U:'sha256:'+_sha(json.dumps(snapshot,sort_keys=_i))});base[_A]=_Z;base[_D]='';return base
	@gl.public.view
	def preview_authorization(self,consequence_id:str,ttl_seconds:str)->typing.Any:
		ttl=_positive_uint(ttl_seconds)
		if ttl is _F:return self._refusal({_T:consequence_id,_G:NATIVE_CURRENCY,_E:'',_C:_B},_k)
		if self._paused():return self._refusal({_T:consequence_id,_G:NATIVE_CURRENCY,_E:'',_C:_B},_r)
		return self._evaluate(consequence_id,ttl)
	@gl.public.write
	def authorize(self,consequence_id:str,ttl_seconds:str)->typing.Any:
		self._assert_owner();ttl=_positive_uint(ttl_seconds)
		if ttl is _F or ttl>self._max_ttl():return{_A:_K,_D:_k}
		if self._paused():return{_A:_K,_D:_r}
		prior=self._get_intent(consequence_id)
		if prior:
			status=prior.get(_A)
			if status==_Z:return{_A:_K,_D:'REJECTED_REPLAY'}
			if status==_m:return{_A:_K,_D:_A0}
			if status==_n:return{_A:_K,_D:_o}
		plan=self._evaluate(consequence_id,ttl)
		if plan.get(_A)!=_Z:record=dict(plan);record[_H]=1;record[_a]=_now_iso();self.intents[consequence_id]=json.dumps(record);return record
		now_iso=_now_iso();record={_T:consequence_id,_f:consequence_id,_Y:plan.get(_Y,''),_P:plan.get(_P,''),_O:plan.get(_O,''),_E:plan.get(_E,''),_C:plan.get(_C,_B),_G:NATIVE_CURRENCY,_Q:plan.get(_Q,''),_l:plan.get(_l,''),_U:plan.get(_U,''),_A:_Z,_s:_h,'authorized_at':now_iso,_X:plan.get(_X,''),_H:0,_g:'',_a:'','settler':'',_A1:'',_A2:'',_A3:'',_A4:''};self.intents[consequence_id]=json.dumps(record);return record
	def _settlement_checks(self,consequence_id,recipient,amount,mutate):
		A='REJECTED_INTENT_NOT_FOUND';base={_T:consequence_id,_A:_h,_D:''}
		if self._paused():return self._refusal(base,_r)
		intent=self._get_intent(consequence_id)
		if not intent:return self._refusal(base,A)
		if intent.get(_A)==_m:return self._refusal(base,_A0)
		if intent.get(_A)==_n:return self._refusal(base,_o)
		if intent.get(_A)!=_Z:return self._refusal(base,A,str(intent.get(_A,'')))
		if not _valid_addr(recipient):return self._refusal(base,_z,str(recipient))
		if _norm_addr(recipient)!=intent.get(_E):return self._refusal(base,'REJECTED_RECIPIENT_MISMATCH',_norm_addr(recipient))
		amount_text=str(amount)
		if not amount_text.isdigit()or int(amount_text)<=0:return self._refusal(base,_y,amount_text)
		if amount_text!=intent.get(_C):return self._refusal(base,'REJECTED_AMOUNT_MISMATCH',amount_text)
		try:now=_ts(_now_iso());expires_at=_ts(intent.get(_X,''))
		except Exception:return self._refusal(base,_o,'invalid-expiry')
		if now>=expires_at:
			if mutate:intent[_A]=_n;intent[_s]=_n;self.intents[consequence_id]=json.dumps(intent)
			return self._refusal(base,_o)
		plan=self._evaluate(consequence_id,self._max_ttl())
		if plan.get(_A)!=_Z:
			if mutate:intent[_H]=int(intent.get(_H,0))+1;intent[_g]=_b;intent[_a]=_now_iso();self.intents[consequence_id]=json.dumps(intent)
			return self._refusal(base,_b,plan.get(_D,''))
		if plan.get(_E)!=intent.get(_E)or plan.get(_C)!=intent.get(_C):
			if mutate:intent[_H]=int(intent.get(_H,0))+1;intent[_g]=_b;intent[_a]=_now_iso();self.intents[consequence_id]=json.dumps(intent)
			return self._refusal(base,_b,'core-intent-mismatch')
		if int(self.balance)<int(intent.get(_C,_B)):return self._refusal(base,'REJECTED_INSUFFICIENT_CUSTODY')
		return{_A:_p,_D:'',_c:intent,'plan':plan}
	@gl.public.view
	def preview_settlement(self,consequence_id:str,recipient:str,amount:str)->typing.Any:
		result=self._settlement_checks(consequence_id,recipient,amount,_d)
		if result.get(_A)==_p:return{_A:_p,_D:'',_T:consequence_id,_E:result[_c].get(_E,''),_C:result[_c].get(_C,_B),_X:result[_c].get(_X,''),_U:result[_c].get(_U,''),'vault_balance':str(int(self.balance))}
		return result
	@gl.public.write
	def settle(self,consequence_id:str,recipient:str,amount:str)->typing.Any:
		self._assert_initialized();result=self._settlement_checks(consequence_id,recipient,amount,_i)
		if result.get(_A)!=_p:return result
		intent=result[_c];plan=result['plan']
		if plan.get(_U)!=intent.get(_U):intent[_H]=int(intent.get(_H,0))+1;intent[_g]=_b;intent[_a]=_now_iso();self.intents[consequence_id]=json.dumps(intent);return{_A:_K,_D:_b,_u:'snapshot-drift'}
		before=int(self.balance);seq=self._next_seq('next_settlement');intent[_A]=_m;intent[_s]=_m;intent[_H]=int(intent.get(_H,0))+1;intent[_g]='';intent[_a]=_now_iso();intent['settler']=self._sender();intent[_A1]=_now_iso();intent[_A2]=str(before);intent[_A4]=str(seq);self.intents[consequence_id]=json.dumps(intent);self._set_total(_M,self._total(_M)+int(intent[_C]));gl.chain.Account(Address(_V+intent[_E])).emit_transfer(value=u256(int(intent[_C])),on='finalized');intent[_A3]=str(int(self.balance));self.intents[consequence_id]=json.dumps(intent);return intent
	@gl.public.write.payable
	def __on_errored_message__(self)->typing.Any:
		self._assert_initialized();value=int(gl.message.value);seq=self._next_seq(_w);record={_j:str(seq),_C:str(value),_x:str(int(self.balance)),'at':_now_iso()};self.refunds[str(seq)]=json.dumps(record)
		if value>0:self._set_total(_N,self._total(_N)+value)
		return record
	@gl.public.write
	def set_paused(self,paused:bool)->typing.Any:self._assert_owner();self.meta[_I]='1'if paused else _B;return{_A:'PAUSED'if paused else'UNPAUSED',_I:bool(paused)}
	@gl.public.write
	def pause(self)->typing.Any:self._assert_owner();self.meta[_I]='1';return{_A:'PAUSED',_I:_i}
	@gl.public.write
	def unpause(self)->typing.Any:self._assert_owner();self.meta[_I]=_B;return{_A:'UNPAUSED',_I:_d}
	@gl.public.write
	def set_max_ttl(self,ttl_seconds:str)->typing.Any:
		self._assert_owner();ttl=_positive_uint(ttl_seconds)
		if ttl is _F or ttl>MAX_TTL:return{_A:_K,_D:_k}
		self.meta[_R]=str(ttl);return{_A:'TTL_UPDATED',_R:str(ttl)}
	@gl.public.view
	def get_intent(self,consequence_id:str)->typing.Any:
		intent=self._get_intent(consequence_id)
		if intent is _F:return{_T:consequence_id,_A:_h}
		return intent
	@gl.public.view
	def get_config(self)->typing.Any:return{_J:self.meta.get(_J,''),_W:self.meta.get(_W,''),_S:self.meta.get(_S,''),_G:self.meta.get(_G,NATIVE_CURRENCY),_R:self.meta.get(_R,_B),_I:self._paused(),_e:self.meta.get(_e,''),_q:self.meta.get(_q,''),_L:self.meta.get(_L,_B),_M:self.meta.get(_M,_B),_N:self.meta.get(_N,_B)}
	@gl.public.view
	def get_balance(self)->typing.Any:balance=int(self.balance);expected=self._total(_L)-self._total(_M)+self._total(_N);return{'balance':str(balance),_L:str(self._total(_L)),_M:str(self._total(_M)),_N:str(self._total(_N)),'expected_balance':str(expected),'reconciled':balance==expected}
	@gl.public.view
	def get_deposit(self,seq:str)->typing.Any:
		raw=self.deposits.get(str(seq))
		if not raw:return{_j:str(seq),_A:_h}
		return json.loads(raw)
	@gl.public.view
	def get_refund(self,seq:str)->typing.Any:
		raw=self.refunds.get(str(seq))
		if not raw:return{_j:str(seq),_A:_h}
		return json.loads(raw)
