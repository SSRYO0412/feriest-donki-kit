#!/usr/bin/env python3
"""Fish Audio API helper: create a voice-clone model and generate TTS with it.

Reads the API key from a local file (never pass it on the CLI or paste it in chat —
see references/fish_audio_notes.md for the recommended Keychain/local-file pattern).

Usage:
    # 1. Create a private clone model from a reference audio clip (10-30s, clean/no BGM ideally)
    python3 fish_audio_helper.py create-model \\
        --key-file .fishkey --audio reference_clip.mp3 \\
        --text "<verbatim transcript of the reference clip>" \\
        --title my_clone_v1
    # -> prints the model _id (use as --reference-id below)

    # 2. Generate speech with that cloned voice, using inline [tag] emotion markup
    python3 fish_audio_helper.py tts \\
        --key-file .fishkey --reference-id <model_id> \\
        --text-file script_tagged.txt --output out.mp3

Known gotcha (2026-07-01): the inline zero-shot `references` field (passing a
base64 audio clip + transcript directly in the /v1/tts request body) returned
"Reference Audio is not valid" consistently in testing, regardless of format
(wav/mp3), encoding (plain base64 / data URI), clip length (10s/20s), or even
when the reference audio was itself Fish-Audio-generated. The reliable path is
always: POST /model (multipart) to create a persistent private clone, then use
its _id as reference_id in /v1/tts. Model creation with train_mode=fast returns
state=trained immediately (no training wait).
"""
import argparse
import sys
import requests


def load_key(key_file):
    with open(key_file) as f:
        return f.read().strip()


def create_model(args):
    key = load_key(args.key_file)
    with open(args.audio, "rb") as f:
        files = {"voices": (args.audio, f, "audio/mpeg")}
        data = {
            "type": "tts",
            "title": args.title,
            "train_mode": "fast",
            "texts": args.text,
            "visibility": "private",
            "enhance_audio_quality": "true",
        }
        resp = requests.post(
            "https://api.fish.audio/model",
            headers={"Authorization": f"Bearer {key}"},
            files=files,
            data=data,
            timeout=60,
        )
    resp.raise_for_status()
    body = resp.json()
    print(f"model_id={body['_id']} state={body.get('state')}")
    return body["_id"]


def tts(args):
    key = load_key(args.key_file)
    if args.text_file:
        with open(args.text_file, encoding="utf-8") as f:
            text = f.read()
    else:
        text = args.text

    body = {"text": text, "format": args.format}
    if args.reference_id:
        body["reference_id"] = args.reference_id

    resp = requests.post(
        "https://api.fish.audio/v1/tts",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "model": args.model,
        },
        json=body,
        timeout=180,
    )
    if resp.status_code != 200:
        print(f"ERROR {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)
    with open(args.output, "wb") as f:
        f.write(resp.content)
    print(f"wrote {args.output} ({len(resp.content)} bytes)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_create = sub.add_parser("create-model")
    p_create.add_argument("--key-file", required=True)
    p_create.add_argument("--audio", required=True, help="reference clip, mp3 recommended, 10-30s")
    p_create.add_argument("--text", required=True, help="verbatim transcript of the reference clip")
    p_create.add_argument("--title", required=True)
    p_create.set_defaults(func=create_model)

    p_tts = sub.add_parser("tts")
    p_tts.add_argument("--key-file", required=True)
    p_tts.add_argument("--reference-id", default=None, help="model id from create-model, or a public voice id")
    p_tts.add_argument("--text", default=None)
    p_tts.add_argument("--text-file", default=None, help="file containing [tag]-annotated script")
    p_tts.add_argument("--output", required=True)
    p_tts.add_argument("--format", default="mp3")
    p_tts.add_argument("--model", default="s2.1-pro-free")
    p_tts.set_defaults(func=tts)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
