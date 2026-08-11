#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""media_manifest.json を素材解析DB（非同梱）から生成する。

★配布物には窓単位の解析データ（71列）を含めない方針（2026-08-11）。
  検収(--verify-media)と件数検算に要る最小情報——クリップ名・実尺・窓数の集計——だけを出す。
  発注側マシンにDBがある場合のみ再生成できる。配布先ではこのスクリプトは実行不能で正しい。
"""
import sqlite3, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = sys.argv[1] if len(sys.argv) > 1 else \
    "/Volumes/Extreme SSD/FERIEST/01_assets/db_202608/feriest_0801-0805_windows_kitcopy.sqlite"

c = sqlite3.connect(DB)
out = {}
for prod, key, t1 in c.execute(
        "SELECT product, key, MAX(t1) FROM asset_windows_v2 "
        "WHERE product NOT LIKE '%_dup_%' GROUP BY product, key"):
    if not key.startswith(prod + "_"):
        continue
    clip = key[len(prod) + 1:]
    out.setdefault(prod, {"clips": {}, "n_windows": 0})
    out[prod]["clips"][clip] = round(t1, 2)
for prod, n in c.execute(
        "SELECT product, COUNT(*) FROM asset_windows_v2 "
        "WHERE product NOT LIKE '%_dup_%' GROUP BY product"):
    if prod in out:
        out[prod]["n_windows"] = n

doc = {
    "_note": "★原本フッテージの在庫表（検収と件数検算のためだけの最小情報）。"
             "クリップ名と実尺（秒・素材解析時の実測）。check_links.py --verify-media が "
             "ffprobe の実測と突合して 欠け/余分/取り違え/破損 を検出する。"
             "n_windows は時間窓の総数（集計値のみ）。★窓単位の解析データは配布物に含めない——"
             "候補は data/design/s34_FINAL3.json、追加の判断は実素材の実測と実画目視で行う（実測主義）。",
    "_generated_by": ".fork/gen_manifest.py（発注側マシンでのみ実行可能）",
    "products": out,
}
dst = os.path.join(ROOT, "data/asset_db/media_manifest.json")
json.dump(doc, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
tot_c = sum(len(v["clips"]) for v in out.values())
tot_w = sum(v["n_windows"] for v in out.values())
print(f"manifest: {len(out)}商材 / {tot_c}クリップ / 窓集計{tot_w} → {dst}")
for p, v in sorted(out.items()):
    print(f"  {len(v['clips']):3d}本 {v['n_windows']:5d}窓  {p[:34]}")
