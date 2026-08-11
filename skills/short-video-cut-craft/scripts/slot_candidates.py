#!/usr/bin/env python3
"""slot_candidates.py — [S3] スロット譜 × asset_windows_v2 → 各スロット3〜5候補＋「置かない」。

段階フィルタ（REF-DRIVEN S3）:
 ①ハード: confirmed_by NOT NULL / verdict∈(GO,CONDITIONAL) / clip_kind=broll素材 /
          窓尺 >= スロット尺+のりしろ0.3s / 同一素材同一区間の二重使用禁止(既割当と重ならない)
 ②意味  : 求めるカテゴリ一致（不一致は大減点だが候補に残す＝人が判断できるように）
 ③形式  : shot_size一致で加点（軸2）
 ④多様性: 前スロット採用カテゴリと相違（軸3を候補段階で先付け）
 ⑤スコア: 内容45/寄引15/新鮮15/尺10/画質5 − NG100 ＋参照適合(尺帯+10/shot+5)
使い方: python3 slot_candidates.py <slot_score.json> <db> <out.json> [--max-use 2] [--gap 15]
"""
import json, sqlite3, sys, os, collections

slots = json.load(open(sys.argv[1], encoding="utf-8"))["slots"]
db, out_p = sys.argv[2], sys.argv[3]
MAXUSE = int(sys.argv[sys.argv.index("--max-use")+1]) if "--max-use" in sys.argv else 3
GAP = float(sys.argv[sys.argv.index("--gap")+1]) if "--gap" in sys.argv else 9.0
# ★2026-07-30 Codex敵対レビューで判明した設計欠陥の修正:
#  ①内容不一致がハード除外でなかった。内容一致0でも「尺充足10+尺帯10+GO5=25点」で生き残り、
#    S03「車種提示」に後席の窓が候補として並んだ。スコアが「使える画」ではなく「尺が合う画」を
#    上げていた＝供給が細い条件下で最悪の挙動。→ 内容一致をハード条件に昇格。
#    候補が0件になるなら、間違った画を出すのではなく0件のまま供給不足として顕在化させる。
#  ②再登場ギャップ15sは75秒の動画では過剰。9sへ緩和（別部位/別クロップは元々別窓）。
#  ③「直前と同カテゴリ禁止」を継続/2段目スロットにも掛けていた。2段目は同じ被写体の続きなので
#    同カテゴリが正しい。→ 継続スロットでは無効化。
#  ④同一素材の使用上限を素材単位2回→3回（窓が重ならない限り別の画）。

con = sqlite3.connect(db); con.row_factory = sqlite3.Row
raw = [dict(r) for r in con.execute("""SELECT * FROM asset_windows_v2
    WHERE superseded=0 AND confirmed_by IS NOT NULL AND clip_kind='broll素材'
      AND verdict IN ('GO','CONDITIONAL') ORDER BY rel, t0""")]

# ★2026-07-30: 窓は「分析の単位」であって「使用の単位」ではない。素材内で連続する同カテゴリの窓は
#   ひと続きのショットなので結合して1つの候補にできる。これを実装するまで、荷室7窓(計9.0s)を持って
#   いながら2.5秒スロットの候補が0件になっていた（1窓の中央値が1.29秒だったため尺不足で全滅）。
#   結合の可否は「同一素材・同カテゴリ・時間が隣接(隙間<0.05s)」で判定し、
#   verdictはメンバーに1つでもCONDITIONALがあればCONDITIONAL（条件は連結して引き継ぐ）。
def merge_runs(ws):
    out, run = [], []
    def flush(run):
        if not run: return
        if len(run) == 1: out.append({**run[0], "merged_from": 1}); return
        conds = [w["conditional_terms"] for w in run if w.get("conditional_terms")]
        shots = collections.Counter(w["shot_size"] for w in run)
        out.append({**run[0], "t1": run[-1]["t1"],
                    "verdict": "CONDITIONAL" if any(w["verdict"] == "CONDITIONAL" for w in run) else "GO",
                    "conditional_terms": " / ".join(dict.fromkeys(conds)) or None,
                    "shot_size": shots.most_common(1)[0][0],
                    "shot_mixed": len(shots) > 1, "merged_from": len(run)})
        for w in run: out.append({**w, "merged_from": 1})   # 単窓も候補に残す
    for w in ws:
        if run and w["rel"] == run[-1]["rel"] and w.get("被写体カテゴリ") == run[-1].get("被写体カテゴリ") \
           and abs(float(w["t0"]) - float(run[-1]["t1"])) < 0.05:
            run.append(w)
        else:
            flush(run); run = [w]
    flush(run)
    return out

