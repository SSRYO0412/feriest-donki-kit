#!/usr/bin/env python3
"""select_solver.py — [S4] 割付ソルバ（多点スタート探索）。正典 REF-DRIVEN-SELECTION §4/§8。

★なぜ貪欲ではだめか（2026-07-30の実績）
前から順に埋める貪欲＋制約のパッチ当てを7回繰り返したが、あるゲートを直すと別のゲートが落ちる
状態を抜けられなかった（隣接カテゴリ／A-roll連続／挿入本数の3つが互いに干渉する）。
これは系列全体の制約充足問題なので、局所ではなく**系列で解く**必要がある（正典§4 S4
「局所最適でなく系列最適」）。

制約（すべて参考の実測から。project.jsonのthresholdsが正本）
 H1 同一素材の同一区間の重複なし
 H2 隣接スロットの被写体カテゴリ相違（継続/2段目は例外）
 H3 A-roll連続 ≤ 参考の最大×1.2
 H4 挿入クリップ数が参考換算の0.8〜1.2倍
 H5 挿入総尺が参考換算の0.8〜1.2倍
 H6 ユニーク被写体カテゴリ ≥ 6/分
目的 意味一致率の最大化（同点なら素点合計）

使い方: python3 select_solver.py <slot_candidates.json> <style_profile.json> <out.json> [--tries 400]
"""
import json, sys, random, collections

cand = json.load(open(sys.argv[1], encoding="utf-8"))
sp = json.load(open(sys.argv[2], encoding="utf-8"))
out_p = sys.argv[3]
TRIES = int(sys.argv[sys.argv.index("--tries")+1]) if "--tries" in sys.argv else 400

slots = cand["slots"]
V = sp["visual_switch"]
TOT = sum(float(s["尺"]) for s in slots)
REF_CLIPS = V["挿入"]["クリップ数"] * TOT / V["duration"]
REF_SEC = TOT * float(str(V["挿入"]["占有率"]).rstrip("%")) / 100
MAX_RUN = 11.4          # 参考のA-roll連続 最大9.53s×1.2
MIN_CLUSTER_PM = 6.0
SAME_CAT_MIN_GAP = 3.0   # 同カテゴリの再登場が許される最小間隔（ゲートG-fと必ず一致させる）
ins_idx = [i for i, s in enumerate(slots) if s["求める画"].startswith("挿入")]


def build(order):
    """与えられた検討順で1解を構成する。順序が違えば別の解になる。"""
    used, taken, cats = [], {}, {}
    sec = 0.0
    for i in order:
        s = slots[i]
        cont = "継続" in s["求める画"] or "2段目" in s["求める画"]
        # 隣接カテゴリは「確定済みの前後」だけを見る（未確定は制約にしない）
        # 時間基準: 同カテゴリが SAME_CAT_MIN_GAP 秒以内に再登場すると同じ画に見える
        nb = {cats[j] for j in cats
              if abs(slots[j]["t0"] - s["t0"]) < SAME_CAT_MIN_GAP + float(s["尺"])}
        pool = []
        for c in s["candidates"]:
            if not c.get("rel"): continue
            if not cont and c["cat"] in nb: continue
            t0 = c["t0"]
            for _ in range(6):
                ov = [b for r, a, b in used if r == c["rel"] and not (t0 + s["尺"] <= a or t0 >= b)]
                if not ov: break
                t0 = round(max(ov), 2)
            if c["t1"] - t0 < s["尺"] - 0.25: continue
            v = (c.get("score") or 0) + (30 if c["cat"] == s["求めるカテゴリ"] else 0)
            pool.append((v, t0, c))
        if not pool: continue
        if sec >= REF_SEC * 1.2 or len(taken) + 1 > REF_CLIPS * 1.2: continue
        v, t0, c = max(pool, key=lambda x: x[0])
        o = round(min(c["t1"], t0 + s["尺"]), 2)
        used.append((c["rel"], t0, o)); taken[i] = (c, t0, o); cats[i] = c["cat"]
        sec += o - t0
    return taken


