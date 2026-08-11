#!/usr/bin/env python3
"""主映像（A-roll）が素で見えている区間の「変なところ」を測る。

なぜ要るか（2026-07-29 ユーザー指摘）:
> 「Aロールで何か変なところがある部分を検出してほしい」

「変」のままでは測れないので、測れる症状に分解する:
  1. 手ブレ・大きな振り … 連続フレームの移動量（位相相関）
  2. ピンボケ           … ラプラシアン分散の急落
  3. 露出の段差         … フレーム平均輝度の1次差分
  4. 色の段差           … 色ヒストグラムの距離
  5. 画の停止           … 連続フレームの差がほぼ0（尺の割に動きが無い）

★測る範囲は **A-rollが素で見えている区間だけ**。
  挿入映像で隠れている区間は画が成立しているので対象外（CUT-QC-RULES 0-3）。

★このスクリプトは合否を出さない。閾値超えの区間を列挙して、
  そのフレームを書き出す。良し悪しは目とCodexが決める。
  画像解析は閾値依存で必ず取りこぼすので、**候補を絞る道具**として使う。

使い方:
  python3 qc_aroll_anomaly.py <完成MP4 または A-rollのMP4> <broll.json> <総尺>
        [--fps 10] [--out qc/aroll_anomaly.json] [--dump qc/aroll_flagged]
"""
import json, os, subprocess, sys, argparse
import numpy as np


