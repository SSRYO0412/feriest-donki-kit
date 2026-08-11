#!/usr/bin/env python3
"""slot_assign.py — [S4] 割付ソルバ。正典 REF-DRIVEN-SELECTION §1/§4/§5 準拠。

★設計の大原則（2026-07-30に一度これを破って作り直した）
正典§1「衝突時の優先順位: 肝TOP3(軸2)=ハード / ユニバーサルゲート(軸3)=ハード /
軸1=制約内での最大化」。つまり**意味一致（軸1）はハードではない**。
意味の一致を優先して挿入を捨てると、地A-rollばかりで絵変わりしない設計になる。
実際に内容一致をハード化したところ挿入要求27スロット中17が「置かない」になり、
18_ACTY_R2で指摘された「絵変わり不足」をそのまま再生産した。

したがって:
 ・**台本の視覚列に「挿入」と書かれたスロットは埋めるのが既定**。「置かない」は最後の手段
 ・意味が少しズレても視覚変化を作る方を選ぶ（正典§5 軸1-1の合格は意味一致率≥80%。100%ではない）
 ・多様性・使い回し・再登場間隔は**減点**で扱う（ハードにすると候補が枯れる）
 ・ハードは1つだけ: 同一素材の同一区間の重複（正典§4①のゼロ重複）

使い方: python3 slot_assign.py <slot_candidates.json> <out.json>
"""
import json, sys, collections

PEN_SAME_CAT   = 25   # 直前スロットと同じ被写体カテゴリ（軸3の多様性）
PEN_REAPPEAR   = 12   # 同一素材が近い時間に再登場（1秒ごとに回復）
PEN_REUSE      = 8    # 同一素材の2回目以降（回数×）
REAPPEAR_WIN   = 8.0  # この秒数以内の再登場を減点対象にする

d = json.load(open(sys.argv[1], encoding="utf-8"))
slots = d["slots"]
TOT = sum(float(x["尺"]) for x in slots)
# ★挿入の総量は参考の占有率を予算にする（正典§5 2-x「出力÷参考」の思想）。
#   予算なしで埋めると占有44%（参考32%）まで膨らみ、挿入だらけで参考から離れる。
#   上限は参考占有率の1.15倍。ここに収まる範囲で、価値の高いスロットから埋める。
# 参考07の実測: 挿入占有32.0%（16.34s/51.1s）。18(75.1s)換算で24.0s。
# 1.15倍の余裕を付けると挿入だらけになり参考から離れたので、実測どおり1.0倍で持つ。
REF_OCC = 32.0
BUDGET = TOT * REF_OCC / 100
MAX_AROLL_RUN = 11.4      # 参考のA-roll連続 最大9.53s×1.2。project.jsonのthresholdsが正本
used_spans, use_count, last_use, spent = [], collections.Counter(), {}, 0.0
assign, prev_cat = {}, None

# ★どのスロットを埋めるかを先に決める（2026-07-30）。貪欲に前から埋めると予算が前半で尽き、
#   後半に26秒のA-roll連続ができた。参考は挿入帯を4本に分けて散らしている（A-roll連続 最大9.53s）。
#   よって「A-roll連続がMAX_AROLL_RUNを超えないための必須スロット」を先に確保し、
#   残予算を得点順に配る。
ins_slots = [x for x in slots if x["求める画"].startswith("挿入")]
must = set()
last_ins_end = 0.0
for x in ins_slots:
    # 0.7だと必須スロットに候補が無かった場合に上限を超える（実測11.70s>11.4s）。
    # 0.55にして刻みを細かくし、必須が空振りしても次で回収できるようにする。
    if x["t0"] - last_ins_end >= MAX_AROLL_RUN * 0.55:
        if any(c.get("rel") for c in x["candidates"]):
            must.add(x["slot"]); last_ins_end = x["t1"]
best_of = {x["slot"]: max([c.get("score") or 0 for c in x["candidates"]] or [0]) for x in ins_slots}
optional = sorted([x["slot"] for x in ins_slots if x["slot"] not in must],
                  key=lambda k: -best_of[k])
allow = set(must)
budget_left = BUDGET - sum(float(x["尺"]) for x in ins_slots if x["slot"] in must)
for k in optional:
    d2 = next(float(x["尺"]) for x in ins_slots if x["slot"] == k)
    if budget_left - d2 >= 0: allow.add(k); budget_left -= d2
print(f'挿入予算 {BUDGET:.1f}s / 必須スロット {len(must)}（A-roll連続{MAX_AROLL_RUN}s超の回避）/ 追加 {len(allow)-len(must)} = 計{len(allow)}')

