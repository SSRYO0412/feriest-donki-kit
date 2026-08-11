#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G90 参考突合 — 「参考と瓜二つか」を感想でなく数値で判定する。

★この案件で最も効いた是正は「参考のテロップは1種類ではない」「テンポも参考通りか」だった。
どちらも人の印象では出てこず、参考を実測して並べて初めて分かった。だからここは
`.fork/REFERENCE-TARGETS.json`（参考の実測値）との突合に固定する。

★測定は完成MP4の画素から行う。Premiere API の読み戻しでは座標系の誤りを原理的に検出できない
（同じAPIで書いて同じAPIで読むと、書き込みと読み出しが同じ誤りを共有して必ず一致する）。

依存は Python 標準ライブラリ と ffmpeg/ffprobe のみ。numpy も Pillow も要らない。

  python3 scripts/reference_match.py --build design/build_0801_v7.json \\
      --mp4 /path/to/ebi_v3.mov --out qc/reference_match.json

build.json の形（最小）:
  {"video_id":"0801","fps":30,"frames":337,
   "shots":[{"name":"c01","start_f":0,"end_f":28,"src":"IMG_2855","zoom":[100,110]}, ...],
   "telops":[{"text":"海老好き大集合","start_f":0,"end_f":57,
              "tier":"通常","font":"mplus-1p-heavy","size":68.948,"color":"#FDFCFD"}, ...]}
