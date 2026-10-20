"""Real-world walkthrough: a corporate treasury pays a supplier invoice.

Run (GLSim must be listening on the address in gltest.config.yaml):
    gltest examples/treasury-usecase/test_treasury_usecase.py -v -s

Story
-----
Acme Corp's treasury account holds USDC operating capital. A procurement
agent bot is delegated narrow spending authority to pay an approved cloud
vendor. Every payment crosses, in order:

    allowlist -> per-tx limit -> delegate limits -> daily limit
    -> attestation (compliance) -> encumbrance (available balance) -> settle

The scenario exercises, on the real GLSim consensus path:
  * delegated payment inside bounds (settles)
  * over-limit attempts (denied, funds untouched)
  * non-allowlisted recipient (denied)
  * delegate daily cap (denied)
  * compliance revocation -> all payments fail closed
  * attestation renewal -> payments resume
  * dispute + refund (compensating entry, history preserved)
  * delegation revocation -> agent loses all authority
  * final conservation audit (deposits - net sends == balance)
"""
import json
import time

from gltest import get_contract_factory, get_accounts
from gltest.assertions import tx_execution_succeeded

ACCOUNT_ID = "OPERATING"
W = 3000   # wait interval ms
R = 10     # wait retries


def _title(n, text):
    print("\n" + "=" * 72)
    print(f"STEP {n}  {text}")
    print("=" * 72)