def evaluate(taken):
    """制約違反数（少ないほど良い）と目的値を返す。"""
    viol = 0
    # H2 隣接
    ts = sorted(taken)
    for a in range(len(ts)):
        for b in range(a+1, len(ts)):
            ia, ib = ts[a], ts[b]
            if slots[ib]["t0"] - slots[ia]["t1"] >= SAME_CAT_MIN_GAP: break
            cont = "継続" in slots[ib]["求める画"] or "2段目" in slots[ib]["求める画"]
            if not cont and taken[ia][0]["cat"] == taken[ib][0]["cat"]: viol += 1
    # H3 A-roll連続
    last = 0.0; mx = 0.0
    for i in sorted(taken):
        mx = max(mx, slots[i]["t0"] - last); last = slots[i]["t1"]
    mx = max(mx, TOT - last)
    if mx > MAX_RUN: viol += 1
    # H4/H5
    n = len(taken); sec = sum(o - t for _, t, o in taken.values())
    if not (REF_CLIPS*0.8 <= n <= REF_CLIPS*1.2): viol += 1
    if not (REF_SEC*0.8 <= sec <= REF_SEC*1.2): viol += 1
    # H6
    cl = len({c["cat"] for c, _, _ in taken.values()}) + 1
    if cl / (TOT/60) < MIN_CLUSTER_PM: viol += 1
    match = sum(1 for i, (c, _, _) in taken.items() if c["cat"] == slots[i]["求めるカテゴリ"])
    return viol, match, sec, mx, cl, n


rnd = random.Random(20260730)
best = None
for t in range(TRIES):
    order = list(ins_idx)
    if t == 0: pass                                   # 時系列順
    elif t == 1: order.sort(key=lambda i: -max([c.get("score") or 0 for c in slots[i]["candidates"]] or [0]))
    else: rnd.shuffle(order)
    taken = build(order)
    ev = evaluate(taken)
    key = (-ev[0], ev[1], ev[2])                      # 違反が少ない→意味一致が多い→挿入が長い
    if best is None or key > best[0]: best = (key, taken, ev)

key, taken, ev = best
viol, match, sec, mx, cl, n = ev
assign = {}
for i, s in enumerate(slots):
    if i in taken:
        c, t0, o = taken[i]
        assign[s["slot"]] = {"win": c["win"], "rel": c["rel"], "in": t0, "out": o, "cat": c["cat"],
                             "shot": c["shot"], "verdict": c["verdict"], "conditional": c.get("conditional"),
                             "score": c["score"], "why": c["why"],
                             "端数": round(s["尺"] - (o - t0), 2) if s["尺"] - (o - t0) > 0.01 else None,
                             "意味一致": c["cat"] == s["求めるカテゴリ"]}
    elif s["求める画"].startswith("挿入"):
        assign[s["slot"]] = {"win": "★置かない（地A-rollのまま）",
                             "理由": "参考換算の挿入量（クリップ数・総尺）に収めるため、または候補が制約で不可"}
    else:
        assign[s["slot"]] = {"win": "地(A-roll)"}

res = [{**s, "割付": assign[s["slot"]]} for s in slots]
json.dump({"slots": res, "meta": {**cand["meta"], "探索回数": TRIES, "制約違反": viol,
           "挿入": n, "参考換算クリップ": round(REF_CLIPS, 1), "挿入総尺": round(sec, 2),
           "参考換算秒": round(REF_SEC, 1), "挿入占有率%": round(sec/TOT*100, 1),
           "意味一致率%": round(match/max(1, n)*100, 1), "最大A-roll連続s": round(mx, 2),
           "ユニーククラスタ_毎分": round(cl/(TOT/60), 1)}},
          open(out_p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f'探索{TRIES}回 → 制約違反 {viol}件')
print(f'挿入 {n}本（参考換算{REF_CLIPS:.1f}・帯{REF_CLIPS*0.8:.1f}〜{REF_CLIPS*1.2:.1f}）/ 総尺{sec:.1f}s（参考換算{REF_SEC:.1f}）/ 占有{sec/TOT*100:.1f}%')
print(f'意味一致 {match}/{n} = {match/max(1,n)*100:.0f}% / 最大A-roll連続 {mx:.2f}s（上限{MAX_RUN}）/ クラスタ {cl/(TOT/60):.1f}/分（下限{MIN_CLUSTER_PM}）')
