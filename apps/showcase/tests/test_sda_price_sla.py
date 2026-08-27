"""GLSim proof for Self-Driving Account: price + SLA in same contract, tick() reads outside world.

Covers the classic trap: who wakes vs how it knows.
"""
import json, pathlib
CONTRACT = "contracts/self_driving_account.py"

def _mock_satisfied(direct_vm, satisfied: bool, confidence="high", web_body="ethereum: {usd: 5123}"):
    direct_vm.clear_mocks()
    direct_vm.mock_web(r".*", {"status": 200, "body": web_body})
    direct_vm.mock_llm(r".*", json.dumps({"satisfied": satisfied, "confidence": confidence, "reason": "mocked"}))

def _hex(a):
    if hasattr(a, "as_hex"):
        return a.as_hex
    if isinstance(a, (bytes, bytearray)):
        return "0x" + a.hex()
    return str(a)

def _setup(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    c = direct_deploy(CONTRACT)
    owner = _hex(direct_alice)
    # ensure 0x + 40 hex; if too long (32 bytes -> 64 hex), slice to last 20 bytes
    if len(owner) > 42:
        owner = "0x" + owner[-40:]
    c.initialize(owner)
    c.create_account("ops", json.dumps({"daily_limit":"500","per_tx_limit":"200","currency":"USD","allowlist":[owner]}))
    c.deposit("ops", "1000")
    c.set_autonomous("ON", "1000")
    return c

def test_price_above_pays_and_below_rejects(direct_vm, direct_deploy, direct_alice):
    c = _setup(direct_vm, direct_deploy, direct_alice)
    vendor = _hex(direct_alice)
    if len(vendor) > 42: vendor = "0x"+vendor[-40:]
    # price monitor
    c.set_monitor("eth-price", "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd", "ETH price in USD is above 5000", "5.0", "150", vendor, "ops")
    # sla monitor in same contract
    c.set_monitor("sla-42", "https://status.example.com", "SLA uptime at least 99.9 percent and clause 4.2 satisfied", "5.0", "150", vendor, "ops")

    # tick price when mocked price 5123 -> satisfied true -> should SETTLE
    _mock_satisfied(direct_vm, True, "high", '{"ethereum":{"usd":5123}}')
    r1 = c.tick("eth-price", "tick-price-1")
    assert r1["success"] is True and r1["status"] == "SETTLED", r1
    assert c.get_account("ops")["balance"] == "850"  # 1000-150
    assert c.get_account("ops")["daily_spent"] == "150"

    # same tick_id cannot replay
    direct_vm.mock_web(r".*", {"status": 200, "body": '{"x":1}'})
    direct_vm.mock_llm(r".*", json.dumps({"satisfied": True, "confidence":"high","reason":"x"}))
    try:
        c.tick("eth-price", "tick-price-1")
        assert False, "replay should revert"
    except Exception as e:
        assert "tick_id exists" in str(e)

    # price 4900 -> satisfied false -> REJECTED, no pay, balance unchanged
    _mock_satisfied(direct_vm, False, "high", '{"ethereum":{"usd":4900}}')
    r2 = c.tick("eth-price", "tick-price-2")
    assert r2["success"] is False and r2["status"] == "REJECTED", r2
    assert c.get_account("ops")["balance"] == "850"

    # sla satisfied -> second pay in same day
    _mock_satisfied(direct_vm, True, "high", "Status page: uptime 99.95% last 30d, all systems operational. Clause 4.2 met.")
    r3 = c.tick("sla-42", "tick-sla-1")
    assert r3["success"] is True, r3
    assert c.get_account("ops")["balance"] == "700"

def test_autonomous_off_blocks_tick(direct_vm, direct_deploy, direct_alice):
    c = _setup(direct_vm, direct_deploy, direct_alice)
    c.set_monitor("eth-price", "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd", "ETH price in USD is above 5000", "5.0", "50", _hex(direct_alice)[-42:] if len(_hex(direct_alice))>42 else _hex(direct_alice), "ops")
    c.set_autonomous("OFF", "1000")
    _mock_satisfied(direct_vm, True, "high", '{"usd":6000}')
    r = c.tick("eth-price", "tick-off-1")
    assert r["status"] == "AUTONOMOUS_OFF"

def test_daily_cap_denies_second_price_tick(direct_vm, direct_deploy, direct_alice):
    c = _setup(direct_vm, direct_deploy, direct_alice)
    vendor = _hex(direct_alice)
    if len(vendor) > 42: vendor = "0x"+vendor[-40:]
    c.set_monitor("eth-price", "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd", "ETH price in USD is above 5000", "5.0", "150", vendor, "ops")
    # lower global cap to 200 -> two 150s should fail on second
    c.set_autonomous("ON", "200")
    _mock_satisfied(direct_vm, True, "high", '{"usd":5100}')
    r1 = c.tick("eth-price", "cap-1")
    assert r1["success"] is True
    _mock_satisfied(direct_vm, True, "high", '{"usd":5100}')
    r2 = c.tick("eth-price", "cap-2")
    assert r2["status"] == "DENIED_DAILY_AUTONOMOUS_CAP"