wins = merge_runs(raw)
nm = sum(1 for w in wins if w["merged_from"] > 1)
print(f"候補プール: 単窓{len(raw)} → 結合後{len(wins)}（うち結合区間{nm}本）")

# ★2026-07-30 ユーザー判断で基準を緩和: 「斜視図（正面も斜めからでも）大丈夫」。
#   厳密な外観-正面の窓は2つともBANNEDで実質ゼロだが、正面寄り/側面でも車種提示は成立する。
#   ただし緩めるのは「近縁カテゴリ」だけで、非近縁（車種提示に後席を出す等）はハード除外を維持する。
#   減点幅は「代替としての遠さ」。同一カテゴリ=0、近い=5、やや遠い=12、隣接空間=20。
# ★近縁代替は「斜視図（正面を斜めから）」に限る（2026-07-30）。
#   ユーザー指摘は「正面も斜めからでも大丈夫」＝正面⇄正面寄りの許可であって、
#   リアや別部位への置き換えの許可ではない。最初に広く取ったら次の取り違えが出た:
#     ・「ホンダのアクティです」と車種を名乗る瞬間に外観-リア（後ろ姿）
#     ・「後部座席の汚れが目立つ」に内装-全景
#     ・「荷物がいっぱい入る」に後席
#   訴求している対象そのものが映っていないと、正直訴求が成立しない。よって代替は下表だけ。
#   足りなければ「置かない」でよい（ユーザー判断: 走行距離の画も無ければ無しでOK）。
NEAR = {
    "外観-正面":     {"外観-正面寄り": 3},
    "外観-正面寄り": {"外観-正面": 3},
}
def cat_penalty(want, got):
    """None=代替不可(ハード除外) / 0=一致 / 正数=近縁だが減点"""
    if not want or want == got: return 0
    return NEAR.get(want, {}).get(got)

# ★2026-07-30 ユーザー指摘で基準を緩和: 斜視図(正面を斜めから)は正面の代替として成立する。
#   「求めるカテゴリと完全一致」だけを通すと、外観-正面の窓がBANNEDのみという理由でS03が
#   丸ごと空になるが、実際には正面寄り(斜め)で訴求は成立する。近縁カテゴリは通し、加点だけ下げる。
KIN = {
    "外観-正面":   {"外観-正面寄り": 30, "外観-側面": 20},
    "外観-正面寄り": {"外観-正面": 30, "外観-側面": 22},
    "外観-側面":   {"外観-正面寄り": 22, "外観-リア": 20},
    "外観-リア":   {"外観-側面": 20},
    "内装-運転席":  {"内装-全景": 28},
    "内装-全景":   {"内装-運転席": 28},
    "後席":      {"内装-全景": 20},
}

def cat_fit(want, got):
    """一致45 / 近縁は上表の点 / それ以外は None(=ハード除外)"""
    if not want: return 8, "カテゴリ指定なし8"
    if want == got: return 45, "内容一致45"
    k = KIN.get(want, {}).get(got)
    if k: return k, f"近縁カテゴリ{k}(要求={want}/窓={got}・斜視図等で成立)"
    return None, f"内容不一致(要求={want}/窓={got})"


def score(w, s):
    sc, why = 0, []
    pen = cat_penalty(s["求めるカテゴリ"], w.get("被写体カテゴリ"))
    if pen is None:          # 代替不可（ハード除外側で弾かれるが、スコアも0にしておく）
        why.append(f'内容 代替不可(要求={s["求めるカテゴリ"]}/窓={w.get("被写体カテゴリ")})')
    else:
        sc += 45 - pen
        why.append("内容一致45" if pen == 0
                   else f'近縁代替{45-pen}(要求={s["求めるカテゴリ"]}/窓={w.get("被写体カテゴリ")})')
    if s["求めるshot_size"] and w["shot_size"] == s["求めるshot_size"]:
        sc += 15; why.append("寄引一致15")
    elif s["求めるshot_size"]:
        why.append(f'寄引不一致(窓={w["shot_size"]})')
    else:
        sc += 8; why.append("寄引指定なし8")
    wd = float(w["t1"]) - float(w["t0"]); need = s["尺"] + 0.3
    if wd >= need: sc += 10; why.append(f"尺充足10({wd:.1f}s>={need:.1f}s)")
    if s["尺帯"][0] <= wd <= s["尺帯"][1] * 3: sc += 10; why.append("尺帯適合+10")
    if w["verdict"] == "GO": sc += 5; why.append("GO5")
    else: why.append(f'CONDITIONAL(条件:{(w.get("conditional_terms") or "")[:28]})')
    if s["求めるshot_size"] and w["shot_size"] == s["求めるshot_size"]: sc += 5; why.append("shot参照適合+5")
    return sc, " / ".join(why)

