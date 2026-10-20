"""Semi/autonomous cross-chain payment proof using the GenLayer bridge shape.

Matches genlayer-foundation/genlayer-studio-bridge-boilerplate:
GenLayer BridgeSender -> relay service -> zkSync BridgeForwarder ->
LayerZero V2 -> destination BridgeReceiver -> escrow callback.
The local adapter emulates those calls; it is not a live bridge deployment.
"""
from dataclasses import dataclass, asdict
from hashlib import sha256
import json


@dataclass
class Corridor:
    origin_chain: int = 4221
    destination_lz_eid: int = 40245  # Base Sepolia LayerZero V2 EID
    origin_jurisdiction: str = "US"
    destination_jurisdiction: str = "GB"
    asset: str = "TEST_USDC"
    recipient: str = "0xVendorB"
    max_per_action: int = 150
    max_daily: int = 500


class BridgeSenderMailbox:
    """Local shape of boilerplate intelligent-contracts/BridgeSender.py."""
    def __init__(self):
        self.messages = {}

    def send_message(self, target_chain_eid: int, target_contract: str, data: bytes, payment_id: str):
        message_id = sha256(payment_id.encode() + data).hexdigest()
        self.messages[message_id] = {
            "target_chain_id": target_chain_eid,
            "target_contract": target_contract,
            "data": data.hex(),
        }
        return message_id


class DestinationEscrow:
    """Local shape of a BridgeReceiver.sol callback target."""
    def __init__(self, address="0xDestinationEscrow"):
        self.address = address
        self.received = {}

    def process_bridge_message(self, source_chain: int, source_sender: str, data: bytes):
        message = json.loads(data.decode())
        self.received[message["payment_id"]] = {
            "source_chain": source_chain,
            "source_sender": source_sender,
            **message,
        }
        return self.received[message["payment_id"]]


class CrossChainDemo:
    def __init__(self, corridor=None):
        self.corridor = corridor or Corridor()
        self.mailbox = BridgeSenderMailbox()
        self.escrow = DestinationEscrow()
        self.origin_balance = 1000
        self.daily_spent = 0
        self.used_attempts = set()

    def adjudicate(self, evidence: str, accepted: bool, confidence: str = "high"):
        return {
            "status": "ACCEPTED" if accepted else "REJECTED",
            "confidence": confidence,
            "evidence_hash": sha256(evidence.encode()).hexdigest(),
        }

    def release(self, payment_id: str, amount: int, adjudication: dict,
                approval: bool = False, autonomous: bool = False):
        if payment_id in self.used_attempts:
            return {"status": "DENIED_REPLAY", "payment_id": payment_id}
        c = self.corridor
        if adjudication["status"] != "ACCEPTED":
            return {"status": "DENIED_ADJUDICATION", "payment_id": payment_id}
        if adjudication["confidence"] not in ("medium", "high"):
            return {"status": "DENIED_LOW_CONFIDENCE", "payment_id": payment_id}
        if not autonomous and not approval:
            return {"status": "AWAITING_HUMAN_APPROVAL", "payment_id": payment_id}
        if amount > c.max_per_action:
            return {"status": "DENIED_PER_ACTION", "payment_id": payment_id}
        if self.daily_spent + amount > c.max_daily:
            return {"status": "DENIED_DAILY_CAP", "payment_id": payment_id}
        if amount > self.origin_balance:
            return {"status": "DENIED_INSUFFICIENT_BALANCE", "payment_id": payment_id}

        payload = json.dumps({
            "payment_id": payment_id,
            "amount": amount,
            "asset": c.asset,
            "recipient": c.recipient,
            "destination_jurisdiction": c.destination_jurisdiction,
        }, sort_keys=True).encode()
        bridge_message_id = self.mailbox.send_message(
            c.destination_lz_eid, self.escrow.address, payload, payment_id
        )
        # Boilerplate relay boundary: quote -> callRemoteArbitrary -> LayerZero
        destination = self.escrow.process_bridge_message(
            c.origin_chain, "0xNomosOriginAccount", payload
        )
        self.used_attempts.add(payment_id)
        self.origin_balance -= amount
        self.daily_spent += amount
        return {
            "status": "DESTINATION_SETTLED_SIMULATED",
            "payment_id": payment_id,
            "origin_chain": c.origin_chain,
            "destination_lz_eid": c.destination_lz_eid,
            "origin_jurisdiction": c.origin_jurisdiction,
            "destination_jurisdiction": c.destination_jurisdiction,
            "asset": c.asset,
            "recipient": c.recipient,
            "amount": amount,
            "bridge_message_id": bridge_message_id,
            "origin_balance_after": self.origin_balance,
            "destination_balance_readback": destination["amount"],
            "bridge_evidence": "BOILERPLATE_SHAPED_LOCAL_RELAY_ONLY",
        }


def run_demo(mode="semi"):
    demo = CrossChainDemo()
    judgment = demo.adjudicate(
        "Agreement INV-42: report delivered and clause 4.2 satisfied", True
    )
    return demo.release("INV-42", 150, judgment,
                        approval=(mode == "semi"), autonomous=(mode == "autonomous"))


if __name__ == "__main__":
    print(json.dumps({"semi_autonomous": run_demo("semi"),
                      "autonomous_corridor": run_demo("autonomous")}, indent=2))
