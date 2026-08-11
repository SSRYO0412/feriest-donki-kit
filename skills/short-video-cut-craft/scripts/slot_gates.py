#!/usr/bin/env python3
"""slot_gates.py — [S5] 割付の機械ゲート。設計値から全数列挙して数える（画像解析に頼らない）。

★基準は全て0件（gates.template.json の universal_thresholds と一致させる）
  G-a 0.40秒未満のショット
  G-b 同一素材の同一区間の二重使用（重なりが1フレームでもあれば違反）
  G-c 挿入と挿入の隙間が20F(0.333s)未満（挿入が実質つながって見える）
  G-d BANNED / NO-GO 窓の使用
  G-e 供給尺超過（挿入総尺 > 使える窓の総尺）
  G-f 隣接スロットの被写体カテゴリ重複（継続/2段目を除く）
  警告(WARN・0件でなくてよいが人が見る): CONDITIONAL窓の条件・挿入占有率の参考差・供給不足スロット

使い方: python3 slot_gates.py <slot_assign.json> <style_profile.json> <db> <out.json>
"""
import json, sqlite3, sys, collections

A = json.load(open(sys.argv[1], encoding="utf-8"))
sp = json.load(open(sys.argv[2], encoding="utf-8"))
con = sqlite3.connect(sys.argv[3]); con.row_factory = sqlite3.Row
slots = A["slots"]
V = sp["visual_switch"]
FAIL, WARN = [], []

placed = [s for s in slots if s["割付"].get("rel")]
tot = sum(float(s["尺"]) for s in slots)

# G-a
for s in slots:
    if float(s["尺"]) < 0.40: FAIL.append(f'G-a 0.40秒未満のショット {s["slot"]} {s["尺"]}s')
# G-b
for i, a in enumerate(placed):
    for b in placed[i+1:]:
        if a["割付"]["rel"] == b["割付"]["rel"] and not (a["割付"]["out"] <= b["割付"]["in"] or a["割付"]["in"] >= b["割付"]["out"]):
            FAIL.append(f'G-b 同一区間の二重使用 {a["slot"]}({a["割付"]["in"]}-{a["割付"]["out"]}) × {b["slot"]}({b["割付"]["in"]}-{b["割付"]["out"]}) {a["割付"]["rel"].rsplit("/",1)[-1]}')
# G-c
ps = sorted(placed, key=lambda s: s["t0"])
for i in range(len(ps)-1):
    gap = ps[i+1]["t0"] - ps[i]["t1"]
    if 0 < gap < 0.333:
        FAIL.append(f'G-c 挿入間の隙間が20F未満 {ps[i]["slot"]}→{ps[i+1]["slot"]} {gap:.3f}s')
# G-d / G-e
ok_secs = 0.0
for r in con.execute("""SELECT rel,t0,t1,verdict FROM asset_windows_v2 WHERE superseded=0
        AND confirmed_by IS NOT NULL AND clip_kind='broll素材'"""):
    if r["verdict"] in ("GO", "CONDITIONAL"): ok_secs += float(r["t1"]) - float(r["t0"])
    else:
        for s in placed:
            if s["割付"]["rel"] == r["rel"] and not (s["割付"]["out"] <= float(r["t0"]) or s["割付"]["in"] >= float(r["t1"])):
                FAIL.append(f'G-d {r["verdict"]}窓を使用 {s["slot"]} {r["rel"].rsplit("/",1)[-1]} {r["t0"]}-{r["t1"]}')
ins_sec = sum(s["割付"]["out"] - s["割付"]["in"] for s in placed)
if ins_sec > ok_secs: FAIL.append(f'G-e 供給尺超過 挿入{ins_sec:.1f}s > 使える窓{ok_secs:.1f}s')
# G-f 同カテゴリの再登場が3.0秒以内（=同じ画に見える）。ソルバと同じ時間基準。
SAME_CAT_MIN_GAP = 3.0
ps = sorted(placed, key=lambda x: x["t0"])
for a in range(len(ps)):
    for b in range(a+1, len(ps)):
        if ps[b]["t0"] - ps[a]["t1"] >= SAME_CAT_MIN_GAP: break
        cont = "継続" in ps[b]["求める画"] or "2段目" in ps[b]["求める画"]
        if not cont and ps[a]["割付"]["cat"] == ps[b]["割付"]["cat"]:
            FAIL.append(f'G-f 同カテゴリが{ps[b]["t0"]-ps[a]["t1"]:.2f}秒後に再登場 {ps[a]["slot"]}→{ps[b]["slot"]} {ps[a]["割付"]["cat"]}') or prev
