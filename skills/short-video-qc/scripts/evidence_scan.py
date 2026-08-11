#!/usr/bin/env python3
"""捏造検出: セッション記録（JSONL transcript）から「実際にReadした画像」を機械抽出し、
seen申告（claude_seen.json / slots.json / ラベル等）と突合する。

なぜ要るか:
  「切り出した枚数」をスクリプトが出力し、それを「見た枚数」として記録する——という
  観察の捏造が実際に起きた（39枚切り出し18枚しか見ずに「全数目視」と記録）。
  証跡を申告からではなくツール実行記録から取ることで、嘘を書いても通らなくする。

使い方:
  python3 evidence_scan.py <transcript.jsonl> [--claim <申告jsonのパス>...] [--out qc/evidence_report.json]

  申告jsonの形式は柔軟に対応:
    - {"seen": [paths]} 形式
    - slots.json（candidates[].seen を再帰的に収集）
    - 任意のjson（"seen" キーを再帰探索）

判定:
  申告にあるのに実Readが無いパス（＝捏造疑い）が1件でもあれば exit 1。
"""
import sys, json, re, os, argparse

def read_images_from_transcript(path):
    """JSONL から Read ツールで実際に読んだ画像パスを抽出する"""
    reads = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if '"Read"' not in line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            msg = d.get("message") or {}
            for c in (msg.get("content") or []):
                if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Read":
                    p = (c.get("input") or {}).get("file_path", "")
                    if re.search(r"\.(jpg|jpeg|png|webp)$", p, re.I):
                        reads.append(p)
    return reads

def collect_seen(obj, acc):
    """任意のjsonから seen / seen_claude キーの値（パスのリスト）を再帰収集。
    ★seen_codex は Claude の実Read ではないので対象外（coverage_verify.py が検証する）。
    ★括弧書きの注記（例「（現状維持のため差し替え先なし）」）はパスでないので除外する。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("seen", "seen_claude") and isinstance(v, list):
                acc.extend(x for x in v
                           if isinstance(x, str) and re.search(r"\.(jpg|jpeg|png|webp)", x, re.I))
            else:
                collect_seen(v, acc)
    elif isinstance(obj, list):
        for x in obj:
            collect_seen(x, acc)

def norm(p):
    """パスの照合はbasename＋直近1ディレクトリで行う（絶対/相対の揺れを吸収）。
    注記が後ろに付いたパス（例 "a/b.jpg（原寸で確認）"）にも耐えるよう拡張子までで切る。"""
    m = re.search(r"^(.*?\.(?:jpg|jpeg|png|webp))", p, re.I)
    if m: p = m.group(1)
    parts = p.replace("\\", "/").rstrip("/").split("/")
    return "/".join(parts[-2:]) if len(parts) >= 2 else parts[-1]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("transcript")
    ap.add_argument("--claim", nargs="*", default=[])
    ap.add_argument("--out", default="qc/evidence_report.json")
    a = ap.parse_args()

    actual = read_images_from_transcript(a.transcript)
    actual_set = {norm(p) for p in actual}

    claimed = []
    for cp in a.claim:
        try:
            collect_seen(json.load(open(cp, encoding="utf-8")), claimed)
        except Exception as e:
            print(f"★申告ファイルが読めない: {cp}: {e}")
            sys.exit(2)

    fabricated = sorted({c for c in claimed if norm(c) not in actual_set})

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    report = {
        "transcript": a.transcript,
        "actually_read_count": len(actual),
        "actually_read_unique": len(actual_set),
        "claimed_count": len(claimed),
        "fabricated": fabricated,          # 申告にあるのに実Readが無い＝捏造疑い
        "verdict": "PASS" if not fabricated else "FAIL",
    }
    json.dump(report, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"実Read画像: {len(actual)}件（ユニーク{len(actual_set)}） / 申告: {len(claimed)}件")
    if fabricated:
        print(f"★捏造疑い（申告にあるのに実Readが無い）: {len(fabricated)}件")
        for p in fabricated[:30]:
            print(f"   {p}")
        sys.exit(1)
    print("PASS: 申告と実Readの不一致 0件")

if __name__ == "__main__":
    main()
