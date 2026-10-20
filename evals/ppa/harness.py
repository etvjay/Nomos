#!/usr/bin/env python3
"""
PPA eval harness — deterministic, exact_match per gate.
Usage: python harness.py [--corpus corpus.jsonl] [--adapter ppa_adapter]

Adapter must implement: handle(item) -> dict
  input: item["input"]  -> output: {status, code?, settled?, available?, committed?, ...}
If no adapter, runs in --check mode (validates corpus shape only).

Logs: prints per-id PASS/FAIL, summary, and writes evals/ppa/result.json
"""
import argparse, json, hashlib, pathlib, sys

ROOT = pathlib.Path(__file__).parent

def load_corpus(path):
    items=[]
    with open(path) as f:
        for i,line in enumerate(f,1):
            line=line.strip()
            if not line: continue
            try:
                items.append(json.loads(line))
            except Exception as e:
                raise SystemExit(f"corpus json error line {i}: {e}")
    return items

def corpus_hash(path):
    h=hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
    return h[:16]

def compare(expected, actual):
    """Shallow exact_match per gate — expected keys must equal actual keys."""
    mism=[]
    for k,v in expected.items():
        if k not in actual:
            mism.append(f"missing key {k}: expected {v!r}")
        elif actual[k] != v:
            mism.append(f"{k}: expected {v!r} got {actual[k]!r}")
    return mism

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(ROOT/"corpus.jsonl"))
    ap.add_argument("--thresholds", default=str(ROOT/"thresholds.yaml"))
    ap.add_argument("--adapter", default=None, help="python module path e.g. ppa_adapter:handle or file.py")
    ap.add_argument("--check", action="store_true", help="validate corpus only")
    args=ap.parse_args()

    items=load_corpus(args.corpus)
    h=corpus_hash(args.corpus)
    print(f"corpus: {args.corpus}  hash={h}  items={len(items)}")
    # validate shape
    for it in items:
        assert "id" in it and "gate" in it and "input" in it and "expected" in it and "weight" in it, f"bad shape {it.get('id')}"
    if args.check or not args.adapter:
        print("check mode — no adapter, corpus valid. Wire adapter to run for real.")
        print("example adapter: create nomos/evals/ppa/ppa_adapter.py with def handle(item): ...")
        for it in items:
            print(f"  - {it['id']:40s} gate={it['gate']:22s} weight={it['weight']}")
        return 0

    # load adapter: "path:func" or "module.func"
    handle=None
    if ":" in args.adapter:
        mod, func = args.adapter.split(":",1)
        import importlib
        m=importlib.import_module(mod)
        handle=getattr(m, func)
    else:
        # file path
        import importlib.util
        p=pathlib.Path(args.adapter)
        spec=importlib.util.spec_from_file_location("adapter", p)
        m=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        handle=getattr(m, "handle")

    results=[]
    for it in items:
        actual=handle(it)
        mism=compare(it["expected"], actual)
        ok=len(mism)==0
        results.append({"id": it["id"], "gate": it["gate"], "weight": it["weight"], "ok": ok, "mism": mism, "expected": it["expected"], "actual": actual})
        tag="PASS" if ok else "FAIL"
        print(f"{tag} {it['id']:40s} gate={it['gate']:22s} weight={it['weight']:8s} {' '.join(mism) if mism else ''}")

    crit_fail=sum(1 for r in results if not r["ok"] and r["weight"]=="critical")
    major_fail=sum(1 for r in results if not r["ok"] and r["weight"]=="major")
    total_fail=sum(1 for r in results if not r["ok"])
    verdict="GREEN" if crit_fail==0 and major_fail==0 else ("YELLOW" if crit_fail==0 else "RED")
    print(f"\nsummary: {len(results)-total_fail}/{len(results)} pass  critical_fail={crit_fail} major_fail={major_fail}  verdict={verdict}  hash={h}")
    out=ROOT/"result.json"
    out.write_text(json.dumps({"corpus_hash": h, "verdict": verdict, "crit_fail": crit_fail, "major_fail": major_fail, "results": results}, indent=2))
    print(f"wrote {out}")
    return 0 if verdict!="RED" else 1

if __name__=="__main__":
    raise SystemExit(main())
