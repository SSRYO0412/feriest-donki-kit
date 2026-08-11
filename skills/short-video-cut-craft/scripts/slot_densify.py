#!/usr/bin/env python3
"""slot_densify.py — 絵変わり点を「文節頭」に置き直して参考の視覚切替密度・尺分布に寄せる。

★なぜ必要か（2026-07-30の実測で判明）
参考07の style_profile にあった cuts_per_min=35.2 は Premiere track0(A-roll)の30カットだけを
数えた値で、挿入トラック(track3の27クリップ)による視覚変化が丸ごと落ちていた。
全71クリップから算出した真の視覚切替は 39点/51.1s = 45.8/分、中央値1.20s、1.2秒未満が52%。
つまり設計目標が0.72倍に過小だった。18_R2が「絵変わりが少ない」と評価された構造的原因はこれ。

★なぜ等間隔で刻まないか
平均だけ合わせると1.5秒が並ぶ階段状になり、参考の「短短長」の不規則さが再現できない（Goodhart）。
参考の不規則さは発話の構造から出ている。だから絵変わり点は**fugashiの文節頭**にだけ置き、
間隔は結果として決まるようにする。数値を作りに行かない。

文節頭の定義: 自立語(名詞/動詞/形容詞/副詞/接続詞/感動詞/連体詞)で始まり、直前が付属語(助詞/助動詞/
接尾辞)または句読点であるトークン。行頭も文節頭。

使い方: python3 slot_densify.py <script.json> <style_profile.json> <out_draft.json> [--min-aroll 0.55] [--min-insert 1.15]
"""
import json, sys, unicodedata
import fugashi

JIRITSU = {"名詞", "動詞", "形容詞", "形状詞", "副詞", "接続詞", "感動詞", "連体詞", "代名詞"}
FUZOKU = {"助詞", "助動詞", "接尾辞"}
tagger = fugashi.Tagger()

def mora(kana):
    """カナのモーラ数。拗音(ャュョァィゥェォ)は前のモーラに吸収、長音/撥音/促音は1モーラ。"""
    if not kana: return 0
    small = "ャュョァィゥェォヮ"
    return sum(0 if ch in small else 1 for ch in unicodedata.normalize("NFKC", kana))

def bunsetsu_offsets(text):
    """(モーラ累積位置, 表層) のリスト。文節頭のみ返す。"""
    toks, acc, out, prev_pos = list(tagger(text)), 0, [], None
    for i, w in enumerate(toks):
        pos1 = w.feature.pos1
        kana = getattr(w.feature, "kana", None) or w.surface
        head = (i == 0) or (prev_pos in FUZOKU) or (prev_pos is None) \
               or (pos1 in JIRITSU and prev_pos not in JIRITSU)
        if head and pos1 in JIRITSU:
            out.append((acc, w.surface))
        acc += mora(kana)
        prev_pos = pos1
    return out, acc

def densify(row, min_gap):
    """行の尺予算を文節頭の比率で割り、min_gap以上の間隔になる点だけ残す。"""
    text = (row["音声"] or "").replace("→", "")
    heads, total = bunsetsu_offsets(text)
    dur = float(row["尺予算"])
    if total == 0 or not heads: return [0]
    pts, last = [0.0], 0.0
    for m, surf in heads[1:]:
        t = round(m / total * dur, 2)
        if t - last >= min_gap and dur - t >= min_gap:
            pts.append(t); last = t
    return pts

if __name__ == "__main__":
    sc = json.load(open(sys.argv[1], encoding="utf-8"))
    sp = json.load(open(sys.argv[2], encoding="utf-8"))
    out_p = sys.argv[3]
    A = float(sys.argv[sys.argv.index("--min-aroll")+1]) if "--min-aroll" in sys.argv else 0.55
    I = float(sys.argv[sys.argv.index("--min-insert")+1]) if "--min-insert" in sys.argv else 1.15
    target = sp["visual_switch"]["per_min"]
    dur = sum(float(r["尺予算"]) for r in sc["rows"])
    rows = []
    for r in sc["rows"]:
        # 締めロングは参考の締め文法（3.9s級の1ショット）なので割らない
        if "締め" in r["機能"]:
            pts = [0]
        else:
            is_ins = "挿入" in (r["視覚"] or "")
            pts = densify(r, I if is_ins else A)
        rows.append({**r, "絵変わり点": pts})
    n = sum(len(r["絵変わり点"]) for r in rows)
    segs = []
    for r in rows:
        b = sorted(set(list(map(float, r["絵変わり点"])) + [float(r["尺予算"])]))
        segs += [round(b[i+1]-b[i], 2) for i in range(len(b)-1)]
    import numpy as np
    s = np.array(segs)
    band = lambda lo, hi: int(((s >= lo) & (s < hi)).sum())
    print(f"スロット {n} / 目標 {round(dur*target/60,1)}（参考 {target}/分）= {n/dur*60:.1f}/分")
    print(f"中央値 {np.median(s):.2f}s（参考 {sp['visual_switch']['中央値秒']}） 最短 {s.min():.2f}s 最長 {s.max():.2f}s")
    print(f"分布 <0.8 {band(0,0.8)}({band(0,0.8)/len(s)*100:.0f}%) | 0.8-1.2 {band(0.8,1.2)}({band(0.8,1.2)/len(s)*100:.0f}%) "
          f"| 1.2-2.0 {band(1.2,2.0)}({band(1.2,2.0)/len(s)*100:.0f}%) | 2.0-3.0 {band(2.0,3.0)}({band(2.0,3.0)/len(s)*100:.0f}%) "
          f"| >=3.0 {band(3.0,99)}({band(3.0,99)/len(s)*100:.0f}%)")
    print(f"参考       <0.8 26% | 0.8-1.2 26% | 1.2-2.0 38% | 2.0-3.0 8% | >=3.0 3%")
    json.dump({**sc, "rows": rows}, open(out_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("→", out_p)
