#!/usr/bin/env python3
"""Fetch and inspect GenLayer Intelligent Contract source by address.

This helper is intentionally dependency-light so review agents can use it in
fresh contexts. It tries the known GenLayer RPC parameter shapes, decodes the
returned source, saves review artifacts, and runs local static checks.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "contract_fetch"

NETWORKS = {
    "studio": "https://studio.genlayer.com/api",
    "studionet": "https://studio.genlayer.com/api",
    "bradbury": "https://rpc-bradbury.genlayer.com",
    "asimov": "https://rpc-asimov.genlayer.com",
    "local": "http://127.0.0.1:4000/api",
}

ADDRESS_RE = re.compile(r"0x[a-fA-F0-9]{40}")


def extract_address(value: str) -> str:
    match = ADDRESS_RE.search(value)
    if not match:
        raise SystemExit(f"No 0x40-hex contract address found in: {value}")
    return match.group(0)


def infer_network(value: str) -> str | None:
    host = urlparse(value).netloc.lower()
    if "explorer-studio" in host or "studio.genlayer.com" in host:
        return "studio"
    if "explorer-bradbury" in host or "rpc-bradbury" in host:
        return "bradbury"
    if "explorer-asimov" in host or "rpc-asimov" in host:
        return "asimov"
    return None


def rpc_call(rpc_url: str, method: str, params):
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": int(time.time() * 1000),
    }
    request = Request(
        rpc_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "accept": "application/json",
            "user-agent": "Mozilla/5.0 GenLayer-Contract-Review/1.0",
        },
        method="POST",
    )
    with urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def result_error(payload) -> str | None:
    if not isinstance(payload, dict):
        return "non-object JSON-RPC response"
    error = payload.get("error")
    if error:
        return json.dumps(error, sort_keys=True)
    if payload.get("result") in (None, ""):
        return "empty result"
    return None


def try_rpc_shapes(rpc_url: str, method: str, address: str):
    shapes = [
        [address],
        [{"address": address}],
        [{"contract_address": address}],
        [{"contractAddress": address}],
    ]
    attempts = []
    for params in shapes:
        try:
            payload = rpc_call(rpc_url, method, params)
            attempts.append({"params": params, "response": payload})
            if result_error(payload) is None:
                return payload, attempts
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            attempts.append({"params": params, "error": str(exc)})
    return None, attempts


def maybe_decode_base64(value: str) -> str:
    compact = value.strip()
    if compact.startswith("0x"):
        try:
            raw = bytes.fromhex(compact[2:])
            text = raw.decode("utf-8", errors="replace")
            if "class " in text or "from genlayer" in text or "@gl.public" in text:
                return text
        except Exception:
            pass
    try:
        raw = base64.b64decode(compact, validate=True)
        text = raw.decode("utf-8", errors="replace")
        if "class " in text or "from genlayer" in text or "@gl.public" in text or "Depends" in text:
            return text
    except Exception:
        pass
    return value


def extract_source(result) -> str | None:
    if isinstance(result, str):
        return maybe_decode_base64(result)
    if isinstance(result, dict):
        for key in ("source", "source_code", "code", "contract_code", "contractCode", "bytecode"):
            value = result.get(key)
            if isinstance(value, str) and value:
                return maybe_decode_base64(value)
        for value in result.values():
            if isinstance(value, str) and ("from genlayer" in value or "@gl.public" in value):
                return maybe_decode_base64(value)
    return None


def source_features(text: str) -> dict:
    return {
        "chars": len(text),
        "depends": re.findall(r'\{\s*"Depends"\s*:\s*"([^"]+)"\s*\}', text),
        "classes": re.findall(r"^class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", text, re.M),
        "public_view": len(re.findall(r"@gl\.public\.view", text)),
        "public_write": len(re.findall(r"@gl\.public\.write", text)),
        "payable": "@gl.public.write.payable" in text,
        "nondet_web": len(re.findall(r"gl\.nondet\.web\.", text)),
        "nondet_prompt": len(re.findall(r"gl\.nondet\.exec_prompt|exec_prompt", text)),
        "eq_principle": len(re.findall(r"eq_principle|prompt_comparative|strict_eq", text)),
        "run_nondet_unsafe": len(re.findall(r"run_nondet_unsafe", text)),
        "tree_map": "TreeMap" in text,
        "dyn_array": "DynArray" in text,
        "bare_exception": len(re.findall(r"raise\s+Exception\(", text)),
    }


def run_command(args: list[str], cwd: Path) -> dict:
    if not shutil.which(args[0]):
        return {"available": False, "returncode": None, "stdout": "", "stderr": f"{args[0]} not found"}
    proc = subprocess.run(args, cwd=str(cwd), text=True, capture_output=True, timeout=120)
    payload = {"available": True, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    try:
        payload["json"] = json.loads(proc.stdout)
    except Exception:
        pass
    return payload


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and inspect GenLayer contract source by address.")
    parser.add_argument("address_or_url", help="0x contract address, Studio import URL, or explorer address URL")
    parser.add_argument("--network", choices=["auto", *NETWORKS.keys()], default="auto")
    parser.add_argument("--rpc-url", help="Custom JSON-RPC endpoint. Overrides --network.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--no-lint", action="store_true", help="Fetch only; skip py_compile and genvm-lint.")
    args = parser.parse_args()

    address = extract_address(args.address_or_url)
    inferred = infer_network(args.address_or_url)
    if args.rpc_url:
        targets = [("custom", args.rpc_url)]
    elif args.network != "auto":
        targets = [(args.network, NETWORKS[args.network])]
    else:
        ordered = []
        if inferred:
            ordered.append(inferred)
        ordered.extend(n for n in ("studio", "bradbury", "asimov") if n not in ordered)
        targets = [(name, NETWORKS[name]) for name in ordered]

    run_dir = args.output_dir / f"{address.lower()}-{int(time.time())}"
    run_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "address": address,
        "input": args.address_or_url,
        "network": None,
        "rpc_url": None,
        "access": "inaccessible",
        "source_path": None,
        "schema_path": None,
        "features": None,
        "attempts_path": str(run_dir / "rpc_attempts.json"),
        "lint": None,
        "compile": None,
        "errors": [],
    }

    all_attempts = []
    source = None
    schema_payload = None
    for network, rpc_url in targets:
        code_payload, code_attempts = try_rpc_shapes(rpc_url, "gen_getContractCode", address)
        all_attempts.append({"network": network, "rpc_url": rpc_url, "method": "gen_getContractCode", "attempts": code_attempts})
        if code_payload:
            source = extract_source(code_payload.get("result"))
            if source:
                summary["network"] = network
                summary["rpc_url"] = rpc_url
                schema_payload, schema_attempts = try_rpc_shapes(rpc_url, "gen_getContractSchema", address)
                all_attempts.append({"network": network, "rpc_url": rpc_url, "method": "gen_getContractSchema", "attempts": schema_attempts})
                break

    write_json(run_dir / "rpc_attempts.json", all_attempts)

    if not source:
        summary["errors"].append("Could not retrieve contract source from attempted RPC endpoints.")
        write_json(run_dir / "summary.json", summary)
        print(json.dumps(summary, sort_keys=True))
        sys.exit(2)

    source_path = run_dir / f"{address.lower()}.py"
    source_path.write_text(source)
    summary["access"] = "reviewed"
    summary["source_path"] = str(source_path)
    summary["features"] = source_features(source)

    if schema_payload:
        schema_path = run_dir / "schema.json"
        write_json(schema_path, schema_payload)
        summary["schema_path"] = str(schema_path)

    if not args.no_lint:
        summary["compile"] = run_command([sys.executable, "-m", "py_compile", str(source_path)], cwd=ROOT)
        summary["lint"] = run_command(["genvm-lint", "check", str(source_path), "--json"], cwd=ROOT)
        write_json(run_dir / "compile.json", summary["compile"])
        write_json(run_dir / "genvm_lint.json", summary["lint"])

    write_json(run_dir / "summary.json", summary)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
