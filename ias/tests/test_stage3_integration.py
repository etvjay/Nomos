"""Full GenLayer-native Intelligent Account integration proof.

Run with GLSim available on :4000:
    gltest ias/tests/test_stage3_integration.py -q
"""
import json
import urllib.request

from genlayer_py import create_account, create_client

OWNER_KEY = "0x" + "22" * 32
RECIPIENT = "0x9f6aa7364d20cf25f054ea83f3cb950317fd34b6"
RECIPIENT2 = "0x8f6aa7364d20cf25f054ea83f3cb950317fd34b6"
ISSUER = "0x1111111111111111111111111111111111111111"


def _install_mock():
    body = json.dumps({
        "jsonrpc": "2.0", "method": "sim_installMocks",
        "params": {"llm_mocks": {
            r".*Extract.*price.*|.*WEBPAGE.*": {
                "value": "42", "confidence": "high", "found": True}},
            "strict": False}, "id": 1}).encode()
    req = urllib.request.Request("http://127.0.0.1:4000/api", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as response:
        result = json.loads(response.read())
    assert "error" not in result, result


def _ok(receipt):
    return str(receipt.get("status")) in {"1", "5", "7", "0x1", "0x5", "0x7", "ACCEPTED", "FINALIZED"}


def _write(client, address, method, args, *, mocked=False):
    if mocked:
        _install_mock()
    kwargs = {}
    tx = client.write_contract(address=address, function_name=method,
                               args=args, **kwargs)
    receipt = client.wait_for_transaction_receipt(tx)
    assert _ok(receipt), f"{method} failed: {receipt}"
    return receipt


def test_stage3_adjudication_proposal_autonomy_and_fail_closed():
    owner = create_account(OWNER_KEY)
    client = create_client(endpoint="http://127.0.0.1:4000/api", account=owner)
    code = open("contracts/ias_stage3.py").read()
    deploy_tx = client.deploy_contract(code=code)
    deploy = client.wait_for_transaction_receipt(deploy_tx)
    assert _ok(deploy), deploy
    address = ((deploy.get("data") or {}).get("contract_address")
               or (deploy.get("txDataDecoded") or {}).get("contractAddress"))
    assert address

    _write(client, address, "initialize", [owner.address])
    rules = {"daily_limit": "1000", "per_tx_limit": "500", "currency": "USDC",
             "require_attestation": True,
             "attestation_issuers": [ISSUER],
             "attestation_policy_version": "IAS-1"}
    _write(client, address, "create_account", ["ACC", json.dumps(rules)])
    _write(client, address, "deposit", ["ACC", "1000"])

    template = {"sub_account": "ACC", "to": RECIPIENT,
                "amount": "100", "payment_id": "AUTO-ACCEPTED"}
    _write(client, address, "create_monitor",
           ["M1", "mocked", "https://example.com", "price", "1", "above",
            "25.0", "GROUP", "1", json.dumps(template)])
    _write(client, address, "create_signal_group",
           ["GROUP", json.dumps(["M1"]), 1, 3600])
    _write(client, address, "set_execution_policy",
           ["GROUP", "0.5", "500", "500", json.dumps([RECIPIENT])])
    _write(client, address, "register_attestation", [
        "ATT-1", json.dumps({
            "subject": RECIPIENT, "issuer": ISSUER, "status": "VALID",
            "issued_at": "2020-01-01T00:00:00+00:00",
            "expires_at": "2099-01-01T00:00:00+00:00",
            "evidence_hash": "sha256:fixture",
            "policy_version": "IAS-1",
        })])
    _write(client, address, "set_kill_switch", ["ON"])

    monitor = _write(client, address, "check_monitor", ["M1"], mocked=True)
    assert _ok(monitor)
    m = client.read_contract(address=address, function_name="get_monitor", args=["M1"])
    assert m["last_status"] == "success"
    assert m["last_value"] == "42"

    correlation = _write(client, address, "evaluate_signal_group", ["GROUP"])
    assert _ok(correlation)
    decision = client.read_contract(address=address,
                                    function_name="get_latest_correlation",
                                    args=["GROUP"])
    assert decision["decision_status"] == "ACCEPTED"
    assert decision["verdict"] == "CONFIRMED"
    payment = client.read_contract(address=address, function_name="get_payment",
                                   args=["AUTO-ACCEPTED"])
    assert payment["status"] == "SETTLED"
    assert payment["actor"] == "autonomous"
    assert payment["decision_id"] == decision["correlation_id"]
    account = client.read_contract(address=address, function_name="get_account",
                                   args=["ACC"])
    assert account["balance"] == "900"

    # A second account has the same autonomy policy but no attestation. Its
    # proposal must be recorded as DENIED and must not debit the balance.
    rules2 = dict(rules)
    _write(client, address, "create_account", ["ACC2", json.dumps(rules2)])
    _write(client, address, "deposit", ["ACC2", "500"])
    template2 = {"sub_account": "ACC2", "to": RECIPIENT2,
                 "amount": "50", "payment_id": "AUTO-MISSING"}
    _write(client, address, "create_monitor",
           ["M2", "mocked", "https://example.com", "price", "1", "above",
            "25.0", "GROUP2", "1", json.dumps(template2)])
    _write(client, address, "create_signal_group",
           ["GROUP2", json.dumps(["M2"]), 1, 3600])
    _write(client, address, "set_execution_policy",
           ["GROUP2", "0.5", "500", "500", json.dumps([RECIPIENT2])])
    _write(client, address, "check_monitor", ["M2"], mocked=True)
    missing = _write(client, address, "evaluate_signal_group", ["GROUP2"])
    assert _ok(missing)
    missing_decision = client.read_contract(
        address=address, function_name="get_latest_correlation", args=["GROUP2"])
    assert missing_decision["decision_status"] == "ACCEPTED"
    denied = client.read_contract(address=address, function_name="get_payment",
                                  args=["AUTO-MISSING"])
    assert denied["status"] == "DENIED"
    assert denied["reason"] == "ATTESTATION_MISSING"
    account2 = client.read_contract(address=address, function_name="get_account",
                                    args=["ACC2"])
    assert account2["balance"] == "500"

    _write(client, address, "set_kill_switch", ["OFF"])
    _write(client, address, "check_monitor", ["M2"], mocked=True)
    disabled = _write(client, address, "evaluate_signal_group", ["GROUP2"])
    assert _ok(disabled)
    assert client.read_contract(address=address,
                                function_name="get_latest_execution",
                                args=["GROUP2"]) == "DISABLED"

    # Provider failure is a persisted UNDETERMINED observation, not a
    # reverted write and never an executable proposal.
    _write(client, address, "create_monitor", [
        "M3", "empty", "", "price",
        "not-a-number", "above", "25.0", "GROUP3", "1", "",
    ])
    failed_observation = _write(client, address, "check_monitor", ["M3"])
    assert _ok(failed_observation)
    failed_monitor = client.read_contract(address=address,
                                          function_name="get_monitor",
                                          args=["M3"])
    assert failed_monitor["last_status"] == "UNDETERMINED"
