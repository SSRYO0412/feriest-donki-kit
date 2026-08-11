#!/usr/bin/env python3
"""slot_score_build.py — [S1] 台本(script.json)＋参考(style_profile)→スロット譜。

★核心: 視覚スロットは「行」ではなく「絵変わり点」ごとに切る。
台本の1行が7秒でも絵変わり点が3つあれば視覚スロットは3つで、これが絵変わり密度の需要そのもの。
18_ACTY_R2の「絵変わりが少ない」は、行=1スロットで設計して行内の絵変わりを作らなかったのが原因。

出力: slot_score.json（各スロットに 求める画・尺帯・カテゴリ差要求・パンチイン・SE・情緒）
使い方: python3 slot_score_build.py <script.json> <style_profile.json> <out.json>
"""
import json, sys, re

sc = json.load(open(sys.argv[1], encoding="utf-8"))
sp = json.load(open(sys.argv[2], encoding="utf-8"))
band = sp["grammar"]["cut_len"]
pi = sp["grammar"]["punch_in"]

def parse_pts(v):
    if isinstance(v, list): return [float(x) for x in v]
    return [float(x) for x in re.findall(r'[\d.]+', str(v or "0"))] or [0.0]

def want_shot(text):
    t = text or ""
    if any(k in t for k in ("寄り", "ステッカー", "メーター", "POP", "ロゴ", "キー")): return "close"
    if any(k in t for k in ("全景", "パン", "荷室", "側面", "全体")): return "wide"
    return None

def want_cat(text):
    t = text or ""
    for k, c in (("荷室", "荷室"), ("後部座席", "後席"), ("リアシート", "後席"),
                 ("ドラレコ", "外観-リア"), ("リア", "外観-リア"),
                 ("側面", "外観-側面"), ("フロント", "外観-正面"), ("POP", "外観-正面寄り"),
                 ("メーター", "内装-運転席"), ("キー", "内装-運転席"),
                 ("シフト", "内装-運転席"), ("インパネ", "内装-運転席"),
                 ("運転席", "内装-運転席"), ("内装", "内装-全景")):
        if k in t: return c
    return None

slots = []
for r in sc["rows"]:
    pts = parse_pts(r.get("絵変わり点"))
    line_t0, dur = float(r["開始秒"]), float(r["尺予算"])
    bounds = sorted(set(pts + [dur]))
    is_insert = "挿入" in (r["視覚"] or "")
    for i in range(len(bounds) - 1) if len(bounds) > 1 else [0]:
        s0 = bounds[i] if len(bounds) > 1 else 0.0
        s1 = bounds[i + 1] if len(bounds) > 1 else dur
        seg = round(s1 - s0, 2)
        slots.append({
            "slot": f'{r["line"]}-{i+1}', "line": r["line"], "機能": r["機能"],
            "t0": round(line_t0 + s0, 2), "t1": round(line_t0 + s1, 2), "尺": seg,
            "尺帯": [round(max(band["min"], seg * 0.8), 2), round(min(band["max"], seg * 1.2), 2)],
            "求める画": "挿入" if (is_insert and i == 0) else ("挿入(継続/2段目)" if is_insert else "地(A-roll)"),
            "求めるカテゴリ": want_cat(r["視覚"]) if is_insert else "A-roll",
            "求めるshot_size": want_shot(r["視覚"]) if is_insert else None,
            "前スロットとカテゴリ相違": True,
            "パンチイン": (f'{pi["standard"]:.2f}' if r["パンチイン"] and i == 0 else
                          ("1.46(最大緊張・1本に1回)" if "146" in (r["備考"] or "") and i == 0 else None)),
            "SE": r["SE"] if i == 0 else [],
            "情緒": r.get("情緒", ""), "発話": r["音声"] if i == 0 else "",
            "視覚指定原文": r["視覚"] if i == 0 else "",
        })
tot = sum(s["尺"] for s in slots)
out = {"meta": {"video": sc["meta"].get("mode"), "slots": len(slots), "total": round(tot, 1),
                # ★参考の密度目標は visual_switch.per_min（A-roll+挿入の全視覚切替）を使う。
    # 旧 cuts_per_min=35.2 はA-rollトラックだけの値で、挿入による視覚変化が落ちていた（2026-07-30訂正）。
    "参考visual_switch_per_min": sp["visual_switch"]["per_min"],
    "参考cuts_per_min_ARoll_only": sp.get("cuts_per_min_ARoll_only"),
    "設計visual_switch_per_min": round(len(slots) / (tot / 60), 1),
                "参考cut_len帯": band},
       "slots": slots}
json.dump(out, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f'スロット {len(slots)} / 総尺 {tot:.1f}s / 設計 {out["meta"]["設計visual_switch_per_min"]} cuts/min '
      f'(参考 {sp["visual_switch"]["per_min"]})')
gaps = [s["尺"] for s in slots]
print(f'スロット尺: 最短{min(gaps):.1f}s 最長{max(gaps):.1f}s（参考帯 {band["min"]}-{band["max"]}s）')
need = [s for s in slots if s["求める画"] == "挿入"]
print(f'挿入を要求するスロット {len(need)} / 地(A-roll) {sum(1 for s in slots if s["求める画"]=="地(A-roll)")}')
