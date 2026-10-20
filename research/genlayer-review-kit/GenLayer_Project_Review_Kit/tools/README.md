# Tools

These helpers are optional. They exist so the kit can be exported without depending on the original review workspace.

## `fetch_genlayer_contract.py`

Fetch and inspect GenLayer Intelligent Contract source from a deployed address, Studio URL, or explorer URL.

Examples:

```sh
python3 tools/fetch_genlayer_contract.py 0x0000000000000000000000000000000000000000 --network studio
python3 tools/fetch_genlayer_contract.py "https://explorer-bradbury.genlayer.com/address/0x..."
python3 tools/fetch_genlayer_contract.py 0x0000000000000000000000000000000000000000 --rpc-url "$RPC_URL"
```

The helper:

- tries known GenLayer RPC source-fetch shapes,
- saves source and JSON artifacts under `data/contract_fetch/`,
- runs Python compile and `genvm-lint` when available,
- prints a JSON summary.

If source cannot be fetched because of RPC/tool limits, treat the evidence as `accessible_limited`, not as a rejection reason.

Do not write "passed GenVM lint" unless this tool or another real linter was run successfully.
