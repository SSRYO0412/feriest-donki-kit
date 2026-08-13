#!/usr/bin/env python3
"""Generalized voice-clone replication pipeline (speaker-independent).

Distills the winning v9 approach (2026-07-02, see references/prosody_control_playbook.md
"最終的に勝った構成") into a two-step pipeline that works for ANY source voice —
male/female, high/low tension, any dialect:

  Step 1: PLAN — measure the original per segment, auto-derive all targets
    python3 replicate_pipeline.py plan original.wav transcript.json mapping.json

  Step 2 (human/Claude): edit mapping.json — rewrite each line's "text" (keep or
    change wording; keep the orthographic prosody: ! !? っ。 。), adjust "tags"
    only if the auto-suggestion is wrong. DO NOT touch "targets".

  Step 3: RUN — closed-loop generation against the measured targets
    python3 replicate_pipeline.py run mapping.json --key-file .fishkey \
        --reference-id <clone_model_id> --workdir v1_work --output final_v1.mp3 [-K 4]

Design principles baked in (all learned the hard way):
- NO categorical emotion tags by default; the clone reference carries the style.
  Tags are auto-suggested only for statistically extreme registers (quiet-low
  lines, shouted exclamations) and kept minimal.
- Orthography is the primary prosody control (!, !?, っ。, 。).
- Per-line targets (F0 mean, ending slope, duration) come from the ORIGINAL's
  measurements, expressed in speaker-relative units (z-scores), so the same
  scoring works for a 100Hz male mutter and a 400Hz female shout.
- Pitch analysis range is auto-estimated from the original (75-500Hz hardcoding
  breaks on male voices).
- Inter-line gaps replicate the original's measured pause structure (uniform
  gaps read as unnatural "slideshow" pacing).
- Candidates are selected by measurement, not by ear. K=4 default.
- Per-line loudness is matched to the batch median before assembly.
"""
import argparse
import json
import os
import re
import subprocess
import sys

import numpy as np
import parselmouth

HELPER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fish_audio_helper.py")


# ---------- measurement ----------

def adaptive_pitch_range(snd):
    """Estimate the speaker's pitch range so analysis works for any voice."""
    pitch = snd.to_pitch(pitch_floor=50, pitch_ceiling=600)
    f0 = pitch.selected_array["frequency"]
    f0v = f0[f0 > 0]
    if len(f0v) < 10:
        return 75.0, 500.0
    p10, p90 = np.percentile(f0v, 10), np.percentile(f0v, 90)
    return max(50.0, 0.6 * p10), min(600.0, 1.6 * p90)


def measure(snd_or_path, floor, ceiling, t0=None, t1=None):
    snd = snd_or_path if isinstance(snd_or_path, parselmouth.Sound) else parselmouth.Sound(snd_or_path)
    if t0 is not None:
        snd = snd.extract_part(from_time=max(0, t0), to_time=min(snd.duration, t1), preserve_times=True)
    pitch = snd.to_pitch(time_step=0.005, pitch_floor=floor, pitch_ceiling=ceiling)
    f0 = pitch.selected_array["frequency"]
    times = pitch.xs()
    v = f0 > 0
    f0v, tv = f0[v], times[v]
    if len(f0v) < 5:
        return None
    tail = tv >= tv[-1] - 0.20
    slope = float(np.polyfit(tv[tail], f0v[tail], 1)[0]) if tail.sum() > 2 else 0.0
    inten = snd.to_intensity(minimum_pitch=floor)
    iv = inten.values[0]
    iv = iv[~np.isnan(iv)]
    return {
        "f0": float(np.mean(f0v)),
        "range": float(np.percentile(f0v, 90) - np.percentile(f0v, 10)),
        "last_slope": slope,
        "dur": float(snd.duration if t0 is None else (t1 - t0)),
        "int": float(np.mean(iv)) if len(iv) else 0.0,
    }


# ---------- plan ----------

def cmd_plan(args):
    snd = parselmouth.Sound(args.audio)
    floor, ceiling = adaptive_pitch_range(snd)
    print(f"speaker pitch range (auto): {floor:.0f}-{ceiling:.0f}Hz")

    with open(args.transcript, encoding="utf-8") as f:
        segs = json.load(f)

    lines = []
    for i, seg in enumerate(segs):
        m = measure(snd, floor, ceiling, seg["start"], seg["end"])
        gap = max(0.0, round(segs[i + 1]["start"] - seg["end"], 2)) if i < len(segs) - 1 else 0.0
        lines.append({
            "idx": i,
            "orig_text": seg["text"],
            "text": seg["text"],  # edit me: rewrite wording, keep orthographic prosody
            "tags": "",           # auto-filled below for extreme registers only
            "targets": m,
            "gap_after": gap,
        })

    valid = [l for l in lines if l["targets"]]
    f0s = np.array([l["targets"]["f0"] for l in valid])
    slopes = np.array([l["targets"]["last_slope"] for l in valid])
    speaker = {
        "pitch_floor": floor, "pitch_ceiling": ceiling,
        "f0_median": float(np.median(f0s)), "f0_std": float(max(np.std(f0s), 15.0)),
        "slope_std": float(max(np.std(slopes), 300.0)),
    }

    # conservative auto-tags for statistically extreme registers only
    for l in valid:
        t = l["targets"]
        z = (t["f0"] - speaker["f0_median"]) / speaker["f0_std"]
        if z < -1.2:
            l["tags"] = "[low quiet voice] "
        elif z > 0.8 and t["dur"] < 1.0 and ("!" in l["orig_text"] or "！" in l["orig_text"]):
            l["tags"] = "[shouting] "

    with open(args.mapping, "w", encoding="utf-8") as f:
        json.dump({"speaker": speaker, "lines": lines}, f, ensure_ascii=False, indent=2)

    print(f"{'idx':>3} {'F0':>5} {'zF0':>5} {'slope':>7} {'dur':>5} {'gap':>5}  tags / text")
    for l in lines:
        t = l["targets"]
        if not t:
            print(f"{l['idx']:>3}  (no voiced data)  {l['orig_text'][:30]}")
            continue
        z = (t["f0"] - speaker["f0_median"]) / speaker["f0_std"]
        print(f"{l['idx']:>3} {t['f0']:>5.0f} {z:>+5.1f} {t['last_slope']:>+7.0f} {t['dur']:>5.2f} {l['gap_after']:>5.2f}  {l['tags']}{l['orig_text'][:28]}")
    print(f"\nwrote {args.mapping} — now edit each line's \"text\" (and only if needed, \"tags\"), then run.")


