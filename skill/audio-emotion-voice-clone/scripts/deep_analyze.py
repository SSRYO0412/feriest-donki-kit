#!/usr/bin/env python3
"""Precise Praat-based acoustic analysis with corpus-relative z-scoring and
arousal/tension emotion scoring, per transcript segment.

Usage:
    python3 deep_analyze.py audio.wav transcript.json analysis_output.json

Input transcript.json format: list of {"start": float, "end": float, "text": str, ...}
(as produced by transcribe.py)

Design notes (learned 2026-07-01):
- Praat/parselmouth gives precise acoustic MEASUREMENTS (F0, intensity, jitter, shimmer).
  It does NOT give emotion labels by itself — that interpretation layer has to be built
  on top. This script builds that layer via z-scores against the corpus (the audio's own
  mean/std), not fixed absolute thresholds. Fixed thresholds hide the "breathing pattern"
  of the emotional arc (e.g. a dip right before a hook, i.e. the "tame" / anticipation
  beat) — z-scoring against the corpus mean makes that visible.
- Arousal score approximates the well-established prosody-emotion association (Banse &
  Scherer, and general affective-prosody literature): higher pitch range/height, higher
  intensity, faster speech rate, and stronger pitch movement/slope correlate with higher
  arousal (excitement, urgency, surprise). Lower values correlate with calm/flat delivery.
- Tension score uses jitter/shimmer (vocal-fold irregularity) as a proxy for vocal strain
  associated with anger/stress — these are physical voice-quality measures, not a trained
  classifier, so treat the resulting labels as an interpretable heuristic, not a certified
  emotion classification.
"""
import argparse
import json
import numpy as np
import parselmouth
from parselmouth.praat import call


def segment_stats(snd, start, end):
    start_c = max(0, start)
    end_c = min(snd.duration, end)
    sub = snd.extract_part(from_time=start_c, to_time=end_c, preserve_times=True)

    pitch = sub.to_pitch(pitch_floor=75, pitch_ceiling=500)
    f0 = pitch.selected_array["frequency"]
    times = pitch.xs()
    voiced_mask = f0 > 0
    f0v = f0[voiced_mask]
    tv = times[voiced_mask]

    intensity = sub.to_intensity(minimum_pitch=75)
    intens_vals = intensity.values[0]
    intens_vals = intens_vals[~np.isnan(intens_vals)]

    try:
        point_process = call(sub, "To PointProcess (periodic, cc)", 75, 500)
        jitter_local = call(point_process, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
        shimmer_local = call([sub, point_process], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
    except Exception:
        jitter_local = float("nan")
        shimmer_local = float("nan")

    if len(f0v) >= 2:
        f0_mean = float(np.mean(f0v))
        f0_range = float(np.max(f0v) - np.min(f0v))
        f0_std = float(np.std(f0v))
        slope = float(np.polyfit(tv, f0v, 1)[0])
    else:
        f0_mean = f0_range = f0_std = slope = 0.0

    intens_mean = float(np.mean(intens_vals)) if len(intens_vals) else 0.0
    intens_range = float(np.max(intens_vals) - np.min(intens_vals)) if len(intens_vals) else 0.0

    return {
        "f0_mean_hz": round(f0_mean, 1),
        "f0_range_hz": round(f0_range, 1),
        "f0_std_hz": round(f0_std, 1),
        "f0_slope_hz_s": round(slope, 1),
        "intensity_mean_db": round(intens_mean, 1),
        "intensity_range_db": round(intens_range, 1),
        "jitter_pct": round(jitter_local * 100, 2) if jitter_local == jitter_local else None,
        "shimmer_pct": round(shimmer_local * 100, 2) if shimmer_local == shimmer_local else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("transcript_json")
    ap.add_argument("output_json")
    args = ap.parse_args()

    snd = parselmouth.Sound(args.audio)
    with open(args.transcript_json, encoding="utf-8") as f:
        segments = json.load(f)

    results = []
    for i, seg in enumerate(segments):
        dur = seg["end"] - seg["start"]
        n_chars = len(seg["text"].replace(" ", "").replace("、", "").replace("。", ""))
        speech_rate = round(n_chars / dur, 2) if dur > 0 else 0
        prev_end = segments[i - 1]["end"] if i > 0 else None
        next_start = segments[i + 1]["start"] if i < len(segments) - 1 else None
        stats = segment_stats(snd, seg["start"], seg["end"])
        stats.update({
            "idx": i,
            "text": seg["text"],
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "duration": round(dur, 2),
            "chars_per_sec": speech_rate,
            "pause_before_s": round(max(0, seg["start"] - prev_end), 2) if prev_end is not None else None,
            "pause_after_s": round(max(0, next_start - seg["end"]), 2) if next_start is not None else None,
        })
        results.append(stats)

    def col(name):
        return np.array([r[name] for r in results if r[name] is not None])

    means, stds = {}, {}
    for feat in ["f0_mean_hz", "f0_range_hz", "f0_slope_hz_s", "intensity_mean_db",
                 "jitter_pct", "shimmer_pct", "chars_per_sec"]:
        c = col(feat)
        means[feat] = float(np.mean(c)) if len(c) else 0.0
        stds[feat] = float(np.std(c)) if len(c) and np.std(c) > 0 else 1.0

    def z(feat, val):
        if val is None:
            return 0.0
        return (val - means[feat]) / stds[feat]

    for r in results:
        r["z_f0_mean"] = round(z("f0_mean_hz", r["f0_mean_hz"]), 2)
        r["z_f0_range"] = round(z("f0_range_hz", r["f0_range_hz"]), 2)
        r["z_f0_slope"] = round(z("f0_slope_hz_s", r["f0_slope_hz_s"]), 2)
        r["z_intensity"] = round(z("intensity_mean_db", r["intensity_mean_db"]), 2)
        r["z_jitter"] = round(z("jitter_pct", r["jitter_pct"]), 2) if r["jitter_pct"] is not None else 0.0
        r["z_shimmer"] = round(z("shimmer_pct", r["shimmer_pct"]), 2) if r["shimmer_pct"] is not None else 0.0
        r["z_rate"] = round(z("chars_per_sec", r["chars_per_sec"]), 2)

        arousal = r["z_f0_range"] * 0.3 + r["z_intensity"] * 0.3 + r["z_rate"] * 0.25 + abs(r["z_f0_slope"]) * 0.15
        tension = r["z_jitter"] * 0.5 + r["z_shimmer"] * 0.5
        r["arousal_score"] = round(arousal, 2)
        r["tension_score"] = round(tension, 2)

        if arousal > 0.6:
            label = "high-arousal (excited/urgent)"
        elif arousal < -0.6:
            label = "low-arousal (calm/flat)"
        else:
            label = "mid-arousal (neutral/explain)"
        if tension > 0.8:
            label += " + tense"
        r["emotion_label"] = label

    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump({"segments": results, "corpus_means": means, "corpus_stds": stds}, f, ensure_ascii=False, indent=2)

    print(f"{'idx':>3} {'time':>12} {'arousal':>7} {'tension':>7}  label / text")
    for r in results:
        print(f"{r['idx']:>3} {r['start']:>5.1f}-{r['end']:>5.1f} {r['arousal_score']:>7.2f} "
              f"{r['tension_score']:>7.2f}  {r['emotion_label']:<28} {r['text'][:24]}")


if __name__ == "__main__":
    main()
