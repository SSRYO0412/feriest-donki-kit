#!/usr/bin/env python3
"""Render a 3-panel prosody/emotion chart: F0 contour, intensity contour,
and per-segment arousal z-score bars (red = high-arousal, blue = low-arousal).

Usage:
    python3 plot_prosody.py audio.wav deep_acoustic_analysis.json out.png

Always Read the resulting PNG yourself before drawing conclusions — the numeric
table alone tends to hide the "breathing pattern" (dips right before a hook, etc).
"""
import argparse
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import parselmouth


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("analysis_json")
    ap.add_argument("output_png")
    args = ap.parse_args()

    snd = parselmouth.Sound(args.audio)
    pitch = snd.to_pitch(time_step=0.01, pitch_floor=75, pitch_ceiling=500)
    f0 = pitch.selected_array["frequency"]
    f0[f0 == 0] = np.nan
    times = pitch.xs()

    intensity = snd.to_intensity(minimum_pitch=75)
    int_times = intensity.xs()
    int_vals = intensity.values[0]

    with open(args.analysis_json, encoding="utf-8") as f:
        data = json.load(f)
    segs = data["segments"]

    fig, axes = plt.subplots(3, 1, figsize=(16, 10), sharex=True)

    axes[0].plot(times, f0, color="tab:blue", linewidth=1)
    axes[0].set_ylabel("F0 (Hz)")
    axes[0].set_title("Pitch contour (F0)")

    axes[1].plot(int_times, int_vals, color="tab:orange", linewidth=1)
    axes[1].set_ylabel("Intensity (dB)")
    axes[1].set_title("Intensity contour")

    arousal = [s["arousal_score"] for s in segs]
    mid_times = [(s["start"] + s["end"]) / 2 for s in segs]
    colors = ["crimson" if a > 0.6 else ("steelblue" if a < -0.6 else "gray") for a in arousal]
    axes[2].bar(mid_times, arousal, width=[s["duration"] * 0.9 for s in segs], color=colors)
    axes[2].axhline(0.6, color="crimson", linestyle="--", linewidth=0.5)
    axes[2].axhline(-0.6, color="steelblue", linestyle="--", linewidth=0.5)
    axes[2].set_ylabel("Arousal z-score")
    axes[2].set_title("Segment-level arousal (red=high-arousal/excited, blue=low-arousal/calm)")
    axes[2].set_xlabel("Time (s)")

    for ax in axes:
        for s in segs:
            ax.axvline(s["start"], color="lightgray", linewidth=0.4)

    plt.tight_layout()
    plt.savefig(args.output_png, dpi=130)
    print(f"saved {args.output_png}")


if __name__ == "__main__":
    main()