def exposed(broll, dur):
    """挿入映像に隠れていない区間を返す"""
    iv = sorted((x["tl_in"], x["tl_in"] + x["dur"]) for x in broll)
    out, cur = [], 0.0
    for a, b in iv:
        if a > cur:
            out.append((cur, a))
        cur = max(cur, b)
    if cur < dur:
        out.append((cur, dur))
    return [(a, b) for a, b in out if b - a > 0.3]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mp4")
    ap.add_argument("broll")
    ap.add_argument("duration", type=float)
    ap.add_argument("--fps", type=int, default=10)
    ap.add_argument("--out", default="qc/aroll_anomaly.json")
    ap.add_argument("--dump", default=None)
    ap.add_argument("--cutlist", default=None,
                    help="★指定するとカット境界の前後を除外する。境界では画が変わるのが当然で、"
                         "指定しないと段差の検出が境界だらけになる（実際に大半が境界だった）")
    a = ap.parse_args()

    import cv2
    br = json.load(open(a.broll, encoding="utf-8"))
    br = br["inserts"] if isinstance(br, dict) else br
    zones = exposed(br, a.duration)

    W = 240
    cmd = ["ffmpeg", "-v", "error", "-i", a.mp4, "-vf", f"fps={a.fps},scale={W}:-2",
           "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    cmdc = ["ffmpeg", "-v", "error", "-i", a.mp4, "-vf", f"fps={a.fps},scale=64:-2",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    rawc = subprocess.run(cmdc, capture_output=True).stdout
    # 高さを推定
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=width,height", "-of", "csv=p=0", a.mp4],
                           capture_output=True, text=True).stdout.strip().split(",")
    sw, sh = int(probe[0]), int(probe[1])
    H = int(round(sh * W / sw / 2)) * 2
    Hc = int(round(sh * 64 / sw / 2)) * 2
    n = len(raw) // (W * H)
    g = np.frombuffer(raw[:n * W * H], dtype=np.uint8).reshape(n, H, W).astype(np.float32)
    nc = len(rawc) // (64 * Hc * 3)
    c = np.frombuffer(rawc[:nc * 64 * Hc * 3], dtype=np.uint8).reshape(nc, Hc, 64, 3).astype(np.float32)
    n = min(n, nc)
    print(f"フレーム {n}枚（{a.fps}fps・{W}x{H}）/ 素見え区間 {len(zones)}箇所")

    # 指標
    mean = g.reshape(n, -1).mean(axis=1)
    diff = np.r_[0, np.abs(np.diff(g, axis=0)).mean(axis=(1, 2))]
    lap = np.array([cv2.Laplacian(g[i], cv2.CV_32F).var() for i in range(n)])
    colr = np.r_[0, np.abs(np.diff(c.reshape(nc, -1)[:n], axis=0)).mean(axis=1)]
    # 移動量（位相相関）
    shift = np.zeros(n)
    for i in range(1, n):
        try:
            (dx, dy), _ = cv2.phaseCorrelate(g[i - 1], g[i])
            shift[i] = (dx * dx + dy * dy) ** 0.5
        except Exception:
            shift[i] = 0.0

    def inzone(t):
        return any(x <= t <= y for x, y in zones)

    ts = np.arange(n) / a.fps
    mask = np.array([inzone(t) for t in ts])
    sel = np.where(mask)[0]
    if len(sel) < 10:
        sys.exit("★素見え区間が短すぎて測れない")

    def flag(arr, label, hi=True, k=3.0, unit=""):
        v = arr[sel]
        med, mad = np.median(v), np.median(np.abs(v - np.median(v))) + 1e-9
        z = (v - med) / (1.4826 * mad)
        idx = sel[(z > k) if hi else (z < -k)]
        out, run = [], None
        for i in idx:
            if run and i - run[-1] <= 2:
                run.append(i)
            else:
                if run:
                    out.append(run)
                run = [i]
        if run:
            out.append(run)
        return [{"kind": label, "start": round(r[0] / a.fps, 2), "end": round(r[-1] / a.fps, 2),
                 "peak": round(float(arr[r].max() if hi else arr[r].min()), 3),
                 "median": round(float(med), 3), "unit": unit} for r in out]

    # ★カット境界は画が変わって当然なので除外する
    bnd = []
    if a.cutlist:
        cd = json.load(open(a.cutlist, encoding="utf-8"))
        bnd = [c["tl"] for c in cd["cuts"]]
    for x in br:
        bnd += [x["tl_in"], x["tl_in"] + x["dur"]]
    bnd = sorted(bnd)

    def near_boundary(t, margin=0.25):
        return any(abs(t - b) <= margin for b in bnd)

    hits = (flag(shift, "カメラの振り・手ブレ", True, 3.5, "px/frame")
            + flag(lap, "ピンボケ", False, 3.0, "ラプラシアン分散")
            + flag(np.abs(np.r_[0, np.diff(mean)]), "露出の段差", True, 4.0, "輝度差")
            + flag(colr, "色の段差", True, 4.0, "RGB差"))
    # 画の停止
    stop, run = [], None
    for i in sel:
        if diff[i] < 0.6:
            run = (run or []) + [i]
        else:
            if run and (run[-1] - run[0]) / a.fps >= 1.5:
                stop.append({"kind": "画がほぼ止まっている",
                             "start": round(run[0] / a.fps, 2), "end": round(run[-1] / a.fps, 2),
                             "peak": round(float(diff[run].mean()), 3), "median": None, "unit": "フレーム差"})
            run = None
    hits += stop
    n_all = len(hits)
    hits = [h for h in hits if not (near_boundary(h["start"]) or near_boundary(h["end"]))]
    hits.sort(key=lambda x: x["start"])
    print(f"境界の除外: {n_all}件 → {len(hits)}件（カット/挿入の境界±0.25秒は画が変わって当然）")

    if a.dump and hits:
        os.makedirs(a.dump, exist_ok=True)
        for h in hits:
            t = (h["start"] + h["end"]) / 2
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t}", "-i", a.mp4,
                            "-vframes", "1", "-vf", "scale=360:-2",
                            f"{a.dump}/{h['kind']}_{h['start']:.2f}.jpg"])

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump({"mp4": a.mp4, "fps": a.fps, "exposed_zones": [[round(x, 2), round(y, 2)] for x, y in zones],
               "_note": "合否は出さない。閾値超えの区間を挙げるだけ。良し悪しは目とCodexが決める。",
               "flags": hits}, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"\n候補 {len(hits)}件")
    for h in hits:
        print(f"  {h['start']:7.2f}-{h['end']:7.2f}  {h['kind']:<18} ピーク{h['peak']}（中央値{h['median']}）{h['unit']}")
    print(f"→ {a.out}" + (f" / フレーム {a.dump}" if a.dump else ""))


if __name__ == "__main__":
    main()