for s in slots:                                  # ★時系列順に決める（前後関係で減点が決まるため）
    if not s["求める画"].startswith("挿入") or s["slot"] not in allow:
        assign[s["slot"]] = ({"win": "地(A-roll)"} if not s["求める画"].startswith("挿入")
                             else {"win": "★置かない（地A-rollのまま）",
                                   "理由": "挿入の尺予算（参考占有32%＝24.0s）に収めるため見送り"})
        prev_cat = "A-roll"
        continue
    cont = "継続" in s["求める画"] or "2段目" in s["求める画"]
    best, best_v = None, None
    for c in [c for c in s["candidates"] if c.get("rel")]:
        rel, t1 = c["rel"], c["t1"]
        stem = rel.rsplit("/", 1)[-1]
        # ★窓の「使い残し」を使う（2026-07-30追加）。窓の先頭だけを候補にしていたため、
        #   4.5秒の荷室窓を2.07秒使った時点で残り2.43秒が誰にも使われず、同カテゴリの
        #   別スロットが「置かない」に落ちていた。同一区間の重複は禁止だが、
        #   同じ窓の別の区間は別の画なので使える。使用済み区間の直後へ開始点をずらす。
        t0 = c["t0"]
        for _ in range(6):
            ov = [b for r, a, b in used_spans if r == rel and not (t0 + s["尺"] <= a or t0 >= b)]
            if not ov: break
            t0 = round(max(ov), 2)
        if t1 - t0 < s["尺"] - 0.25:              # ずらした結果、尺が足りなければ不可
            continue
        if prev_cat and not cont and c["cat"] == prev_cat:
            continue                             # ハード（軸3ゲート）
        v = c.get("score") or 0
        pens = []
        if stem in last_use:
            gap = s["t0"] - last_use[stem]
            if 0 <= gap < REAPPEAR_WIN:
                p = int(PEN_REAPPEAR * (1 - gap / REAPPEAR_WIN))
                v -= p; pens.append(f"再登場{gap:.1f}s-{p}")
        if use_count[stem]:
            v -= PEN_REUSE * use_count[stem]; pens.append(f"{use_count[stem]+1}回目-{PEN_REUSE*use_count[stem]}")
        if best_v is None or v > best_v:
            best, best_v, best_pens = {**c, "_in": t0}, v, pens
    if best is None:
        assign[s["slot"]] = {"win": "★置かない（地A-rollのまま）",
                             "理由": "候補なし（同一区間の重複／直前と同カテゴリ／挿入の尺予算超過）"}
        prev_cat = "A-roll"
        continue
    rel = best["rel"]; stem = rel.rsplit("/", 1)[-1]
    in_t = best["_in"]
    out_t = round(min(best["t1"], in_t + s["尺"]), 2)
    zan = round(s["尺"] - (out_t - in_t), 2)
    used_spans.append((rel, in_t, out_t))
    use_count[stem] += 1; last_use[stem] = s["t0"]; spent += out_t - in_t
    assign[s["slot"]] = {"win": best["win"], "rel": rel, "in": in_t, "out": out_t,
                         "cat": best["cat"], "shot": best["shot"], "verdict": best["verdict"],
                         "conditional": best.get("conditional"), "score": best["score"],
                         "実効点": best_v, "減点": best_pens, "why": best["why"],
                         "端数": zan if zan > 0.01 else None,
                         "意味一致": best["cat"] == s["求めるカテゴリ"]}
    prev_cat = best["cat"]

out = [{**s, "割付": assign[s["slot"]]} for s in slots]
ins = [s for s in out if s["求める画"].startswith("挿入")]
placed = [s for s in ins if s["割付"].get("rel")]
sec = sum(s["割付"]["out"] - s["割付"]["in"] for s in placed)
tot = sum(float(s["尺"]) for s in out)
match = sum(1 for s in placed if s["割付"]["意味一致"])
json.dump({"slots": out, "meta": {**d["meta"], "挿入要求": len(ins), "割付": len(placed),
           "置かない": len(ins) - len(placed), "挿入総尺": round(sec, 2),
           "挿入占有率%": round(sec / tot * 100, 1),
           "意味一致率%": round(match / max(1, len(placed)) * 100, 1)}},
          open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f'挿入要求 {len(ins)} → 割付 {len(placed)} / 置かない {len(ins)-len(placed)}')
print(f'挿入総尺 {sec:.1f}s = 占有{sec/tot*100:.1f}% / 意味一致率 {match}/{len(placed)} = {match/max(1,len(placed))*100:.0f}%（正典の合格は80%）')
print("使用素材 " + " ".join(f'{k.replace("IMG_","").replace(".MOV","")}×{v}' for k, v in sorted(use_count.items())))