use_count = collections.Counter(); last_use = {}; assigned = []
res = []
prev_cat = None
for s in slots:
    if not s["求める画"].startswith("挿入"):
        res.append({**s, "candidates": [{"win": "地(A-roll)", "score": None,
                     "why": "この行は地（A-roll素見え）。挿入は要求しない"}], "選定": "地(A-roll)"})
        prev_cat = "A-roll"; continue
    cands = []
    for w in wins:
        stem = os.path.basename(w["rel"])
        wd = float(w["t1"]) - float(w["t0"])
        hard = []
        # ★のりしろ+0.3秒は厳しすぎた（2026-07-30）。2.07秒のスロットに対し2.00秒の窓が
        #   「尺不足」で全滅し、車種提示に使える唯一の正面寄り窓(IMG_6231 0.5-2.5)が捨てられていた。
        #   0.25秒までの不足は隣接する地カット(最短0.7秒)に吸収させれば成立するので許容し、端数を記録する。
        short = s["尺"] - wd
        if short > 0.25: hard.append(f"窓尺不足({wd:.2f}<{s['尺']:.2f})")
        # 使用回数・再登場間隔もハードにしない（正典①に無い）。割付側の減点で扱う。
        # ハードに残すのは「同一素材の同一区間の重複」だけ（これは正典①のゼロ重複）。
        for (r2, a2, b2) in assigned:      # 同一素材同一区間の二重使用禁止
            if r2 == w["rel"] and not (float(w["t1"]) <= a2 or float(w["t0"]) >= b2):
                hard.append(f"既割当窓と重複({a2:.1f}-{b2:.1f})")
        cont = "継続" in s["求める画"] or "2段目" in s["求める画"]
        if prev_cat and not cont and w.get("被写体カテゴリ") == prev_cat:
            pass   # ハードにしない。同カテゴリ連続は割付側で減点し、ゲート(同一sim_cluster連続)で検査する
        # ★内容不一致をハード除外にしてはならない（正典§1: 軸1は制約内での最大化・ハードではない）。
        #   2026-07-30に私がこれをハード化した結果、挿入要求27スロット中17が「置かない」になり、
        #   地A-rollばかりで絵変わりしない出力設計になった＝18_R2で指摘された失敗の再生産。
        #   意味が少しズレても視覚変化を作るのが参考に寄せる道。不一致はスコアで下げるだけにする。
        sc, why = score(w, s)
        cands.append({"win": f'{stem} {w["t0"]}-{w["t1"]}', "rel": w["rel"],
                      "t0": float(w["t0"]), "t1": float(w["t1"]),
                      "cat": w.get("被写体カテゴリ"), "shot": w["shot_size"],
                      "verdict": w["verdict"], "conditional": w.get("conditional_terms"),
                      "score": sc if not hard else None, "hard": hard, "why": why})
    ok = sorted([c for c in cands if not c["hard"]], key=lambda x: -x["score"])[:4]
    ok.append({"win": "★置かない（地A-rollのまま）", "score": 0,
               "why": "顔見せ/実演区間や、置くと重複感が出る場合は置かない方が正の利得"})
    ng_n = len(cands) - len([c for c in cands if not c["hard"]])
    res.append({**s, "candidates": ok, "除外数": ng_n, "選定": None})
    real = len(ok) - 1
    if real == 0:
        print(f'  ✖ {s["slot"]:8s} 候補0件 要求={s["求めるカテゴリ"]:12s} → 置かない/A-roll代替が確定')
    elif real < 3:
        print(f'  ⚠ {s["slot"]:8s} 候補{real}件 要求={s["求めるカテゴリ"]:12s} → 供給不足')
json.dump({"slots": res, "meta": {"pool": len(wins), "max_use": MAXUSE, "gap": GAP}},
          open(out_p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
ins = [r for r in res if r["求める画"].startswith("挿入")]
print(f'挿入スロット {len(ins)} / 候補平均 {sum(len(r["candidates"])-1 for r in ins)/max(1,len(ins)):.1f}件')
print(f"→ {out_p}")
