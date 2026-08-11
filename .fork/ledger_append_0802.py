#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""0802 DBなしビルドの台帳記録（オフライン台帳・追記のみ）。"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rec = {"date": "2026-08-11", "video_id": "0802", "record": "0802 DBなしビルド v1→v4",
  "target": "/Volumes/Extreme SSD/FERIEST/02_work/premiere/jsx_20260811_0802/ (b01〜b12)",
  "version": "v4", "adopted": "採用候補",
  "changes": "ゼロから構築(13→12ショット/316F)。隔離レビュー3体17指摘→14採用3一部採用。"
             "c11(横クロップ靴ひも)はG90-9白飛び外れ値2.1%で破棄しc12を42Fへ延長。"
             "絵文字😂がT6末尾の『い』に重なる欠陥を画素実測(x 0.768→0.797)で修正。"
             "音声13クリップ除去(+12F超過の解消)",
  "reasons_user_quotes": ["これでDBを使わず、一本作ってみよう"],
  "verify": "G90 14/14 PASS・316F/1080x1920実測・キーフレームSS 5点目視",
  "rejected": "v1(設計・レビューNG17)/v2(c11白飛び・😂位置NG)/v3(😂位置NG)は却下版として保持"}
with open(os.path.join(ROOT, "data/ledger/revision_records.jsonl"), "a", encoding="utf-8") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
p = os.path.join(ROOT, "data/ledger/adoption.json")
ad = json.load(open(p)) if os.path.exists(p) else {}
ad.setdefault("videos", {})["0802"] = {
 "adopted_mp4": "/Volumes/Extreme SSD/FERIEST/02_work/premiere/verify_20260811/0802_v4.mov",
 "adopted_prproj": "/Volumes/Extreme SSD/FERIEST/02_work/premiere/FERIEST_0802_spray_v1.prproj",
 "sequence": "0802_spray", "document_id": "020e440e-7df9-4dfc-b377-18a802392506",
 "status": "検証版(v4)・ユーザー目視待ち。ナレーション/BGM/SEは未実装(0801と同方針)",
 "updated": "2026-08-11",
 "history": [{"v": "v1-v3", "verdict": "却下", "why": "レビューNG17件/c11白飛び/😂位置"},
             {"v": "v4", "verdict": "採用候補", "why": "G90 14/14 PASS"}],
 "escalations": ["★R2『水を弾く瞬間』は全素材不在→結果の水滴カットで代替(要発注側承認)",
                 "★s2『床に置いた靴』は素材が机上デモのみ→ロケ混在(要許容判断)",
                 "★s1『手が止まる』不在→2本差し込み(IMG_8708)で代替"]}
json.dump(ad, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("台帳OK")
