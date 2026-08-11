#!/usr/bin/env python3
"""機械検査: 完成動画を全フレーム走査する（サンプリング禁止）。

検査項目（video_profile.json の閾値を使う）:
  1. 尺が設計値と一致（±1フレーム）
  2. 黒フレーム 0件
  3. 孤立フレーム（2フレーム以内で戻るカット）0件
  4. silence_limit_sec 以上の無音 0件
  5. 音声と映像の尺差 0.000秒
  6. 画が実質変わっていない連続秒数が no_change_limit_sec を超える区間の列挙
     → 合否ではなく Phase 4（テンポ5段階判定）の入力。ここで「良い/悪い」は判定しない
     ★限界: この検出は「ほぼ静止した画」しか拾えない。手持ちカメラの微動・歩き撮りでは
       画素差分が出るため、知覚的な「同じ画の繰り返し」（別カットだが見た目が同じ等）は
       検出できない。知覚的な同一性の検出は G21（Codexの全フレーム観察）の仕事であり、
       このスクリプトの0件をもって「同じ画が続いていない」と報告してはならない。

★このスクリプトは「壊れていない」を証明するだけで「良い」は証明しない。
  全項目0件でも、テンポ判定・Codexレビュー・合議採点を通るまで検品通過ではない。

使い方:
  python3 qc_machine.py <mp4> <設計尺(秒)> [--profile qc/video_profile.json] [--out qc/machine_report.json]
"""

# --- VIDEO OPS ライセンスゲート（仕様§4.2・ローカル読取のみ・ネットワークなし） ---
def _vops_require(_feat):
    import sys as _s
    from pathlib import Path as _P
    _h = _P(__file__).resolve()
    _cands = [q for p in _h.parents for q in (p / "ops" / "license", p / "core" / "ops" / "license")]
    _cands.append(_P.home() / ".claude" / "skills" / "_video-core" / "ops" / "license")
    for _c in _cands:
        if (_c / "vops_license.py").exists():
            _s.path.insert(0, str(_c))
            import vops_license as _v
            _v.require(_feat)
            return
    print("⚠ VIDEO OPS: ライセンス機構が見つからない（導通不備）— 続行", file=_s.stderr)


