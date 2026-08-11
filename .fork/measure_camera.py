#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""原本188本のカメラワークを1秒粒度で実測する（発注側の事前計算・配布物には結果だけ入れる）。

★DBの動き列は「大きさ」しか持たず、種類（パン方向・ズームイン/アウト・手持ち揺れ）が
  分からない。修正指示は「もっと激しく」「引きで」「安定した画で」のように種類で来るので、
  原本から位相相関で測り直して分類する。

方法:
  - 各クリップを gray 160x120 / 6fps でデコード（ffmpeg が rotation メタを自動適用するので
    画面座標＝視聴時の向き）
  - 隣接フレームの位相相関 → 画面の流れ (dx, dy)[px/frame]
  - 左右半分・上下半分の相関差 → 発散 div（正=ズームイン/前進、負=ズームアウト）
  - 1秒（6ペア）ごとに集計: 平均ベクトル・平均量・ジッタ（ぶれ）・発散
  - 分類: static / pan_left|right|up|down / zoom_in|zoom_out / handheld / drift
    ★方向は「画面内の被写体が流れる向き」。カメラの向きはその逆

実行: /usr/bin/python3 .fork/measure_camera.py（numpy が要るのは発注側のここだけ）
出力: SSD 側キャッシュ camera_buckets.json（repo には配布用の集約だけを入れる）
"""
import json, os, subprocess, sys
import numpy as np
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = "/Volumes/Extreme SSD/FERIEST/00_source_drive/20260807_新素材_8月掲載分"
OUT = "/Volumes/Extreme SSD/FERIEST/01_assets/db_202608/camera_buckets_v1.json"
W, H, FPS = 160, 120, 6

def decode(path):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", path,
                        "-vf", f"fps={FPS},scale={W}:{H}", "-pix_fmt", "gray",
                        "-f", "rawvideo", "-"], capture_output=True).stdout
    n = len(p) // (W * H)
    return np.frombuffer(p[:n * W * H], np.uint8).reshape(n, H, W).astype(np.float32)

_HANN = {}
def _hann(shape):
    if shape not in _HANN:
        _HANN[shape] = np.outer(np.hanning(shape[0]), np.hanning(shape[1]))
    return _HANN[shape]

def shift(a, b):
    """位相相関で a→b の画面の流れ (dx, dy) を推定する。★窓はフレーム形状ごとに作る
    （全体サイズ固定の窓を半分フレームに掛けて broadcast エラーになった）。"""
    h, w = a.shape
    win = _hann(a.shape)
    fa, fb = np.fft.rfft2(a * win), np.fft.rfft2(b * win)
    r = fb * np.conj(fa)
    r /= (np.abs(r) + 1e-6)
    c = np.fft.irfft2(r, s=(h, w))
    py, px = np.unravel_index(np.argmax(c), c.shape)
    dy = py if py <= h // 2 else py - h
    dx = px if px <= w // 2 else px - w
    return float(dx), float(dy)

def measure_clip(args):
    prod, clip, dur = args
    for ext in (".MP4", ".MOV", ".mp4", ".mov"):
        path = os.path.join(SRC, prod, clip + ext)
        if os.path.exists(path):
            break
    else:
        return prod, clip, None
    fr = decode(path)
    if len(fr) < 2:
        return prod, clip, None
    hw = W // 2; hh = H // 2
    rows = []
    for i in range(1, len(fr)):
        a, b = fr[i - 1], fr[i]
        dx, dy = shift(a, b)
        # 発散: 左右半分の水平流の差 + 上下半分の垂直流の差（正=広がる=ズームイン）
        lx, _ = shift(a[:, :hw], b[:, :hw]); rx, _ = shift(a[:, hw:], b[:, hw:])
        _, ty = shift(a[:hh], b[:hh]);       _, by = shift(a[hh:], b[hh:])
        rows.append((dx, dy, (rx - lx) + (by - ty)))
    v = np.array(rows)                            # (N,3): dx dy div
    buckets = []
    for s in range(0, len(v), FPS):
        seg = v[s:s + FPS]
        if not len(seg):
            continue
        mvx, mvy = seg[:, 0].mean(), seg[:, 1].mean()
        mag = float(np.hypot(seg[:, 0], seg[:, 1]).mean())      # 平均の動き量 px/frame
        jit = float(np.hypot(seg[:, 0] - mvx, seg[:, 1] - mvy).mean())  # ぶれ
        div = float(seg[:, 2].mean())
        # 明るさ系も同じフレームから（白飛びは輝度250以上の画素比）
        f = fr[min(s + FPS // 2, len(fr) - 1)]
        white = float((f >= 250).mean()); bright = float(f.mean())
        sharp = float(np.abs(np.diff(f, axis=1)).mean())        # 粗い相対シャープ
        buckets.append({"t": s // FPS,
                        "vx": round(float(mvx), 2), "vy": round(float(mvy), 2),
                        "mag": round(mag, 2), "jitter": round(jit, 2),
                        "div": round(div, 2), "white": round(white, 4),
                        "bright": round(bright, 1), "sharp": round(sharp, 2)})
    return prod, clip, buckets

def main():
    man = json.load(open(os.path.join(ROOT, "data/asset_db/media_manifest.json")))
    jobs = [(p, c, d) for p, v in man["products"].items() for c, d in v["clips"].items()]
    print(f"{len(jobs)}本を測定（6fps・160x120・位相相関）", flush=True)
    out = {}
    done = 0
    with ThreadPoolExecutor(max_workers=8) as ex:      # ExFAT なので par15 以下厳守
        for prod, clip, b in ex.map(measure_clip, jobs):
            done += 1
            if b is None:
                print(f"  !! 測定不能 {prod}/{clip}", flush=True)
                continue
            out.setdefault(prod, {})[clip] = b
            if done % 20 == 0:
                print(f"  {done}/{len(jobs)}", flush=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False)
    n = sum(len(b) for v in out.values() for b in v.values())
    print(f"buckets={n} → {OUT}")

if __name__ == "__main__":
    main()
