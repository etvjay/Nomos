#!/usr/bin/env python3
"""
Keeper — liveness only. Calls SDA.tick() every interval.
Judgment + money remain inside the contract's quorum + gates.
Usage:
  GL_RPC=https://rpc-bradbury.genlayer.com SDA_ADDR=0x... python3 keeper.py --monitor ops-sla --interval 300
Set KEEPER_PRIVKEY env or it uses the deployer key from ~/.config/foundry/keeperhub.env.
"""
import os, time, argparse, json, sys
from pathlib import Path

# local GenLayer SDK shim: reuse nomos gltest wiring
sys.path.insert(0, str(Path.home() / "nomos-venv312/lib/python3.12/site-packages"))

def load_privkey():
    if os.getenv("KEEPER_PRIVKEY"):
        return os.getenv("KEEPER_PRIVKEY")
    # fallback to deployer
    env = Path.home() / ".config/foundry/keeperhub.env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("KEEPER_PRIVKEY="):
                return line.split("=",1)[1].strip().strip('"').strip("'")
    raise RuntimeError("No KEEPER_PRIVKEY and no keeperhub.env")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--monitor", default="ops-sla")
    ap.add_argument("--interval", type=int, default=300)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--rpc", default=os.getenv("GL_RPC", "https://rpc-bradbury.genlayer.com"))
    args = ap.parse_args()
    print(f"[keeper] monitor={args.monitor} interval={args.interval}s rpc={args.rpc}")
    print("[keeper] liveness only — every tick is a real Bradbury tx (judgment + gates stay onchain).")
    print("[keeper] wiring via genlayer-js / py SDK: next commit plugs eth_sendTransaction here.")
    # stub: shows contract call shape; actual broadcast lands when SDA is deployed
    # keeper loop placeholder — real broadcast uses genlayer client with SDA_ADDR + tick_id=keep-{ts}
    if args.once:
        print("[keeper] once mode: would call SDA.tick(monitor_id, tick_id) now")
    else:
        print(f"[keeper] would loop every {args.interval}s — run with --once for deploy test")