# G-g 軸3-B3 絵変わり保証（正典§5 軸3の帯指標。ここを検査していなかったため
#     「地A-rollばかりで絵変わりしない」設計がゲートを素通りしていた）
vis, prev = [], None
for s2 in slots:
    cat = s2["割付"].get("cat") or "A-roll"
    if cat != prev: vis.append(s2["t0"])          # 画が変わる瞬間
    prev = cat
gaps = [vis[i+1]-vis[i] for i in range(len(vis)-1)] + [tot - vis[-1]]
# ★閾値は案件project.jsonのthresholdsが正本（参考実測で較正）。一般帯4.0sは参考と矛盾していた。
MAXRUN = 11.4
runs, last_end = [], 0.0
for s2 in slots:
    if s2["割付"].get("rel"):
        runs.append(s2["t0"] - last_end); last_end = s2["t1"]
runs.append(tot - last_end)
if max(runs) > MAXRUN:
    FAIL.append(f'G-g A-roll連続が{MAXRUN}秒超 最大{max(runs):.2f}s（参考の最大9.53s×1.2）')
clusters = len({s2["割付"].get("cat") for s2 in slots if s2["割付"].get("cat")}) + 1
per_min = clusters / (tot/60)
if per_min < 6.0:
    FAIL.append(f'G-g ユニーククラスタ{per_min:.1f}/分 < 6.0（画の種類が足りない）')
# G-h 挿入量を参考比で見る（正典§5の「出力÷参考」）。参考07は挿入8クリップ・占有32.0%。
#   18(75.1s)換算では 8×75.1/51.1 = 11.8クリップ・24.0秒が等価。
ins_req = [s2 for s2 in slots if s2["求める画"].startswith("挿入")]
ref_clips_eq = V["挿入"]["クリップ数"] * tot / V["duration"]
ratio = len(placed) / ref_clips_eq
if not (0.8 <= ratio <= 1.2):
    FAIL.append(f'G-h 挿入クリップ数が参考比{ratio:.2f}倍（{len(placed)}本 vs 参考換算{ref_clips_eq:.1f}本）帯0.8〜1.2')
occ_ratio = ins_sec / (tot * float(str(V["挿入"]["占有率"]).rstrip("%")) / 100)
if not (0.8 <= occ_ratio <= 1.2):
    FAIL.append(f'G-h 挿入占有が参考比{occ_ratio:.2f}倍（{ins_sec:.1f}s vs 参考換算{tot*32/100:.1f}s）帯0.8〜1.2')
fill = len(placed) / max(1, len(ins_req))

# WARN
for s in placed:
    if s["割付"].get("conditional"):
        WARN.append(f'CONDITIONAL窓の条件を守る必要 {s["slot"]} {s["割付"]["win"]} → {s["割付"]["conditional"]}')
occ = ins_sec / tot * 100
ref_occ = float(str(V["挿入"]["占有率"]).rstrip("%"))
if abs(occ - ref_occ) > 8: WARN.append(f'挿入占有率 {occ:.0f}%（参考{ref_occ:.0f}%）差{occ-ref_occ:+.0f}pt')
for s in slots:
    if "置かない" in s["割付"].get("win", ""): WARN.append(f'置かない {s["slot"]} 要求={s["求めるカテゴリ"]} 機能={s["機能"]}')

rep = {"FAIL": FAIL, "WARN": WARN, "指標": {
    "スロット": len(slots), "設計密度/分": round(len(slots)/tot*60, 1), "参考密度/分": V["per_min"],
    "挿入クリップ": len(placed), "参考挿入クリップ": V["挿入"]["クリップ数"],
    "挿入総尺": round(ins_sec, 1), "参考挿入総尺": V["挿入"]["占有秒"],
    "挿入占有率%": round(occ, 1), "参考占有率%": ref_occ,
    "挿入1本平均": round(ins_sec/max(1, len(placed)), 2), "参考挿入1本中央": V["挿入"]["中央"],
    "使える窓の総尺": round(ok_secs, 1),
    "最大A-roll連続s": round(max(runs), 2), "ユニーククラスタ_毎分": round(per_min, 1),
    "挿入充填率%": round(fill*100, 1), "意味一致率%": A["meta"].get("意味一致率%")}}
json.dump(rep, open(sys.argv[4], "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"FAIL {len(FAIL)}件 / WARN {len(WARN)}件")
for f in FAIL: print("  ✖", f)
for w in WARN[:6]: print("  ⚠", w)
if len(WARN) > 6: print(f"  …WARN 残り{len(WARN)-6}件は {sys.argv[4]}")
print("指標:", json.dumps(rep["指標"], ensure_ascii=False))
