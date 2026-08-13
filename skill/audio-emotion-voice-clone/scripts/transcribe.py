#!/usr/bin/env python3
"""Transcribe Japanese (or other language) audio with word-level timestamps using faster-whisper.

Usage:
    python3 transcribe.py audio.wav transcript.json [--language ja] [--model large-v3]
        [--compute-type float32] [--initial-prompt "domain vocab, hints"]

Notes (learned 2026-07-01):
- `medium` model + int8 quantization degrades badly on audio with heavy domain-specific
  vocabulary or slang. Prefer `large-v3` + `float32` for accuracy-critical work.
- `initial_prompt` biases decoding toward expected vocabulary (proper nouns, jargon) and
  measurably helps.
- `condition_on_previous_text=False` avoids hallucination cascades where one bad segment
  corrupts all following segments.
- Perfect transcription is often not required if the actual goal is prosody/emotion
  extraction rather than exact wording — don't over-invest in re-running bigger models
  if the segment timing and rough text is good enough for downstream acoustic analysis.
"""
import argparse
import json
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio", help="input audio file (wav recommended)")
    ap.add_argument("output_json", help="path to write segments json")
    ap.add_argument("--language", default="ja")
    ap.add_argument("--model", default="large-v3",
                    help="faster-whisper model size, e.g. medium, large-v3, large-v3-turbo")
    ap.add_argument("--compute-type", default="float32", help="int8 is faster/less accurate; float32 is slower/more accurate")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--initial-prompt", default=None, help="domain vocabulary hint string")
    ap.add_argument("--no-vad", action="store_true", help="disable VAD filter")
    args = ap.parse_args()

    from faster_whisper import WhisperModel

    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)

    segments, info = model.transcribe(
        args.audio,
        language=args.language,
        word_timestamps=True,
        vad_filter=not args.no_vad,
        beam_size=5,
        best_of=5,
        condition_on_previous_text=False,
        initial_prompt=args.initial_prompt,
    )

    result = []
    for seg in segments:
        result.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
            "words": [{"word": w.word, "start": w.start, "end": w.end} for w in (seg.words or [])],
        })
        print(f"[{seg.start:.2f}-{seg.end:.2f}] {seg.text.strip()}", file=sys.stderr)

    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
