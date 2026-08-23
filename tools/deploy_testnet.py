"""Deploy Nomos primitives to GenLayer Testnet Bradbury.

Uses genlayer_py client directly with the account key from gltest.config.yaml
(file is chmod 600; key never printed).

Run:
    source ~/nomos-venv312/bin/activate
    python tools/deploy_testnet.py <contract_filename_in_contracts_dir>
"""
import os
import sys

import yaml
from genlayer_py import create_client, create_account


def main():
    if len(sys.argv) != 2:
        print("usage: deploy_testnet.py <contracts-dir-filename>")
        return 2

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = yaml.safe_load(open(os.path.join(root, "gltest.config.yaml")))
    net_cfg = cfg["networks"]["testnet-bradbury"]
    rpc = net_cfg["url"].removesuffix("/api")  # genlayer_py talks to the RPC root, not /api
    private_key = net_cfg["accounts"][0]
    code_path = os.path.join(root, "contracts", sys.argv[1])
    code = open(code_path).read()

    account = create_account(private_key)
    print(f"deployer: {account.address}")
    client = create_client(endpoint=rpc, account=account)

    print(f"deploying {sys.argv[1]} ...")
    result = client.deploy_contract(code=code)
    addr = getattr(result, "contract_address", None) or (
        result.get("contract_address") if isinstance(result, dict) else str(result)
    )
    print(f"DEPLOYED: {addr}")

    # write deployment receipt
    receipts_dir = os.path.join(root, "convergence", "deployment")
    os.makedirs(receipts_dir, exist_ok=True)
    base = sys.argv[1].replace(".py", "")
    with open(os.path.join(receipts_dir, f"{base}-bradbury.json"), "w") as f:
        import json
        json.dump({
            "network": "testnet-bradbury",
            "chainId": "4221",
            "rpc": rpc,
            "deployer": account.address,
            "contractFile": sys.argv[1],
            "result": str(addr),
        }, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