_vops_require("qc")
# --- ゲートここまで ---
import sys, json, subprocess, argparse, os
import numpy as np

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mp4")
    ap.add_argument("design_duration", type=float)
    ap.add_argument("--profile", default="qc/video_profile.json")
    ap.add_argument("--out", default="qc/machine_report.json")
    a = ap.parse_args()

    prof = {"no_change_limit_sec": 2.5, "silence_limit_sec": 0.25}
    if os.path.exists(a.profile):
        prof.update(json.load(open(a.profile, encoding="utf-8")))

    W, H = 96, 170
    probe = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=nb_frames,r_frame_rate",
         "-show_entries", "format=duration", "-of", "json", a.mp4],
        capture_output=True, text=True).stdout)
    dur = float(probe["format"]["duration"])
    nb = int(probe["streams"][0]["nb_frames"])
    num, den = probe["streams"][0]["r_frame_rate"].split("/")
    fps = float(num) / float(den)

    # ---- 全フレームを縮小して吸い出す（全数。サンプリングしない）----
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", a.mp4,
         "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
        capture_output=True).stdout
    n = len(raw) // (W * H)
    Y = np.frombuffer(raw[:n*W*H], dtype=np.uint8).reshape(n, H, W).astype(np.float32)
    mean = Y.mean(axis=(1, 2))

    black = [{"frame": i, "t": round(i/fps, 3), "luma": round(float(mean[i]), 1)}
             for i in range(n) if mean[i] < 16]

    # フレーム間差分（カット検出と「画が変わらない」検出の両方に使う）
    diff = np.abs(np.diff(Y, axis=0)).mean(axis=(1, 2))  # フレーム間の平均画素差（★axis=0＝時間方向。軸を誤ると画素方向を差分してしまう）
    cuts = [i+1 for i in range(len(diff)) if abs(mean[i+1]-mean[i]) > 12]
    isolated = [{"frame": x, "t": round(x/fps, 3)}
                for x, y in zip(cuts, cuts[1:]) if y - x <= 2]

    # 画が実質変わっていない連続区間（差分が小さいフレームの連なり）
    NO_CHANGE_DIFF = 1.6      # 平均画素差がこの値未満なら「変わっていない」
    limit = prof["no_change_limit_sec"]
    no_change, run = [], None
    for i in range(len(diff)):
        if diff[i] < NO_CHANGE_DIFF:
            if run is None:
                run = i
        else:
            if run is not None and (i - run) / fps >= limit:
                no_change.append({"start": round(run/fps, 3), "end": round(i/fps, 3),
                                  "sec": round((i-run)/fps, 3)})
            run = None
    if run is not None and (len(diff) - run) / fps >= limit:
        no_change.append({"start": round(run/fps, 3), "end": round(len(diff)/fps, 3),
                          "sec": round((len(diff)-run)/fps, 3)})

    # ---- 音声 ----
    wav = subprocess.run(["ffmpeg", "-v", "error", "-i", a.mp4,
                          "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    audio = np.frombuffer(wav, dtype=np.int16).astype(np.float32) / 32768.0
    HOP = int(16000 * 0.002)
    env = np.array([np.abs(audio[i*HOP:(i+1)*HOP]).max() for i in range(len(audio)//HOP)])
    db = 20 * np.log10(np.maximum(env, 1e-6))    # ★線形振幅→dB。単位の取り違えで27件誤検出した過去がある
    # ★2026-07-29 修正: 2msごとの瞬間値をそのまま閾値と比べると、クリック音1点で無音が分断される。
    #   18_v3.mov では中央値-49dBの0.67秒の無音が、-40.3dBのピーク1点のせいで「0件」と誤報された
    #   （実音声を独立に測って発覚。工程の基準を通っても完成MP4に欠陥が残る典型例）。
    #   20msの移動中央値で均してから判定する。閾値も-45→-42dBへ（-45だと同じ取りこぼしが残る）。
    SMOOTH = 10                                   # 10点 = 20ms
    if len(db) >= SMOOTH:
        pad = np.pad(db, (SMOOTH // 2, SMOOTH - SMOOTH // 2 - 1), mode="edge")
        db = np.array([np.median(pad[i:i + SMOOTH]) for i in range(len(db))])
    sil, run2, silences = db < -42, None, []
    slim = prof["silence_limit_sec"]
    for k in range(len(sil)):
        if sil[k]:
            if run2 is None:
                run2 = k
        else:
            if run2 is not None and (k - run2) * 0.002 >= slim:
                silences.append({"start": round(run2*0.002, 3), "end": round(k*0.002, 3)})
            run2 = None
    if run2 is not None and (len(sil) - run2) * 0.002 >= slim:
        silences.append({"start": round(run2*0.002, 3), "end": round(len(sil)*0.002, 3)})

    audio_dur = len(audio) / 16000.0
    dur_ok = abs(nb - round(a.design_duration * fps)) <= 1
    av_ok = abs(audio_dur - n / fps) < 0.05

    report = {
        "mp4": a.mp4, "fps": fps,
        "duration": {"actual_sec": round(dur, 3), "frames": nb,
                     "design_sec": a.design_duration, "ok": dur_ok},
        "black_frames": black,
        "isolated_frames": isolated,
        "silences": silences,
        "av_length_diff_sec": round(audio_dur - n/fps, 3), "av_ok": av_ok,
        "no_change_segments": no_change,   # ← 合否ではなくテンポ判定(Phase4)の入力
        "verdict": "PASS" if (dur_ok and not black and not isolated and not silences and av_ok) else "FAIL",
        "note": "PASSは『壊れていない』の証明であり『良い』の証明ではない。no_change_segmentsは全件Phase4へ。",
    }
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(report, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"尺 {dur:.3f}s/{nb}f（設計{a.design_duration}s）: {'OK' if dur_ok else 'FAIL'}")
    print(f"黒フレーム {len(black)}件 / 孤立 {len(isolated)}件 / 無音({slim}s+) {len(silences)}件 / AV差 {audio_dur - n/fps:+.3f}s")
    print(f"画が変わらない区間({limit}s+): {len(no_change)}件 → 全件をテンポ5段階判定へ")
    for s in no_change:
        print(f"   {s['start']:8.3f}〜{s['end']:8.3f} ({s['sec']:.2f}s)")
    sys.exit(0 if report["verdict"] == "PASS" else 1)

if __name__ == "__main__":
    main()