# ---------- run ----------

def cmd_run(args):
    with open(args.mapping, encoding="utf-8") as f:
        mapping = json.load(f)
    sp = mapping["speaker"]
    floor, ceiling = sp["pitch_floor"], sp["pitch_ceiling"]
    lines = [l for l in mapping["lines"] if l["targets"]]
    os.makedirs(args.workdir, exist_ok=True)

    def gen(text, out):
        subprocess.run([sys.executable, HELPER, "tts", "--key-file", args.key_file,
                        "--reference-id", args.reference_id, "--text", text,
                        "--output", out, "--model", args.model], capture_output=True)

    picks, gaps, report = [], [], []
    for l in lines:
        t = l["targets"]
        full_text = (l.get("tags") or "") + l["text"]
        cands = []
        for k in range(args.K):
            out = os.path.join(args.workdir, f"L{l['idx']:02d}_{k}.mp3")
            gen(full_text, out)
            m = measure(out, floor, ceiling) if os.path.exists(out) else None
            if not m:
                continue
            z_f0 = abs(m["f0"] - t["f0"]) / sp["f0_std"]
            z_slope = abs(m["last_slope"] - t["last_slope"]) / sp["slope_std"]
            z_dur = abs(m["dur"] - t["dur"]) / max(0.3, 0.25 * t["dur"])
            range_bonus = 0.3 * min(m["range"] / max(t["range"], 1.0), 1.5)
            score = z_f0 + z_slope + z_dur - range_bonus
            cands.append((score, out, m))
        if not cands:
            print(f"L{l['idx']:02d}: ALL {args.K} CANDIDATES FAILED (API error?)")
            continue
        cands.sort(key=lambda x: x[0])
        s, path, m = cands[0]
        picks.append(path)
        gaps.append(l["gap_after"])
        flag = "OK" if s < 2.0 else "WEAK"
        report.append((l["idx"], m, t, s, flag))
        print(f"L{l['idx']:02d}: f0={m['f0']:.0f}(tgt {t['f0']:.0f}) slope={m['last_slope']:+.0f}(tgt {t['last_slope']:+.0f}) "
              f"dur={m['dur']:.2f}(tgt {t['dur']:.2f}) score={s:.2f} {flag}")

    # loudness match to batch median
    ints = [measure(p, floor, ceiling)["int"] for p in picks]
    target_int = float(np.median(ints))
    norm_paths = []
    for i, (p, cur) in enumerate(zip(picks, ints)):
        outp = os.path.join(args.workdir, f"norm_{i:02d}.mp3")
        subprocess.run(["ffmpeg", "-y", "-i", p, "-af", f"volume={target_int - cur:.1f}dB",
                        "-codec:a", "libmp3lame", "-b:a", "128k", outp], capture_output=True)
        norm_paths.append(outp)

    # assemble with original-faithful gaps
    entries = []
    for i, (p, gap) in enumerate(zip(norm_paths, gaps)):
        entries.append(f"file '{os.path.abspath(p)}'")
        if gap > 0.02 and i < len(norm_paths) - 1:
            gp = os.path.join(args.workdir, f"gap_{i:02d}.mp3")
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                            "-t", f"{min(gap, 1.5)}", "-codec:a", "libmp3lame", "-b:a", "128k", gp],
                           capture_output=True)
            entries.append(f"file '{os.path.abspath(gp)}'")
    concat_file = os.path.join(args.workdir, "concat.txt")
    with open(concat_file, "w") as f:
        f.write("\n".join(entries) + "\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
                    "-c", "copy", args.output], capture_output=True)

    weak = [r for r in report if r[4] == "WEAK"]
    print(f"\nwrote {args.output}")
    if weak:
        print(f"WEAK lines (no candidate matched targets well — retry with more K or tweak text/tags): "
              f"{', '.join('L%02d' % r[0] for r in weak)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan", help="measure original, produce editable mapping.json")
    p.add_argument("audio"); p.add_argument("transcript"); p.add_argument("mapping")
    p.set_defaults(func=cmd_plan)

    r = sub.add_parser("run", help="closed-loop generate, select, assemble")
    r.add_argument("mapping")
    r.add_argument("--key-file", required=True)
    r.add_argument("--reference-id", required=True)
    r.add_argument("--workdir", required=True, help="candidate/work dir (versioned, never overwrite old runs)")
    r.add_argument("--output", required=True)
    r.add_argument("-K", type=int, default=4, help="candidates per line")
    r.add_argument("--model", default="s2.1-pro-free")
    r.set_defaults(func=cmd_run)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
