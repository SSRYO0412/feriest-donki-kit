#!/usr/bin/env python3
"""挿入映像（B-roll）の重複・順序・尺を機械で検査する。

なぜ要るか（2026-07-29 ユーザー指摘）:
  「後々に話が出てくるはずのものが最初にきてしまっていたり、カットが重複していたりする」
  「車のパンのうち、車体が正面から撮れていない・あまり良い絵じゃないものがある」
  ——どちらも全ショットを目視して初めて気づいた類で、機械で毎回止められるようにする。

検査するもの（全て0件でなければ FAIL）:
  1. 同一素材の**区間の重なり**           … 使い回し
  2. 同一素材の**使用回数**が上限超過      … 素材が痩せて見える
  3. 同一素材の**再登場が近すぎる**        … 直前に見た絵がまた出る
  4. 同一被写体タグの回数が上限超過
  5. 挿入尺が下限未満／素材の実尺を超える
  6. **先出し**: その被写体が話に出るより前に画が出ている
       （伏線の対象を回収発話より前に置かない＝CUT-QC-RULES 手順6の一般化）

先出しの判定には「タグ→その話題を指す言葉」の対応表が要る。
プロジェクト側に mention_map.json を置く:
  {"cargo": ["荷物", "荷室", "積め"], "seat_rear": ["後部座席", "後ろの席"]}
語はテロップ（または完成音声の語列）から検索する。

使い方:
  python3 qc_inserts.py <broll.json> <telops.json> --materials <実尺json>
        [--mention-map <map.json>] [--min-dur 1.2] [--max-use 2] [--max-tag 2]
        [--near 25] [--out qc/inserts_report.json]
"""
import json, sys, argparse, collections


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("broll")
    ap.add_argument("telops")
    ap.add_argument("--materials", required=True,
                    help='{"IMG_6230": 4.2, ...} 素材の実尺(秒)')
    ap.add_argument("--mention-map", default=None)
    ap.add_argument("--min-dur", type=float, default=1.2)
    ap.add_argument("--max-use", type=int, default=2)
    ap.add_argument("--max-tag", type=int, default=2)
    ap.add_argument("--near", type=float, default=25.0,
                    help="同一素材の再登場がこの秒数以内なら近すぎる")
    ap.add_argument("--out", default="qc/inserts_report.json")
    ap.add_argument("--windows-db", default=None,
                    help="asset_windows を持つSQLite。指定すると人が確定したBANNED/NO-GO窓に"
                         "掛かる挿入を検出する（設計スクリプトへの手書きBANNEDを廃止するための正）")
    ap.add_argument("--rel-prefix", default="",
                    help="broll の src（ファイル名）を asset_windows.rel に解決する接頭辞")
    a = ap.parse_args()

    br = load(a.broll)
    ins = br["inserts"] if isinstance(br, dict) else br
    tl = load(a.telops)
    tel = tl["telops"] if isinstance(tl, dict) else tl
    mats = load(a.materials)
    mmap = load(a.mention_map) if a.mention_map else {}

    ng = []
    warn = []   # NGではないが見落とすと事故る項目（CONDITIONAL窓の条件など・2026-07-30追加）

    # --- 1〜3. 素材の重なり・回数・近さ ---
    by = collections.defaultdict(list)
    for x in ins:
        m = x["src"].split(".")[0]
        by[m].append((x["src_in"], x["src_in"] + x["dur"], x["tl_in"], x.get("tag", "")))
    for m, r in by.items():
        r.sort()
        for p, q in zip(r, r[1:]):
            if q[0] < p[1] - 1e-6:
                ng.append({"type": "素材の区間が重なる", "material": m,
                           "detail": f"{p[0]:.2f}-{p[1]:.2f}(tl{p[2]:.1f}) と {q[0]:.2f}-{q[1]:.2f}(tl{q[2]:.1f})"})
        if len(r) > a.max_use:
            ng.append({"type": "同一素材の使用回数が上限超過", "material": m,
                       "detail": f"{len(r)}回（上限{a.max_use}）: " +
                                 ", ".join(f"tl{x[2]:.1f}" for x in r)})
        t = sorted(x[2] for x in r)
        for p, q in zip(t, t[1:]):
            if q - p < a.near:
                ng.append({"type": "同一素材の再登場が近すぎる", "material": m,
                           "detail": f"tl{p:.1f} と tl{q:.1f}（{q-p:.1f}秒差・下限{a.near}秒）"})

    # --- 4. タグ ---
    tg = collections.Counter(x.get("tag", "") for x in ins)
    for k, v in tg.items():
        if v > a.max_tag:
            ng.append({"type": "被写体タグが上限超過", "material": k,
                       "detail": f"{v}回（上限{a.max_tag}）"})

    # --- 5. 尺 ---
    for x in ins:
        m = x["src"].split(".")[0]
        if x["dur"] < a.min_dur - 1e-6:
            ng.append({"type": "挿入尺が下限未満", "material": m,
                       "detail": f"tl{x['tl_in']:.1f} {x['dur']:.2f}秒 < {a.min_dur}秒"})
        if m in mats and x["src_in"] + x["dur"] > mats[m] + 0.05:
            ng.append({"type": "素材の実尺を超える", "material": m,
                       "detail": f"tl{x['tl_in']:.1f} {x['src_in']}+{x['dur']} > 実尺{mats[m]}"})

    # --- 5.5 使用可能窓DB（asset_windows）との突合 ---
    #   ★人が確定した行（confirmed_by NOT NULL）だけを根拠にする。AI提案のままの行は使わない。
    if a.windows_db:
        import sqlite3
        con = sqlite3.connect(a.windows_db)
        con.row_factory = sqlite3.Row
        # ★テーブル自動検出: asset_windows_v2(49列)があればそちらを正とする（2026-07-30）
        tabs = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        WT = "asset_windows_v2" if "asset_windows_v2" in tabs else "asset_windows"
        has_cond = "conditional_terms" in [r[1] for r in con.execute(f"PRAGMA table_info({WT})")]
        for x in ins:
            m = x["src"]
            rel = (a.rel_prefix.rstrip("/") + "/" + m) if a.rel_prefix else m
            t0, t1 = x["src_in"], x["src_in"] + x["dur"]
            rows = con.execute(
                f"SELECT * FROM {WT} WHERE superseded=0 AND confirmed_by IS NOT NULL "
                "AND verdict IN ('BANNED','NO-GO') AND (rel=? OR rel LIKE ?) "
                "AND NOT(t1<=? OR t0>=?)", (rel, f"%/{m}", t0, t1)).fetchall()
            for r in rows:
                ng.append({"type": "確定済みBANNED/NO-GO窓に掛かる", "material": m,
                           "detail": f"使用 {t0:.2f}-{t1:.2f} × {r['verdict']}窓 {r['t0']:.2f}-{r['t1']:.2f}"
                                     f"（{r['reason']}／確定: {r['confirmed_by']}）"})
            # CONDITIONAL窓は「条件を守れば可」なのでNGにせず警告で出す（条件の見落とし防止）
            if has_cond:
                for r in con.execute(
                        f"SELECT * FROM {WT} WHERE superseded=0 AND confirmed_by IS NOT NULL "
                        "AND verdict='CONDITIONAL' AND (rel=? OR rel LIKE ?) "
                        "AND NOT(t1<=? OR t0>=?)", (rel, f"%/{m}", t0, t1)).fetchall():
                    warn.append({"type": "CONDITIONAL窓の条件を守れているか要確認", "material": m,
                                 "detail": f"使用 {t0:.2f}-{t1:.2f} × 条件窓 {r['t0']:.2f}-{r['t1']:.2f}"
                                           f"（条件: {r['conditional_terms']}）"})
        con.close()

    # --- 6. 先出し ---
    first_mention = {}
    for tag, words in mmap.items():
        for t in tel:
            if any(w in t["text"] for w in words):
                first_mention[tag] = t["s"]
                break
    for x in ins:
        tag = x.get("tag", "")
        if tag in first_mention and x["tl_in"] + x["dur"] < first_mention[tag] - 0.5:
            ng.append({"type": "先出し（話に出る前に画が出ている）", "material": x["src"],
                       "detail": f"tag={tag} 画 tl{x['tl_in']:.1f}〜{x['tl_in']+x['dur']:.1f} / "
                                 f"言及は tl{first_mention[tag]:.1f} から"})

    rep = {"broll": a.broll, "inserts": len(ins),
           "materials_used": {m: len(v) for m, v in sorted(by.items())},
           "tags": dict(tg), "first_mention": first_mention,
           "violations": ng, "warnings": warn,
           "verdict": "PASS" if not ng else "FAIL"}
    import os
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(rep, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"挿入 {len(ins)}件 / 素材 {len(by)}種")
    print(f"違反 {len(ng)}件 / 警告 {len(warn)}件")
    for x in ng:
        print(f"  ★[{x['type']}] {x['material']}: {x['detail']}")
    for x in warn:
        print(f"  ⚠[{x['type']}] {x['material']}: {x['detail']}")
    print(f"→ {a.out}")
    sys.exit(0 if not ng else 1)


if __name__ == "__main__":
    main()
