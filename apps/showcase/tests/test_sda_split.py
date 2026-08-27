"""Split proof: price vs sla each in own account (~8.7KB each vs 18KB limit)."""
import json
PRICE_CONTRACT="contracts/sda_price.py"
SLA_CONTRACT="contracts/sda_sla.py"
def _hex(a):
    if hasattr(a,"as_hex"): return a.as_hex
    if isinstance(a,(bytes,bytearray)): return "0x"+a.hex()
    return str(a)
def _mock(direct_vm, satisfied, conf="high", body="x"):
    direct_vm.clear_mocks()
    direct_vm.mock_web(r".*", {"status":200,"body":body})
    direct_vm.mock_llm(r".*", json.dumps({"satisfied":satisfied,"confidence":conf,"reason":"mocked"}))
def _own(a):
    h=_hex(a)
    return "0x"+h[-40:] if len(h)>42 else h
def test_price_split(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender=direct_alice; c=direct_deploy(PRICE_CONTRACT)
    o=_own(direct_alice); c.initialize(o)
    c.create_account("ops", json.dumps({"daily_limit":"500","per_tx_limit":"200","currency":"USD","allowlist":[o]}))
    c.deposit("ops","1000"); c.set_autonomous("ON","1000")
    c.set_price_monitor("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd","ETH price in USD is above 5000","150",o,"ops")
    _mock(direct_vm, True, "high", '{"ethereum":{"usd":5123}}')
    r=c.tick_price("p1"); assert r["success"] and r["status"]=="SETTLED", r
    assert c.get_account("ops")["balance"]=="850"
    _mock(direct_vm, False, "high", '{"ethereum":{"usd":4900}}')
    r2=c.tick_price("p2"); assert r2["status"]=="REJECTED"
    assert c.get_account("ops")["balance"]=="850"
def test_sla_split(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender=direct_alice; c=direct_deploy(SLA_CONTRACT)
    o=_own(direct_alice); c.initialize(o)
    c.create_account("ops", json.dumps({"daily_limit":"500","per_tx_limit":"200","currency":"USD","allowlist":[o]}))
    c.deposit("ops","1000"); c.set_autonomous("ON","1000")
    c.set_sla_monitor("https://status.example.com","SLA uptime at least 99.9% and clause 4.2 satisfied","150",o,"ops")
    _mock(direct_vm, True, "high", "Status: uptime 99.95% last 30d, clause 4.2 met")
    r=c.tick_sla("s1"); assert r["success"], r
    assert c.get_account("ops")["balance"]=="850"
    _mock(direct_vm, False, "high", "Status: uptime 98.1%, major outage")
    r2=c.tick_sla("s2"); assert r2["status"]=="REJECTED"
    assert r2["success"] is False
def test_sla_low_confidence_no_pay(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender=direct_alice; c=direct_deploy(SLA_CONTRACT)
    o=_own(direct_alice); c.initialize(o)
    c.create_account("ops", json.dumps({"daily_limit":"500","per_tx_limit":"200","currency":"USD","allowlist":[o]}))
    c.deposit("ops","1000"); c.set_autonomous("ON","1000")
    c.set_sla_monitor("https://status.example.com","clause 4.2","150",o,"ops")
    _mock(direct_vm, True, "low", "unclear page")
    r=c.tick_sla("s-low"); assert r["status"]=="REJECTED_LOW_CONFIDENCE"
    assert c.get_account("ops")["balance"]=="1000"