def test_treasury_usecase_real_world_flow():
    accounts = get_accounts()
    assert len(accounts) >= 4, "need owner/agent/vendor/attester accounts"
    OWNER, AGENT, VENDOR, ATTESTER = accounts[0], accounts[1], accounts[2], accounts[3]

    print("\nACTORS")
    print(f"  treasury owner      : {OWNER.address}")
    print(f"  procurement agent   : {AGENT.address}")
    print(f"  cloud vendor        : {VENDOR.address}")
    print(f"  attestation issuer  : {ATTESTER.address}")

    # ------------------------------------------------------------------ setup
    _title(1, "Treasury deploys the Programmable Payment Account")
    factory = get_contract_factory(contract_file_path="ppa.py")
    c_owner = factory.deploy(account=OWNER)
    c_agent = factory.build_contract(contract_address=c_owner.address, account=AGENT)
    c_owner.initialize(args=[OWNER.address]).transact(wait_interval=W, wait_retries=R)
    print(f"  contract at {c_owner.address}")
    print("  owner registered; only this address can administer the account")

    _title(2, "Owner sets the spending policy (sub-account rules)")
    rules = json.dumps({
        "currency": "USDC",
        "per_tx_limit": "5000",          # max single payment
        "daily_limit": "10000",          # max total per 24h window
        "allowlist": [VENDOR.address],   # may only pay the approved vendor
        "require_attestation": True,     # compliance gate is ON
        "attestation_issuers": [ATTESTER.address],
        "attestation_policy_version": "v1",
    })
    c_owner.create_account(args=[ACCOUNT_ID, rules]).transact(wait_interval=W, wait_retries=R)
    print(f"  policy: {rules}")

    _title(3, "Capital arrives (in production: settled from a proof-of-payable claim)")
    c_owner.deposit(args=[ACCOUNT_ID, "50000"]).transact(wait_interval=W, wait_retries=R)
    acc = c_owner.get_account(args=[ACCOUNT_ID]).call()
    print(f"  balance = {acc['balance']} USDC, daily_spent = {acc['daily_spent']}")

    _title(4, "Compliance registers a valid vendor attestation")
    att1 = json.dumps({
        "subject": VENDOR.address, "issuer": ATTESTER.address, "status": "VALID",
        "issued_at": "2020-01-01T00:00:00Z", "expires_at": "2099-12-31T00:00:00Z",
        "evidence_hash": "sha256:kyc-bundle-2026", "policy_version": "v1",
    })
    c_owner.register_attestation(args=["ATT-1", att1]).transact(wait_interval=W, wait_retries=R)
    print("  ATT-1: subject=vendor, issuer=compliance, policy v1, VALID")

    _title(5, "Owner delegates narrow spending authority to the agent bot")
    expires = str(int(time.time()) + 7 * 86400)
    c_owner.delegate(args=["DEL-1", AGENT.address, "800", "2400", expires]).transact(
        wait_interval=W, wait_retries=R)
    print("  DEL-1: per-tx max 800, daily max 2400, expires in 7 days")
    print("  (delegation NARROWS: agent is tighter than the account's 5000/10000)")

    # -------------------------------------------------------- agent payments
    def pay(actor_contract, payment_id, amount, note, payee=None):
        """Send one payment and report the observable outcome."""
        receipt = actor_contract.send(
            args=[ACCOUNT_ID, payment_id, payee or VENDOR.address, amount]
        ).transact(wait_interval=W, wait_retries=R)
        if not tx_execution_succeeded(receipt):
            print(f"  {payment_id}: {amount} USDC -> REJECTED BY AUTHORITY "
                  f"(no authority for caller; execution failed, no record written)")
            return None
        rec = c_owner.get_payment(args=[payment_id]).call()
        if rec["status"] == "SETTLED":
            bal = c_owner.get_account(args=[ACCOUNT_ID]).call()["balance"]
            print(f"  {payment_id}: {amount} USDC -> SETTLED  (balance now {bal})  [{note}]")
        else:
            print(f"  {payment_id}: {amount} USDC -> DENIED/{rec['reason']}  [{note}]")
        return rec

    _title(6, "Agent pays invoice INV-1001: 800 USDC to the approved vendor")
    p1 = pay(c_agent, "INV-1001", "800", "within delegate per-tx 800 and daily 2400")
    assert p1["status"] == "SETTLED" and p1["actor"].startswith("delegate:")

    _title(7, "Agent tries to pay 1500 (under account limit 5000, over delegate 800)")
    pay(c_agent, "INV-1500", "1500", "delegation never widens")
    # denied attempts burn nothing:
    acc = c_owner.get_account(args=[ACCOUNT_ID]).call()
    print(f"  funds untouched: balance={acc['balance']}, daily_spent={acc['daily_spent']}")

    _title(8, "Agent tries to pay a NON-allowlisted recipient (rogue wiring attempt)")
    pay(c_agent, "ROGUE-PAY", "100", "policy allowlist", payee=OWNER.address)
    acc = c_owner.get_account(args=[ACCOUNT_ID]).call()
    print(f"  funds untouched: balance={acc['balance']}")

    _title(9, "Agent pays INV-1002 and INV-1003 (800 each) -> hits the 2400 daily cap")
    pay(c_agent, "INV-1002", "800", "delegate daily running total 1600")
    pay(c_agent, "INV-1003", "800", "delegate daily running total 2400 (capped)")

    _title(10, "Agent tries INV-1004 -> delegate daily limit exhausted")
    pay(c_agent, "INV-1004", "800", "2400 + 800 would exceed delegate daily 2400")
    acc = c_owner.get_account(args=[ACCOUNT_ID]).call()
    print(f"  account state: balance={acc['balance']}, daily_spent={acc['daily_spent']}")

    # ------------------------------------------------- compliance + recovery
    _title(11, "Compliance REVOKES the vendor attestation (audit finding)")
    c_owner.revoke_attestation(args=["ATT-1"]).transact(wait_interval=W, wait_retries=R)
    print("  ATT-1 status = REVOKED -> the gate is now closed for EVERYONE")
    pay(c_owner, "COMPLY-1", "500", "even the owner cannot pay without a valid attestation")

    _title(12, "Renewed attestation arrives -> payments resume")
    att2 = dict(json.loads(att1))
    att2["evidence_hash"] = "sha256:kyc-bundle-2026-renewed"
    c_owner.register_attestation(args=["ATT-2", json.dumps(att2)]).transact(
        wait_interval=W, wait_retries=R)
    print("  ATT-2 registered (subject=vendor, policy v1, VALID)")
    pay(c_owner, "RENEW-1", "500", "owner pays directly, within account limits")

    # ---------------------------------------------------- dispute + refund
    _title(13, "Vendor shipment dispute on INV-1001 -> refund")
    c_owner.dispute_payment(
        args=["DSP-1", "INV-1001", "delivery-mismatch",
              json.dumps({"invoice": "INV-1001", "issue": "2 of 5 servers DOA"})]
    ).transact(wait_interval=W, wait_retries=R)
    print("  dispute DSP-1 opened (delivery-mismatch)")
    c_owner.resolve_dispute(args=["DSP-1", "refund"]).transact(wait_interval=W, wait_retries=R)
    refunded = c_owner.get_payment(args=["INV-1001"]).call()
    acc = c_owner.get_account(args=[ACCOUNT_ID]).call()
    print(f"  remedy=refund -> balance {acc['balance']} (800 returned)")
    print(f"  INV-1001 record: status={refunded['status']}, amount={refunded['amount']}, "
          f"to={refunded['to']} (history preserved, not rewritten)")

    # -------------------------------------------------------- revocation
    _title(14, "Owner REVOKES the delegation (agent offboarding)")
    c_owner.revoke_delegation(args=["DEL-1"]).transact(wait_interval=W, wait_retries=R)
    print("  DEL-1 status = REVOKED")
    pay(c_agent, "AFTER-REVOKE", "100", "agent no longer has any authority")

    # -------------------------------------------------------------- audit
    _title(15, "Final audit")
    acc = c_owner.get_account(args=[ACCOUNT_ID]).call()
    settled_ids = ["INV-1001", "INV-1002", "INV-1003", "RENEW-1"]
    settled_sum = sum(int(c_owner.get_payment(args=[i]).call()["amount"]) for i in settled_ids)
    refunded_amt = int(c_owner.get_payment(args=["INV-1001"]).call()["amount"])
    expected = 50000 - settled_sum + refunded_amt

    print(f"  balance        : {acc['balance']} USDC")
    print(f"  daily_spent    : {acc['daily_spent']} (window within account daily 10000)")
    print(f"  settled total  : {settled_sum} (INV-1001/2/3 + RENEW-1)")
    print(f"  refunded       : {refunded_amt} (INV-1001 compensating entry)")
    print(f"  conservation   : 50000 - {settled_sum} + {refunded_amt} = {expected}")
    print(f"  delegation     : {c_owner.get_delegation(args=['DEL-1']).call()['status']}")
    print(f"  attestation ATT-1: {c_owner.get_attestation(args=['ATT-1']).call()['status']}, "
          f"ATT-2: {c_owner.get_attestation(args=['ATT-2']).call()['status']}")

    # DENIED attempts never moved funds:
    for pid, reason in [("INV-1500", "DELEGATE_PER_TX_LIMIT"),
                        ("ROGUE-PAY", "POLICY_DENYLIST"),
                        ("INV-1004", "DELEGATE_DAILY_LIMIT"),
                        ("COMPLY-1", "ATTESTATION_REVOKED")]:
        rec = c_owner.get_payment(args=[pid]).call()
        assert rec["status"] == "DENIED" and rec["reason"] == reason, (pid, rec)

    # Successes and conservation:
    assert int(acc["balance"]) == expected == 47900
    assert acc["daily_spent"] == "2900"          # 800*3 + 500 (refund does not un-spend)
    assert c_owner.get_payment(args=["INV-1001"]).call()["status"] == "REFUNDED"
    assert c_owner.get_delegation(args=["DEL-1"]).call()["status"] == "REVOKED"

    print("\nALL CHECKS PASSED: every gate behaved exactly as specified,")
    print("and every unit of value is accounted for.")