"""
import argparse, json, os, subprocess, sys, statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def P(*a): return os.path.join(ROOT, *a)

# ---------------------------------------------------------------- ffmpeg 薄皮

def probe_frames(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
         "-show_entries", "stream=nb_read_frames,width,height,r_frame_rate",
         "-of", "json", path], capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return {"frames": int(s["nb_read_frames"]), "w": int(s["width"]),
            "h": int(s["height"]), "fps": float(num) / float(den)}

def gray_frames(path, w, h):
    """全フレームを w×h の gray8 で読み出す。numpy を使わず bytes のまま扱う。"""
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={w}:{h}",
         "-pix_fmt", "gray", "-f", "rawvideo", "-"],
        capture_output=True, check=True).stdout
    n = w * h
    return [p[i * n:(i + 1) * n] for i in range(len(p) // n)]

PIC_BAND_H = 700   # ★カット判定に使う上部の高さ。テロップ（y850〜）を含めない

def gray_frames_region(path, x, y, w, h, sw, sh):
    """矩形領域だけを全フレーム gray8 で読む。"""
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path,
         "-vf", f"crop={w}:{h}:{x}:{y},scale={sw}:{sh}",
         "-pix_fmt", "gray", "-f", "rawvideo", "-"],
        capture_output=True, check=True).stdout
    n = sw * sh
    return [p[i * n:(i + 1) * n] for i in range(len(p) // n)]

def rgb_region(path, frame_idx, fps, x, y, w, h, sw, sh):
    """1フレームの矩形領域を sw×sh に縮めて rgb24 で取る。"""
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{frame_idx / fps:.4f}", "-i", path,
         "-frames:v", "1", "-vf", f"crop={w}:{h}:{x}:{y},scale={sw}:{sh}",
         "-pix_fmt", "rgb24", "-f", "rawvideo", "-"],
        capture_output=True, check=True).stdout
    return [(p[i], p[i + 1], p[i + 2]) for i in range(0, len(p) - 2, 3)]

# 輝度しきい値マップ（≥th を 1、それ以外 0 に潰す）→ .count で数える
def _tbl(th):
    return bytes(1 if i >= th else 0 for i in range(256))
TBL_WHITE = _tbl(250)
TBL_BLACK = bytes(1 if i <= 16 else 0 for i in range(256))

def ratio(buf, table):
    return buf.translate(table).count(1) / len(buf)

def mean_gray(buf):
    return sum(buf) / len(buf)

def dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5

def hex2rgb(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))

# ---------------------------------------------------------------- 判定

class R:
    """★逸脱を『無かったこと』にしない。免責するなら理由と独立承認を必ず残す。

    build.json の waivers に理由と independent_approval を書いた項目だけ WAIVED になる。
    理由だけで承認が無いものは WAIVED ではなく FAIL のまま（黙って通さない）。
    """
    def __init__(self, waivers=None):
        self.items = []
        self.waivers = waivers or {}
    def add(self, gid, name, ok, measured, expected, note=""):
        v = "PASS" if ok else "FAIL"
        w = self.waivers.get(gid)
        if v == "FAIL" and w:
            if w.get("reason") and w.get("independent_approval"):
                v = "WAIVED"
            else:
                note = (note + " ／★免責が不完全: reason と independent_approval の"
                                "両方が要る。片方だけでは FAIL のまま").strip()
        self.items.append({"id": gid, "name": name, "verdict": v,
                           "measured": measured, "expected": expected, "note": note,
                           **({"waiver": w} if v == "WAIVED" else {})})
    def failed(self):
        return [i for i in self.items if i["verdict"] == "FAIL"]
    def waived(self):
        return [i for i in self.items if i["verdict"] == "WAIVED"]


def check_tempo(build, T, r):
    fps = build["fps"]
    shots = build["shots"]
    lens = [s["end_f"] - s["start_f"] for s in shots]
    tgt, tol = T["tempo"], T["tempo_tolerance"]

    # 1) 最短ショット — 参考の最短14Fが知覚の下限
    floor = tol["shot_len_min_frames_floor"]
    bad = [(s["name"], l) for s, l in zip(shots, lens) if l < floor]
    r.add("G90-1", "最短ショット", not bad, {"under_floor": bad, "min": min(lens)},
          {">=": floor}, tol["_floor_reason"])

    # 2) 最長ショット
    cap = tgt["shot_len_max_frames"]
    over = [(s["name"], l) for s, l in zip(shots, lens) if l > cap]
    r.add("G90-2", "最長ショット", not over, {"over_cap": over, "max": max(lens)},
          {"<=": cap}, "超えるなら『画の強さ』の根拠を書く。0801では静止全景2.17秒が弱いと指摘された")

    # 3) 尺の中央値
    med = st.median(lens)
    ref, pct = tgt["shot_len_median_frames"], tol["shot_len_median_pct"]
    lo, hi = ref * (1 - pct / 100), ref * (1 + pct / 100)
    r.add("G90-3", "ショット尺の中央値", lo <= med <= hi,
          {"median_frames": med, "median_sec": round(med / fps, 3)},
          {"band_frames": [round(lo, 1), round(hi, 1)], "ref": ref})

    # 4) ★主判定 — 1テロップあたりのショット数
    nt = len(build["telops"])
    spt = len(shots) / nt if nt else None
    ref, pct = tgt["shots_per_telop"], tol["shots_per_telop_pct"]
    lo, hi = ref * (1 - pct / 100), ref * (1 + pct / 100)
    r.add("G90-4", "1テロップあたりのショット数（主判定）",
          spt is not None and lo <= spt <= hi,
          {"shots": len(shots), "telops": nt,
           "shots_per_telop": round(spt, 3) if spt else None},
          {"band": [round(lo, 3), round(hi, 3)], "ref": ref},
          tgt["_note"] if "_note" in tgt else "")

    # 5) cuts/分 — ★参考値だが単独では合否にしない（テロップ密度を無視した過剰分割を招くため）
    dur = build["frames"] / fps
    cpm = len(shots) / dur * 60
    r.add("G90-5", "cuts/分（参考値・単独では合否にしない）", True,
          {"cuts_per_min": round(cpm, 1), "duration_sec": round(dur, 3)},
          {"ref": tgt["cuts_per_min"]},
          "★これだけを参考に合わせると過剰分割になる。主判定はG90-4")


def check_telop_style(build, T, r):
    """★テロップは1種類ではない。全区間が3階層のどれかに厳密に一致するか。"""
    tiers = T["telop_grammar"]["tiers"]
    def norm(s):
        # 「商品名の2行組(上段)」のような但し書きを落として階層名だけで見る
        return (s or "").split("(")[0].split("（")[0].strip()
    def matches(t):
        for tier in tiers:
            if t.get("tier") and norm(t["tier"]) != norm(tier["kind"]):
                continue
            fonts = [tier.get("font")] if tier.get("font") else []
            if "size" in tier:
                sizes = tier["size"] if isinstance(tier["size"], list) else [tier["size"]]
            else:  # 商品名2行組
                sizes = ([tier["size_top"]] +
                         (tier["size_bottom"] if isinstance(tier["size_bottom"], list)
                          else [tier["size_bottom"]]))
            if t.get("font") in fonts and any(abs(t.get("size", -1) - s) < 0.5 for s in sizes):
                return tier["kind"]
        return None
    bad = [{"text": t.get("text"), "font": t.get("font"), "size": t.get("size"),
            "declared_tier": t.get("tier")} for t in build["telops"] if not matches(t)]
    r.add("G90-6", "テロップ様式が3階層のどれかに一致", not bad,
          {"off_grammar": bad, "n": len(build["telops"])},
          {"tiers": [t["kind"] for t in tiers]},
          T["telop_grammar"]["_note"])

    # フチ色 — ★純黒ではない
    sc = T["telop_grammar"]["stroke_color"]
    off = [t.get("text") for t in build["telops"]
           if t.get("stroke") and t["stroke"].upper() != sc.upper()]
    r.add("G90-7", "フチ色", not off, {"off": off},
          {"stroke_color": sc}, T["telop_grammar"]["_stroke_note"])


def check_pixels(build, T, mp4, r, band_px=None):
    """★完成画素での実測。読み戻しでは検出できないものをここで捕まえる。"""
    info = probe_frames(mp4)
    fps = info["fps"]
    r.add("G90-8", "尺（完成ファイル）", info["frames"] == build["frames"],
          {"mp4_frames": info["frames"], "wh": [info["w"], info["h"]], "fps": fps},
          {"design_frames": build["frames"], "wh": [1080, 1920]},
          "★書き出しが途中で止まっても報告は成功に見える。実ファイルで数える")

    GW, GH = 64, 114                       # 縮小グレー（判定に十分・全フレーム保持できる）
    fr = gray_frames(mp4, GW, GH)
    n = min(len(fr), build["frames"])

    # 9) 白飛び — ★絶対値でなく他ショットとの相対で見る
    wr = {}
    for s in build["shots"]:
        a, b = s["start_f"], min(s["end_f"], n)
        if a >= b: continue
        mid = (a + b) // 2
        wr[s["name"]] = round(ratio(fr[mid], TBL_WHITE), 5)
    vals = sorted(wr.values())
    m = st.median(vals) if vals else 0
    # 他が概ね0なのに1つだけ突出、を拾う（0801の c04 6.34% / 他0.00% がこの形）
    out = {k: v for k, v in wr.items() if v > 0.02 or (v > 0.005 and v > m * 20 + 0.002)}
    r.add("G90-9", "白飛び（相対比較）", not out, {"per_shot": wr, "median": m},
          {"outliers": 0, "abs_max": 0.02},
          "★他のショットと比べて初めて異常と分かる。絶対値だけで判断しない")

    # 10) 黒フレーム
    blk = [i for i in range(n) if ratio(fr[i], TBL_BLACK) > 0.98]
    r.add("G90-10", "黒フレーム", not blk, {"frames": blk[:20], "n": len(blk)}, {"n": 0})

    # 11) ★設計カット点で画が変わるか／設計外で変わっていないか
    #
    # ★テロップ帯を含めて測ると、テロップの切り替わりと出現アニメを「画変わり」と誤検出する
    #   （0801では c01 の強調アニメが frames 3-8 に偽の画変わりを5つ出した）。
    #   カットは『画』で判定するので、テロップの載る帯を外した上部だけを見る。
    # ★しきい値だけだと素材内の速い動きを拾う。カットは1フレームの尖ったピークなので
    #   「前後より 1.8 倍以上高い局所ピーク」を条件に足す。この2つで 0801 は miss 0 / extra 0。
    pic = gray_frames_region(mp4, 0, 0, info["w"], PIC_BAND_H, 64, 40)
    m = min(len(pic), build["frames"])
    d = [sum(abs(x - y) for x, y in zip(pic[i], pic[i - 1])) / len(pic[i])
         for i in range(1, m)]
    med_d = st.median(d) if d else 0
    thr = max(6.0, med_d * 3.5)
    detected = set()
    for i in range(1, len(d) + 1):
        v = d[i - 1]
        if v <= thr:
            continue
        nb = [d[j - 1] for j in (i - 1, i + 1) if 1 <= j <= len(d)]
        if nb and v > 1.8 * max(nb):
            detected.add(i)
    designed = {s["start_f"] for s in build["shots"] if s["start_f"] > 0}
    def near(f, S, w=2): return any(abs(f - g) <= w for g in S)
    missing = sorted(f for f in designed if not near(f, detected))
    extra   = sorted(f for f in detected if not near(f, designed))
    r.add("G90-11", "設計カット点で画が変わる", not missing,
          {"missing_cuts": missing, "threshold": round(thr, 2), "median_diff": round(med_d, 2)},
          {"missing": 0},
          "設計上は切ったのに画が変わらない＝同一素材の連続や差し替え漏れ")
    r.add("G90-12", "設計外の画変わりが無い", not extra,
          {"unexpected_at": extra}, {"n": 0},
          "★素材内のシーン切替を踏んでいる可能性。窓の t0/t1 を実画で見直す")

    # 12) テロップの ΔRGB — 背景から浮いているか
    lay = T["telop_grammar"]["layout_measured"]
    y0, y1 = (band_px or lay["bottom_y"])
    mind = T["telop_contrast"]["min_delta"]
    rows = []
    for t in build["telops"]:
        if not t.get("color"): continue
        a, b = t["start_f"], min(t["end_f"], n)
        if a >= b: continue
        mid = (a + b) // 2
        # ★背景は「テロップ色から遠い画素」で定義してはいけない。
        #   除外半径が合格しきい値と同じだと ΔRGB が構造的にしきい値を下回れず、
        #   判定が原理的に空振りする（G92 較正ハーネスがこの穴を実際に検出した）。
        #   文字はフチ（暗い輪郭）で囲まれているので、フチの位置で幾何的に文字域を取り、
        #   膨張させて外した残りを背景とする。色ではなく形で分けるので Δ に下限が生まれない。
        SW, SH = 120, 16
        px = rgb_region(mp4, mid, fps, 0, y0, info["w"], max(1, y1 - y0), SW, SH)
        tc, sc = hex2rgb(t["color"]), hex2rgb(t.get("stroke") or
                                              T["telop_grammar"]["stroke_color"])
        mask = [dist(p, sc) < 60 or dist(p, tc) < 30 for p in px]
        dil = list(mask)
        for yy in range(SH):
            for xx in range(SW):
                if not mask[yy * SW + xx]: continue
                for dy in range(-2, 3):
                    for dx in range(-4, 5):
                        ny, nx = yy + dy, xx + dx
                        if 0 <= ny < SH and 0 <= nx < SW:
                            dil[ny * SW + nx] = True
        bg = [p for p, m in zip(px, dil) if not m]
        if len(bg) < len(px) * 0.08:
            rows.append({"text": t.get("text"), "telop": t["color"], "bg": None,
                         "delta": None, "ok": False,
                         "_why": "背景画素が足りず測れない（文字が帯を埋めている）。帯の指定を見直す"})
            continue
        mb = tuple(sum(c[i] for c in bg) / len(bg) for i in range(3))
        dd = dist(tc, mb)
        rows.append({"text": t.get("text"), "telop": t["color"],
                     "bg": "#%02X%02X%02X" % tuple(int(v) for v in mb),
                     "bg_px_ratio": round(len(bg) / len(px), 3),
                     "delta": round(dd, 1), "ok": dd >= mind})
    r.add("G90-13", "テロップと背景の ΔRGB", all(x["ok"] for x in rows),
          {"per_telop": rows}, {">=": mind, "band": T["telop_contrast"]["reference_band"]},
          T["telop_contrast"]["_note"])


def check_zoom(build, T, r):
    z = T["zoom_grammar"]
    lo, hi = z["others"]["end_range"]
    bad, waived = [], []
    for s in build["shots"]:
        if not s.get("zoom"): continue
        a, b = s["zoom"][0], s["zoom"][-1]
        if s.get("punch"): continue          # 冒頭パンチは別文法
        if a != z["others"]["start"] or not (lo <= b <= hi):
            w = s.get("zoom_waiver")
            # ★ショット単位の免責。理由と独立承認が揃っているものだけ外す。
            #   1つ免責したからといって他の逸脱まで通してはならない
            if w and w.get("reason") and w.get("independent_approval"):
                waived.append({"shot": s["name"], "zoom": s["zoom"], "waiver": w})
            else:
                bad.append({"shot": s["name"], "zoom": s["zoom"],
                            "_why": "理由と独立承認が揃っていない"})
    r.add("G90-14", "ズーム文法", not bad, {"off_grammar": bad, "waived": waived},
          {"start": z["others"]["start"], "end_range": [lo, hi]},
          "★意図して外すのは可。ただし外した分だけ shots[].zoom_waiver に理由と独立承認を残す"
          "（0801のc04は『もっとピザに寄って。』の指示で115→135）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", required=True)
    ap.add_argument("--mp4")
    ap.add_argument("--targets", default=P(".fork/REFERENCE-TARGETS.json"))
    ap.add_argument("--out", default="qc/reference_match.json")
    ap.add_argument("--telop-band", nargs=2, type=int,
                    help="下段テロップのyレンジ。省略時は参考の実測値を使う")
    a = ap.parse_args()

    T = json.load(open(a.targets, encoding="utf-8"))
    build = json.load(open(a.build, encoding="utf-8"))
    r = R(build.get("waivers"))

    check_tempo(build, T, r)
    check_telop_style(build, T, r)
    check_zoom(build, T, r)
    if a.mp4:
        check_pixels(build, T, a.mp4, r, a.telop_band)
    else:
        r.add("G90-P", "画素実測", False, {"mp4": None}, {"mp4": "required"},
              "★--mp4 を渡さない実行は G90 の合格にならない。設計値だけの検算は"
              "『同じ座標系で書いて同じ座標系で読む』のと同じ穴を残す")

    res = {"gate": "G90", "name": "参考突合（瓜二つ判定）",
           "video_id": build.get("video_id"), "build": a.build, "mp4": a.mp4,
           "reference": T["reference"]["name"],
           "verdict": "PASS" if not r.failed() else "FAIL",
           "n_fail": len(r.failed()), "n_waived": len(r.waived()), "items": r.items,
           "_waived_note": "★WAIVED は『測ったら外れていたが、理由と独立承認を添えて残した』の意味。"
                           "PASS と混ぜて数えない。台帳にはこの件数をそのまま書く",
           "_note": "★これは測定なのでモデル多様性の問題を受けない。"
                    "判断が要るゲート（G50系・G91）とは別物として扱う"}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(res, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    for i in r.items:
        print(f"  {i['verdict']:4s} {i['id']:7s} {i['name']}")
        if i["verdict"] == "FAIL":
            print(f"        measured={json.dumps(i['measured'], ensure_ascii=False)[:220]}")
    print(f"\n{res['verdict']}  ({res['n_fail']} fail / {len(r.items)})  → {a.out}")
    return 1 if res["verdict"] == "FAIL" else 0

if __name__ == "__main__":
    sys.exit(main())
