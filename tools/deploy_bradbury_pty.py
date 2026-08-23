"""Deploy all Nomos primitive contracts to Testnet Bradbury via the Node CLI,
driven through a pseudo-tty so interactive prompts get answers.

Usage: python3 tools/deploy_bradbury.py
Requires: genlayer CLI on PATH, account 'default' created + funded.
"""
import os
import pty
import sys
import time

PASSWORD = "nomos-bradbury-2026"

CONTRACTS = [
    "proof_of_payable.py",
    "claim_verification.py",
    "claim_encumbrance.py",
    "capital_commitment.py",
    "policy_envelope.py",
    "workflow_authorization.py",
    "daa.py",
    "dal.py",
    "mandate_allocation.py",
    "gaia.py",
    "financial_contract.py",
]


def run_cli(args):
    """Run genlayer CLI answering password prompts."""
    pid, fd = pty.fork()
    if pid == 0:
        os.execvp("genlayer", ["genlayer"] + args)
        return
    out = b""
    while True:
        try:
            chunk = os.read(fd, 4096)
        except OSError:
            break
        if not chunk:
            break
        out += chunk
        if b"password" in chunk.lower():
            time.sleep(0.2)
            os.write(fd, (PASSWORD + "\n").encode())
    os.close(fd)
    _, status = os.waitpid(pid, 0)
    text = out.decode(errors="replace")
    ok = "successfully" in text.lower() or "deployed" in text.lower()
    return ok, text


def main():
    root = "/home/ubuntu/nomos"
    receipts = []
    for c in CONTRACTS:
        path = f"{root}/contracts/{c}"
        print(f"\n=== deploying {c} ===")
        ok, text = run_cli(["deploy", "--contract", path])
        print(text[-600:])
        addr = ""
        for line in text.splitlines():
            if "Contract Address" in line or "contract_address" in line.lower():
                addr = line.split(":")[-1].strip()
                break
        receipts.append((c, addr, ok))
    print("\n=== SUMMARY ===")
    for c, a, ok in receipts:
        print(f"{c}: {'OK' if ok else 'CHECK'} {a}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
