#!/usr/bin/env python3
"""grammar_log.py — 判断文法の追記（[5]学習ループ）。削除禁止・supersedeのみ。

使い方:
  python3 grammar_log.py add "<状況>" "<判断>" --source user --quote "<原文>"
  python3 grammar_log.py add "<状況>" "<判断>" --source sheet --supersedes G07
  python3 grammar_log.py list
追記先: このスキルの references/grammar.jsonl（正典 JUDGMENT-GRAMMAR.md へは
Claudeが定期的に昇格転記する）。
"""
import json, os, sys, argparse, datetime

LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "references", "grammar.jsonl")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add")
    p.add_argument("situation")
    p.add_argument("judgment")
    p.add_argument("--source", required=True, choices=["sheet", "g19", "user", "design"])
    p.add_argument("--quote", default="")
    p.add_argument("--supersedes", default=None)
    sub.add_parser("list")
    a = ap.parse_args()

    rows = []
    if os.path.exists(LOG):
        rows = [json.loads(l) for l in open(LOG, encoding="utf-8") if l.strip()]
    if a.cmd == "list":
        for r in rows:
            sup = f" (supersedes {r['supersedes']})" if r.get("supersedes") else ""
            print(f"{r['id']} [{r['source']}] {r['situation']} → {r['judgment']}{sup}")
        return
    nid = f"L{len(rows)+1:03d}"
    row = {"id": nid, "situation": a.situation, "judgment": a.judgment,
           "source": a.source, "quote": a.quote,
           "date": datetime.date.today().isoformat(), "supersedes": a.supersedes}
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"追記 {nid} → {LOG}")


if __name__ == "__main__":
    main()
