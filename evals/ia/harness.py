#!/usr/bin/env python3
"""
IA eval harness — deterministic + hybrid judge scoring.
Mirrors nomos/evals/ppa/harness.py.
Usage: python harness.py [--corpus corpus.jsonl] [--adapter ia_adapter]

Adapter must implement: handle(item) -> dict
  input: item["input"] -> output: dict matching item["expected"] (or judge rubric)
If no adapter, runs in --check mode (validates corpus shape only).

Scoring:
  scoring==exact -> exact_match on expected keys
  scoring==judge -> keyword/rubric check (ia-008, ia-017, ia-018)

Logs: prints per-id PASS/FAIL, summary, writes result.json
"""
import argparse, json, hashlib, pathlib, sys, re

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
    """Shallow exact_match — expected keys must equal actual keys."""
    mism=[]
    for k,v in expected.items():
        if k not in actual:
            mism.append(f"missing key {k}: expected {v!r}")
        elif actual[k] != v:
            mism.append(f"{k}: expected {v!r} got {actual[k]!r}")
    return mism

def judge_compare(item, actual):
    """Rubric/keyword check for scoring==judge items."""
    iid = item["id"]
    expected = item["expected"]
    inp = item["input"]
    mism=[]

    if iid == "ia-008-coordinator-dispute-category-judgment":
        # expected category delivery-mismatch
        cat = str(actual.get("category","")).lower()
        exp_cat = str(expected.get("category","")).lower()
        # pass if exact or contains delivery
        if cat != exp_cat:
            # allow keyword containment
            if "delivery" not in cat or "mismatch" not in cat:
                mism.append(f"category: expected {exp_cat!r} got {cat!r}")
        # also accept rubric keyword in explanation if present
        if mism and "rubric" not in actual:
            pass

    elif iid == "ia-017-judgment-explanation-quality":
        exp_text = str(actual.get("explanation","")).lower()
        # must mention SLA breach overrides price
        required = ["sla", "breach"]
        # at least sla+breach, ideally price/overrides
        for kw in required:
            if kw not in exp_text:
                mism.append(f"explanation missing keyword {kw!r}: got {actual.get('explanation')!r}")
        if "price" not in exp_text and "overrid" not in exp_text:
            mism.append(f"explanation should mention price/overrides: got {actual.get('explanation')!r}")
        # score check if provided
        if "score" in actual and "score_min" in expected:
            if actual["score"] < expected["score_min"]:
                mism.append(f"score {actual['score']} < min {expected['score_min']}")

    elif iid == "ia-018-monitor-price-extraction-judgment":
        # expected price 3421.11 tolerance 10 bps = 0.1%
        exp_price = expected.get("price", inp.get("truth", 3421.11))
        tol_bps = expected.get("tolerance_bps", inp.get("tolerance_bps", 10))
        actual_price = actual.get("price")
        if actual_price is None:
            mism.append(f"missing price: expected {exp_price}")
        else:
            try:
                diff = abs(float(actual_price) - float(exp_price))
                allowed = float(exp_price) * float(tol_bps) / 10000.0
                # for ia-018 generous: also allow parsing exact string
                if diff > allowed + 1e-9:
                    mism.append(f"price {actual_price} diff {diff:.4f} > allowed {allowed:.4f} (tolerance {tol_bps} bps)")
            except Exception as e:
                mism.append(f"price compare error: {e}")

    else:
        # generic judge: exact_match but ignore rubric/score_min keys
        filtered_expected = {k:v for k,v in expected.items() if k not in ("rubric","score_min")}
        for k,v in filtered_expected.items():
            if k not in actual:
                mism.append(f"missing key {k}: expected {v!r}")
            elif isinstance(v, float):
                try:
                    if abs(float(actual[k]) - float(v)) > 1e-6:
                        mism.append(f"{k}: expected {v!r} got {actual[k]!r}")
                except:
                    if actual[k] != v:
                        mism.append(f"{k}: expected {v!r} got {actual[k]!r}")
            elif actual[k] != v:
                mism.append(f"{k}: expected {v!r} got {actual[k]!r}")

    return mism

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(ROOT/"corpus.jsonl"))
    ap.add_argument("--thresholds", default=str(ROOT/"thresholds.yaml"))
    ap.add_argument("--adapter", default=None, help="python module path e.g. ia_adapter:handle or file.py")
    ap.add_argument("--check", action="store_true", help="validate corpus only")
    args=ap.parse_args()

    items=load_corpus(args.corpus)
    h=corpus_hash(args.corpus)
    print(f"corpus: {args.corpus}  hash={h}  items={len(items)}")
    for it in items:
        assert "id" in it and "gate" in it and "input" in it and "expected" in it and "weight" in it, f"bad shape {it.get('id')}"
        # scoring defaults to exact if missing
        if "scoring" not in it:
            it["scoring"] = "exact"

    if args.check or not args.adapter:
        print("check mode — no adapter, corpus valid. Wire adapter to run for real.")
        print("example adapter: create nomos/evals/ia/ia_adapter.py with def handle(item): ...")
        for it in items:
            print(f"  - {it['id']:40s} gate={it['gate']:22s} weight={it['weight']:8s} scoring={it.get('scoring','exact')}")
        return 0

    handle=None
    if ":" in args.adapter:
        mod, func = args.adapter.split(":",1)
        import importlib
        m=importlib.import_module(mod)
        handle=getattr(m, func)
    else:
        import importlib.util
        p=pathlib.Path(args.adapter)
        spec=importlib.util.spec_from_file_location("adapter", p)
        m=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        handle=getattr(m, "handle")

    results=[]
    for it in items:
        actual=handle(it)
        scoring = it.get("scoring","exact")
        if scoring == "judge":
            mism=judge_compare(it, actual)
        else:
            mism=compare(it["expected"], actual)
        ok=len(mism)==0
        results.append({"id": it["id"], "gate": it["gate"], "weight": it["weight"], "scoring": scoring, "ok": ok, "mism": mism, "expected": it["expected"], "actual": actual})
        tag="PASS" if ok else "FAIL"
        print(f"{tag} {it['id']:40s} gate={it['gate']:22s} weight={it['weight']:8s} scoring={scoring:6s} {' '.join(mism) if mism else ''}")

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
