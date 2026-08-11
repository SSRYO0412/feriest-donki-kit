#!/usr/bin/env python3
"""pacing_measure.py — ペーシングカーブ（需要の正本）の実測と設計照合。案件非依存。

measure: 参考動画から実測 → pacing_curve.json
  - カット密度カーブ（時間正規化ビンごとの cuts/10s）
  - ショット長の分布（前/中/後の三分位ごとに 中央値・最短・最長）
  - シーン検出は**複数閾値スイープ**（単一閾値はトーキングヘッドのジャンプカットを
    4割取りこぼす実証あり → 0.20/0.30/0.40 の和集合を0.30秒で併合）
design: 自分の設計（cutlist+broll）から**全数列挙**で同じカーブを計算（画像解析に頼らない）
check:  design のカーブを pacing_curve.json の帯（±tol）と照合。帯外ビンがあれば FAIL

使い方:
  python3 pacing_measure.py measure <video.mp4> [--bins 10] [--out pacing_curve.json]
  python3 pacing_measure.py design <profile> [--bins 10]
  python3 pacing_measure.py check <profile> [--tol 0.35]
"""
import json, os, re, sys, subprocess, argparse


def probe_dur(v):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", v], capture_output=True, text=True)
    return float(r.stdout.strip())


def scene_times(video, th):
    r = subprocess.run(
        ["ffmpeg", "-i", video, "-vf", f"select='gt(scene,{th})',metadata=print",
         "-an", "-f", "null", "-"], capture_output=True, text=True)
    return [float(m.group(1)) for m in
            re.finditer(r"pts_time:([0-9.]+)", r.stderr + r.stdout)]


def merge(ts, eps=0.30):
    out = []
    for t in sorted(ts):
        if not out or t - out[-1] >= eps:
            out.append(t)
    return out


def curve_from_cuts(cut_times, dur, bins):
    per = [0] * bins
    for t in cut_times:
        per[min(bins - 1, int(t / dur * bins))] += 1
    return [round(c / (dur / bins) * 10, 2) for c in per]     # cuts/10s


def shot_stats(bounds, dur):
    edges = [0.0] + sorted(bounds) + [dur]
    lens = [b - a for a, b in zip(edges, edges[1:]) if b - a > 0.01]
    thirds = {"head": [], "mid": [], "tail": []}
    for a, b in zip(edges, edges[1:]):
        k = "head" if a < dur / 3 else ("mid" if a < dur * 2 / 3 else "tail")
        thirds[k].append(b - a)
    def st(ls):
        if not ls:
            return None
        ls = sorted(ls)
        return {"median": round(ls[len(ls) // 2], 2), "min": round(ls[0], 2),
                "max": round(ls[-1], 2), "n": len(ls)}
    return {k: st(v) for k, v in thirds.items()}, st(lens)


def design_bounds(prof, root):
    """設計値からショット境界を全数列挙（A-rollカット境界＋B-rollのin/out）"""
    def P(rel):
        return rel if os.path.isabs(rel) else os.path.join(root, rel)
    cl = json.load(open(P(prof["artifacts"]["cutlist"]), encoding="utf-8"))
    br = json.load(open(P(prof["artifacts"]["broll"]), encoding="utf-8"))
    ins = br["inserts"] if isinstance(br, dict) else br
    dur = cl["duration"]

    def covered(t):
        """挿入に覆われた時刻か（覆われたA-rollカット境界は画面上のショット境界ではない）"""
        return any(x["tl_in"] - 0.02 < t < x["tl_in"] + x["dur"] + 0.02 for x in ins)

    b = set()
    for c in cl["cuts"][1:]:
        if not covered(c["tl"]):
            b.add(round(c["tl"], 2))
    for x in ins:
        b.add(round(x["tl_in"], 2))
        b.add(round(x["tl_in"] + x["dur"], 2))
    # 隣接挿入が吸着している境界は1つに（20F閉じの結果）
    cover = sum(x["dur"] for x in ins)
    return sorted(t for t in b if 0.05 < t < dur - 0.05), dur, cover


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("measure"); p.add_argument("video")
    p.add_argument("--bins", type=int, default=10)
    p.add_argument("--ths", default="0.20,0.30,0.40")
    p.add_argument("--out", default="pacing_curve.json")
    p = sub.add_parser("design"); p.add_argument("profile")
    p.add_argument("--bins", type=int, default=10)
    p = sub.add_parser("check"); p.add_argument("profile")
    p.add_argument("--tol", type=float, default=0.35)
    p.add_argument("--bins", type=int, default=10)
    a = ap.parse_args()

    if a.cmd == "measure":
        dur = probe_dur(a.video)
        ts = []
        for th in a.ths.split(","):
            ts += scene_times(a.video, float(th))
        bounds = merge(ts)
        curve = curve_from_cuts(bounds, dur, a.bins)
        thirds, overall = shot_stats(bounds, dur)
        doc = {"_note": "参考実測ペーシングカーブ。案件プロファイルから参照する。"
                        "参考が変われば再測定（数値をスキルに焼かない）。",
               "source": os.path.abspath(a.video), "duration": round(dur, 2),
               "bins": a.bins, "cuts_per_10s": curve,
               "shot_len": {"thirds": thirds, "overall": overall},
               "n_cuts": len(bounds)}
        json.dump(doc, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"{a.video}: {dur:.1f}s / カット {len(bounds)} / cuts_per_10s {curve} → {a.out}")
        return

    prof = json.load(open(a.profile, encoding="utf-8"))
    root = prof["root"]
    bounds, dur, cover = design_bounds(prof, root)
    curve = curve_from_cuts(bounds, dur, a.bins)
    thirds, overall = shot_stats(bounds, dur)
    if a.cmd == "design":
        print(f"設計: {dur:.1f}s / 境界 {len(bounds)}（全数列挙） / 挿入被覆 {cover/dur*100:.0f}%")
        print(f"cuts_per_10s {curve}")
        print("shot_len thirds:", json.dumps(thirds, ensure_ascii=False))
        return

    # ---- check ----
    pc_rel = prof.get("selection", {}).get("pacing_curve", "qc/pacing_curve.json")
    pc_path = pc_rel if os.path.isabs(pc_rel) else os.path.join(root, pc_rel)
    if not os.path.exists(pc_path):
        sys.exit(f"★参考カーブが無い: {pc_path}（pacing_measure.py measure <参考動画> で作る）")
    ref = json.load(open(pc_path, encoding="utf-8"))
    rc = ref["cuts_per_10s"]
    if len(rc) != len(curve):
        sys.exit("★ビン数が参考と不一致")
    bad = []
    for i, (d, r) in enumerate(zip(curve, rc)):
        lo, hi = r * (1 - a.tol), r * (1 + a.tol)
        if not (lo <= d <= hi):
            bad.append({"bin": i, "pos": f"{i*100//len(rc)}-{(i+1)*100//len(rc)}%",
                        "design": d, "ref": r, "band": [round(lo, 2), round(hi, 2)]})
    print(f"設計 {curve}\n参考 {rc}\n帯外ビン {len(bad)}件")
    for x in bad:
        print(f"  ★{x['pos']}: 設計{x['design']} / 参考{x['ref']} / 帯{x['band']}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
