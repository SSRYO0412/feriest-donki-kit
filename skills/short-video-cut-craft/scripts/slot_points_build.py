#!/usr/bin/env python3
"""slot_points_build.py — [S1] 台本の各行に絵変わり点を確定的に打つ（参考の視覚文法を規則化）。

★参考07の実測（full_props.json+audio_full.jsonから機械算出・2026-07-30）
  視覚切替 29点/51.1s = 34.1/分（テロップ33個は絵変わりではないので除外、
  挿入で隠れている間のA-rollカット9本も見えないので除外）
  中央1.55s / 最短0.59 / 最長3.95 / 分布 <0.8 14% 0.8-1.2 21% 1.2-2.0 31% 2.0-3.0 24% >=3.0 10%
  挿入は8クリップ・1本1.43〜2.85s(中央2.07)・全て別素材・音声level=0でミュート・占有32%

★規則（この順に適用。数値は上の実測から来ている。当て込みで動かさない）
  R-a 挿入行は「2.0秒級の挿入1本＋残りは地」。細切れにすると参考の挿入文法から外れる
  R-b 07が明記する insert_style「2段連続」は最大緊張の行にだけ適用（2.1秒×2）
  R-c フック行(0-3秒)は参考でカットが最も詰まる箇所。0.7秒級の短尺を2つ置いて分布の短い裾を作る
  R-d 締めロングは割らない（参考の締めは3.95秒の1ショット）
  R-e 地(A-roll)として残る区間は fugashi の文節頭で刻む。最小間隔1.0秒。
      参考のA-roll可視区間は34.7秒で21カット=1ショット1.65秒級なので、これで密度が合う。
      等間隔で刻むと1.65秒が並ぶ階段状になり参考の不規則さが出ない（Goodhart）ので、
      間隔は発話の文節構造から決まるようにして、こちらから数値を作りに行かない。
  R-f それでも参考の最長3.95秒を超える区間が残ったら1.7秒目安で等分

使い方: python3 slot_points_build.py <script.json> <style_profile.json> [--write]
"""
import json, sys, numpy as np, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slot_densify import bunsetsu_offsets

sc = json.load(open(sys.argv[1], encoding="utf-8"))
sp = json.load(open(sys.argv[2], encoding="utf-8"))
V = sp["visual_switch"]
REF_MAX = float(V["最長"])
INS_LEN = float(V["挿入"]["中央"])          # 2.07
MIN_SEG = float(V["最短"]) * 0.85           # 0.50 認識下限（参考最短の85%まで許容）

for r in sc["rows"]:
    dur = float(r["尺予算"]); vis = r["視覚"] or ""; fn = r["機能"]
    if "締め" in fn:                                            # R-d
        pts = [0.0]
    elif "フック" in fn and float(r["開始秒"]) < 3.0:            # R-c
        pts = [0.0, 0.7, 1.4] if dur >= 2.4 else [0.0, 0.7]
        pts = [p for p in pts if dur - p >= MIN_SEG]
    elif "挿入" in vis:
        if "★" in fn or "最大緊張" in fn:                        # R-b 2段連続
            pts = [0.0, round(INS_LEN, 2), round(INS_LEN * 2, 2)]
        else:                                                    # R-a
            pts = [0.0] + ([round(INS_LEN, 2)] if dur - INS_LEN >= MIN_SEG else [])
    else:
        pts = [0.0]
    # R-e 地として残る区間を文節頭で刻む（挿入区間そのものは割らない）
    ins_end = pts[1] if ("挿入" in vis and len(pts) > 1) else (pts[-1] if "挿入" in vis else 0.0)
    heads, total = bunsetsu_offsets((r["音声"] or "").replace("→", ""))
    out = list(pts)
    if total:
        last = max(pts)
        for m, _ in heads[1:]:
            t = round(m / total * dur, 2)
            if t <= ins_end + 1e-6: continue          # 挿入が乗っている区間は割らない
            if t - last >= 1.0 and dur - t >= 1.0:
                out.append(t); last = t
    # R-f 参考の最長を超える区間だけ割る
    b = sorted(set(out)) + [dur]
    for i in range(len(b) - 1):
        seg = b[i+1] - b[i]
        if seg > REF_MAX:
            n = max(1, int(round(seg / 1.7)) - 1)
            for k in range(1, n + 1):
                t = round(b[i] + seg * k / (n + 1), 2)
                if t - b[i] >= 0.7 and b[i+1] - t >= 0.7: out.append(t)
    r["絵変わり点"] = sorted(set(round(x, 2) for x in out))

segs = []
for r in sc["rows"]:
    b = sorted(set([float(x) for x in r["絵変わり点"]] + [float(r["尺予算"])]))
    segs += [round(b[i+1]-b[i], 2) for i in range(len(b)-1)]
s = np.array(segs); tot = sum(float(r["尺予算"]) for r in sc["rows"])
band = lambda lo, hi: ((s >= lo) & (s < hi)).sum() / len(s) * 100
print(f"スロット {len(s)} / 密度 {len(s)/tot*60:.1f}/分 = 参考{V['per_min']}の{len(s)/tot*60/V['per_min']:.2f}倍")
print(f"中央 {np.median(s):.2f}s(参考{V['中央値秒']}) 最短 {s.min():.2f}(参考{V['最短']}) 最長 {s.max():.2f}(参考{V['最長']})")
print(f"分布 <0.8 {band(0,.8):.0f}%(14) | 0.8-1.2 {band(.8,1.2):.0f}%(21) | 1.2-2.0 {band(1.2,2):.0f}%(31) "
      f"| 2.0-3.0 {band(2,3):.0f}%(24) | >=3.0 {band(3,99):.0f}%(10)")
if "--write" in sys.argv:
    json.dump(sc, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("→ 書き込み:", sys.argv[1])
