#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""projects/<video_id>.json を生成する。

★手で書かない。参考の実測値（REFERENCE-TARGETS.json）とコンテ（data/conte/conte.json）と
素材DBから機械的に導く。数値の出どころが辿れないと『瓜二つ』の判定が感想に戻るため。

  python3 .fork/gen_projects.py          # 生成
  python3 .fork/gen_projects.py --check  # 既存と一致するか検算（差分があれば非0で終了）
"""
import json, os, sqlite3, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def p(*a): return os.path.join(ROOT, *a)

TARGETS = json.load(open(p(".fork/REFERENCE-TARGETS.json")))
CONTE   = json.load(open(p("data/conte/conte.json")))
BASE    = json.load(open(p(".fork/project.base.json")))

MEDIA_DIR = {
    "0801": "海老ドーン贅沢ぷりぷり海老マヨピザ",
    "0802": "ド情熱逆さで使える消臭スプレー&速乾防水スプレー",
    "0803": "おうちでライブマイク",
    "0804": "Reebokファン付きベスト",
    "0805": "Mii +フレグランスオイル、ロックミルク",
}

# ★クライアント赤入れ（字コンテの緑枠/青枠）。原文のまま。要約しない
CLIENT_NOTES = {
    "0801": ["「お盆はトロリスタのピザに決まり！」→「お盆はドンキのピザに決まり！」",
             "商品の魅力はしっかり伝わる構成になっていると思いますが、全体的にストレートな商品紹介にまとまっている印象もあるので、SNS動画としてはもう少し遊び心や視聴者がクスッとできる要素があっても良さそうと感じてます。（このコンテに限った話ではなく全体的に）"],
    "0802": ["フックの最初のカットで商品2本をまず映す",
             "スプレー後に水を弾くカットを入れる"],
    "0803": ["パッケージの「歌いたい場所があなたのステージ！」をファーストカットに",
             "2カット目に商品全景",
             "「3色展開」専用カットは不要"],
    "0804": ["「正面から見たらファン付きってバレない」→ポジティブな文言へ",
             "風より「見た目がスマートで普段使いしやすい」を訴求",
             "1カットごとに異なる訴求を詰め込むのではなく、動画全体で一番伝えたい訴求を決め、その訴求をカット同士でつなげるような構成を意識いただきたいです。"],
    "0805": ["毛先だけのアップは禁止（パサついて見える）",
             "毛束全体のまとまり・ツヤを見せる",
             "香りの訴求をもっと最初に"],
}

# ★全数検索で不在を確定済み。『探せば見つかる』と誤認しないこと
NO_MATERIAL = {
    "0803": [{"要求": "3色展開", "撮られていないもの": "3本目の色", "確定": "★実物は黒とシルバーの2色のみ。1窓も存在しない。画と文言が食い違うのでクライアント確認が要る"}],
    "0804": [{"要求": "モバイルバッテリーで起動", "撮られていないもの": "接続の瞬間", "確定": "テロップ/ナレで補う"},
             {"要求": "1万円以下", "撮られていないもの": "価格を示す画", "確定": "テロップで補う"}],
    "0805": [{"要求": "香水みたいにいい香り", "撮られていないもの": "香りを確かめる動作", "確定": "テロップ/ナレで補う"}],
}

BUILT = {
    "0801": {"status": "built",
             "prproj": "/Volumes/Extreme SSD/FERIEST/02_work/premiere/FERIEST_0801_ebi_v1.prproj",
             "sequence": "0801_ebi",
             "document_id": "3ea1839d-a639-48ba-acae-e0d506adfd39",
             "version": "v7",
             "actual": {"frames": 337, "duration_sec": 11.233, "shots": 10,
                        "cuts_per_min": 53.4, "shot_len_median_sec": 0.93,
                        "telops": 6, "shots_per_telop": 1.67},
             "role": "★修正の実演の出発点。ゼロから組む対象ではない"}
}

def db_counts():
    con = sqlite3.connect(p(BASE["source"]["asset_db"]))
    out = {}
    for prod, n_win, n_key in con.execute(
            "select product, count(*), count(distinct key) from asset_windows_v2 "
            "where product not like '%_dup_%' group by 1"):
        out[prod] = (n_win, n_key)
    con.close()
    return out

def main():
    check = "--check" in sys.argv
    counts = db_counts()
    tgt = TARGETS["tempo"]
    tol = TARGETS["tempo_tolerance"]
    os.makedirs(p("projects"), exist_ok=True)
    diffs = []

    for vid, cv in sorted(CONTE["videos"].items()):
        prod = cv["product"]
        slots = cv["slots"]
        # ★テロップ数はコンテのテロップ欄が埋まっているスロット数。カット指示の数ではない
        n_telop = sum(1 for s in slots if (s.get("telop") or "").strip())
        spt = tgt["shots_per_telop"]
        med = tgt["shot_len_median_sec"]
        shots = round(n_telop * spt)
        dur = round(shots * med, 2)
        lo_s = int(n_telop * spt * (1 - tol["shots_per_telop_pct"] / 100))
        hi_s = round(n_telop * spt * (1 + tol["shots_per_telop_pct"] / 100))

        n_win, n_key = counts.get(prod, (0, 0))
        doc = {
            "_note": "★.fork/gen_projects.py が生成。手で書き換えない。"
                     "実測で値が変わったら生成元（REFERENCE-TARGETS.json / conte.json）を直して再生成する",
            "_generated_by": ".fork/gen_projects.py",
            "video_id": vid,
            "product": prod,
            "media_dir": os.path.join(BASE["source"]["media_root"], MEDIA_DIR[vid]),
            "conte_slots": len(slots),
            "telops": n_telop,
            "assets": {"windows": n_win, "sources": n_key},
            "target": {
                "_derivation": "shots = telops × shots_per_telop(参考1.77) / "
                               "duration = shots × shot_len_median(参考0.80秒)。"
                               "★参考の骨格に合わせる reference-first。素材の都合で決めない",
                "shots": shots,
                "shots_band": [lo_s, hi_s],
                "duration_sec": dur,
                "shot_len_median_sec": med,
                "shot_len_min_sec": round(tol["shot_len_min_frames_floor"] / 30, 3),
                "shot_len_max_sec": round(tgt["shot_len_max_frames"] / 30, 3),
                "_band_note": "帯を外れたら理由を qc/tempo_report.json に書く。"
                              "『そのまま残す』を選ぶなら independent_approval が要る",
            },
            "client_notes": CLIENT_NOTES.get(vid, []),
            "_client_notes_note": "★字コンテの赤入れ原文。要約・言い換えをしない。これが確定内容",
            "no_material": NO_MATERIAL.get(vid, []),
            "_no_material_note": "★全数検索で不在を確定済み。『探せば見つかる』と誤認しない",
        }
        doc.update(BUILT.get(vid, {"status": "to_build",
                                   "role": "★ゼロから組み上げる対象"}))

        path = p("projects", vid + ".json")
        new = json.dumps(doc, ensure_ascii=False, indent=1) + "\n"
        if check:
            old = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
            if old != new:
                diffs.append(vid)
        else:
            open(path, "w", encoding="utf-8").write(new)
        print(f"{vid} {prod[:22]:24s} slots={len(slots):2d} telops={n_telop:2d} "
              f"→ shots={shots:2d} ({lo_s}-{hi_s}) dur={dur:5.2f}s  "
              f"windows={n_win:4d} sources={n_key:2d}  {doc['status']}")

    if check:
        if diffs:
            print("DRIFT:", ",".join(diffs)); return 1
        print("OK: projects/*.json は生成元と一致")
    return 0

if __name__ == "__main__":
    sys.exit(main())
