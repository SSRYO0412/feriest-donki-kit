#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修正即応の事前計算（発注側のみ実行可能）。配布物には「答えの表」だけを入れる。

★狙い: 素材解析DBを配布せずに、修正指示への数値絞り込みをDBあり時と同じ精度・速さにする。
  0801 の修正12ラウンド＋敵対レビュー6件を分解すると、DBを引いた場面は全て次の軸に収まる:
    白飛び / 動き量 / ★カメラワークの種類 / 寄り引き / 人物 / 被写体中心 / 尺(t0/t1)

入力（発注側マシンにのみ存在）:
  - 退避DB: feriest_0801-0805_windows_kitcopy.sqlite（窓の t0/t1・white_max・person_count 等）
  - camera_buckets_v1.json（.fork/measure_camera.py の実測。1秒粒度の流れ/ぶれ/発散）
  - 原本フッテージ（被写体中心の画素計算）

出力（配布物・repo に入れる）:
  - data/revision_aids/clip_profiles.json  188本×1秒粒度の数値プロファイル＋カメラ分類
  - data/revision_aids/alternatives.json   30スロット×軸別の代替候補 top5 ＋ 商材別の極値リスト

実行: /usr/bin/python3 .fork/gen_revision_aids.py   （numpy は発注側のここだけ）
"""
import json, os, sqlite3, subprocess, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = "/Volumes/Extreme SSD/FERIEST/01_assets/db_202608/feriest_0801-0805_windows_kitcopy.sqlite"
CAM = "/Volumes/Extreme SSD/FERIEST/01_assets/db_202608/camera_buckets_v1.json"
SRC = "/Volumes/Extreme SSD/FERIEST/00_source_drive/20260807_新素材_8月掲載分"

# ---------------------------------------------------------------- カメラ分類
# ★しきい値は 160x120・6fps の実測分布から決めた（下の main で分布を出して検証する）。
#   方向は「画面内の被写体が流れる向き」。カメラの向きはその逆。

def classify(b):
    mag, jit, div = b["mag"], b["jitter"], abs(b["div"])
    if mag < 0.6 and jit < 0.6:
        return "static"
    if abs(b["div"]) >= max(1.2, mag * 0.8):
        return "zoom_in" if b["div"] > 0 else "zoom_out"
    if jit > mag * 1.2 and jit > 1.2:
        return "handheld"                      # ぶれ主体（狙いの無い揺れ）
    if mag >= 1.2:
        vx, vy = b["vx"], b["vy"]
        if abs(vx) >= abs(vy):
            return "pan_right" if vx > 0 else "pan_left"
        return "pan_down" if vy > 0 else "pan_up"
    return "drift"                             # 小さく流れている（手持ちの自然な揺らぎ）

def summarize_window(buckets, t0, t1):
    seg = [b for b in buckets if t0 - 0.5 <= b["t"] <= t1 - 0.5]
    if not seg:
        seg = buckets[:1]
    if not seg:
        return None
    classes = [classify(b) for b in seg]
    dom = max(set(classes), key=classes.count)
    return {"camera": dom,
            "motion": round(float(np.mean([b["mag"] for b in seg])), 2),
            "jitter": round(float(np.mean([b["jitter"] for b in seg])), 2)}

# ---------------------------------------------------------------- 被写体中心（562候補）

def subject_center(path, tmid):
    """中央フレームの鮮鋭度エネルギー重心。★近似の一次フィルタ。採否は必ず実画目視。"""
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{tmid:.2f}", "-i", path,
                        "-frames:v", "1", "-vf", "scale=180:320", "-pix_fmt", "gray",
                        "-f", "rawvideo", "-"], capture_output=True).stdout
    if len(p) < 180 * 320:
        return None
    f = np.frombuffer(p[:180 * 320], np.uint8).reshape(320, 180).astype(np.float32)
    gx = np.abs(np.diff(f, axis=1)); gy = np.abs(np.diff(f, axis=0))
    e = gx[:-1, :] + gy[:, :-1]
    e = e ** 2
    tot = e.sum()
    if tot < 1e-3:
        return None
    ys = (e.sum(axis=1) * np.arange(e.shape[0])).sum() / tot / e.shape[0]
    xs = (e.sum(axis=0) * np.arange(e.shape[1])).sum() / tot / e.shape[1]
    return round(float(xs), 3), round(float(ys), 3)

def clip_path(prod, clip):
    for ext in (".MP4", ".MOV", ".mp4", ".mov"):
        p = os.path.join(SRC, prod, clip + ext)
        if os.path.exists(p):
            return p
    return None

# ---------------------------------------------------------------- main

def main():
    cam = json.load(open(CAM))
    con = sqlite3.connect(DB)
    cols = "win, product, key, t0, t1, dur, shot_size, white_max, sharp_med, bright_med, person_count"
    rows = [dict(zip(cols.replace(" ", "").split(","), r)) for r in con.execute(
        f"SELECT {cols} FROM asset_windows_v2 WHERE product NOT LIKE '%_dup_%'")]
    print(f"windows={len(rows)}")

    # --- 1) clip_profiles.json（配布物・数値とカメラ分類のみ）
    profiles = {}
    n_b = 0
    for prod, clips in cam.items():
        profiles[prod] = {}
        for clip, buckets in clips.items():
            profiles[prod][clip] = [
                {"t": b["t"], "camera": classify(b), "motion": b["mag"],
                 "jitter": b["jitter"], "white": b["white"], "bright": b["bright"],
                 "sharp": b["sharp"]} for b in buckets]
            n_b += len(buckets)
    print(f"clip_profiles: {n_b} buckets")

    # --- 窓ごとのカメラ集約（alternatives 用）
    for r in rows:
        clip = r["key"][len(r["product"]) + 1:]
        b = cam.get(r["product"], {}).get(clip)
        r.update(summarize_window(b, r["t0"], r["t1"]) or
                 {"camera": None, "motion": None, "jitter": None})

    # --- 2) alternatives.json
    s34 = json.load(open(os.path.join(ROOT, "data/design/s34_FINAL3.json")))
    bywin = {r["win"]: r for r in rows}

    def expand(c):
        """候補→構成窓のリスト。★562候補中416件は `#w0008-w0010` の連続窓の範囲表記。
        単一窓しか引かないと候補プールの26%しか見ないことになる（実際に踏んだ）。"""
        w = c.get("win")
        if not w:
            return []
        if w in bywin:
            return [bywin[w]]
        if "#w" in w and "-w" in w:
            key, rng = w.rsplit("#", 1)
            a, b = rng.split("-")
            lo, hi = int(a[1:]), int(b[1:])
            return [bywin[f"{key}#w{i:04d}"] for i in range(lo, hi + 1)
                    if f"{key}#w{i:04d}" in bywin]
        return []
    alternatives = {"_note":
        "★修正指示への即応表（発注側の退避DBと原本実測から事前計算・2026-08-11）。"
        "各スロットの候補(s34)を軸別に並べ直したもの＋商材全体の極値リスト。"
        "行が持つのは win/t0/t1/尺/軸の値 だけ。★どの行も採用前に必ず実画を目視する。"
        "camera の方向は『画面内の被写体が流れる向き』（カメラの向きはその逆）。"
        "subject_center は鮮鋭度エネルギー重心による近似の一次フィルタ",
        "products": {}}

    def slim(r, extra=()):
        d = {"win": r["win"], "t0": r["t0"], "t1": r["t1"], "dur": r["dur"]}
        for k in extra:
            d[k] = r.get(k)
        return d

    for prod, pv in s34["products"].items():
        prows = [r for r in rows if r["product"] == prod]
        slots_out = []
        for s in pv["slots"]:
            cands = [r for c in s["candidates"] for r in expand(c)]
            uniq = list({r["win"]: r for r in cands}.values())
            axes = {}
            # ★白飛び0の同値が多いので、同値なら長尺を先に（使い勝手で並べる）
            axes["白飛び回避"] = [slim(r, ("white_max",)) for r in
                sorted(uniq, key=lambda r: (r["white_max"] is None,
                                            r["white_max"], -r["dur"]))[:5]]
            axes["動き最大"] = [slim(r, ("motion", "camera")) for r in
                sorted(uniq, key=lambda r: -(r["motion"] or 0))[:5]]
            axes["安定・静止"] = [slim(r, ("motion", "jitter", "camera")) for r in
                sorted(uniq, key=lambda r: ((r["jitter"] or 9) + (r["motion"] or 9)))[:5]]
            axes["寄り"] = [slim(r, ("shot_size",)) for r in uniq
                            if r["shot_size"] in ("close", "closeup")][:5]
            axes["引き"] = [slim(r, ("shot_size",)) for r in uniq
                            if r["shot_size"] in ("wide", "full")][:5]
            axes["人物なし"] = [slim(r, ("person_count",)) for r in uniq
                                if (r["person_count"] or 0) == 0][:5]
            cam_axes = {}
            for cls in ("zoom_in", "zoom_out", "pan_left", "pan_right",
                        "pan_up", "pan_down", "handheld", "static"):
                hit = [slim(r, ("motion", "jitter")) for r in uniq if r["camera"] == cls]
                if hit:
                    cam_axes[cls] = hit[:5]
            axes["カメラワーク種類別"] = cam_axes
            slots_out.append({"slot": s["slot"], "telop": s["telop"], "axes": axes})

        ext = {
            "動き最大_top10": [slim(r, ("motion", "camera")) for r in
                sorted(prows, key=lambda r: -(r["motion"] or 0))[:10]],
            "完全静止_top10": [slim(r, ("motion", "jitter")) for r in
                sorted(prows, key=lambda r: ((r["motion"] or 9) + (r["jitter"] or 9)))[:10]],
            "白飛びゼロで長尺_top10": [slim(r, ("white_max",)) for r in
                sorted([r for r in prows if (r["white_max"] or 1) < 0.001],
                       key=lambda r: -r["dur"])[:10]],
        }
        for cls in ("zoom_in", "zoom_out", "pan_left", "pan_right", "handheld"):
            hit = sorted([r for r in prows if r["camera"] == cls],
                         key=lambda r: -(r["motion"] or 0))[:8]
            if hit:
                ext[f"camera_{cls}_top"] = [slim(r, ("motion", "jitter")) for r in hit]
        alternatives["products"][prod] = {"slots": slots_out, "product_wide": ext}

    # --- 3) 被写体中心（s34 の候補窓のみ・562件）
    print("被写体中心を計算中（562候補）…", flush=True)
    done = 0
    for prod, pv in s34["products"].items():
        for s in pv["slots"]:
            for c in s["candidates"]:
                for r in expand(c):
                    if "subject_center" in r:
                        continue
                    clip = r["key"][len(prod) + 1:]
                    path = clip_path(prod, clip)
                    if not path:
                        continue
                    sc = subject_center(path, (r["t0"] + r["t1"]) / 2)
                    if sc:
                        r["subject_center"] = {"x_pct": sc[0], "y_pct": sc[1]}
                    done += 1
                    if done % 100 == 0:
                        print(f"  {done}", flush=True)
    # alternatives の各行に subject_center を追記
    for prod, pv in alternatives["products"].items():
        for s in pv["slots"]:
            for ax, items in s["axes"].items():
                seq = items.values() if isinstance(items, dict) else [items]
                for lst in seq:
                    for it in lst:
                        sc = bywin.get(it["win"], {}).get("subject_center")
                        if sc:
                            it["subject_center"] = sc

    os.makedirs(os.path.join(ROOT, "data/revision_aids"), exist_ok=True)
    json.dump({"_note":
        "★原本188本×1秒粒度の数値プロファイル（発注側の実測から事前計算）。"
        "camera: static/pan_*/zoom_*/handheld/drift。方向は画面内の流れ。"
        "motion=平均の動き量[px/f @160x120]・jitter=ぶれ・white=輝度250以上の画素比。"
        "★候補表(alternatives.json)の外を探すときの粗い地図。採否は必ず実画目視",
        "clips": profiles},
        open(os.path.join(ROOT, "data/revision_aids/clip_profiles.json"), "w"),
        ensure_ascii=False)
    json.dump(alternatives,
        open(os.path.join(ROOT, "data/revision_aids/alternatives.json"), "w"),
        ensure_ascii=False, indent=1)
    print("done: data/revision_aids/{clip_profiles,alternatives}.json")

    # --- 検算用にカメラ分類の分布を出す
    from collections import Counter
    dist = Counter(r["camera"] for r in rows if r["camera"])
    print("窓のカメラ分類分布:", dict(dist))

if __name__ == "__main__":
    main()
