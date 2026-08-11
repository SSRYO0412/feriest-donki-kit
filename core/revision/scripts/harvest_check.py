#!/usr/bin/env python3
"""harvest_check.py — 収穫チェック（学びの正本反映漏れ検出・2026-08-10 新設）

なぜ在るか:
  学びが memory / LEARNINGS.md / Notion 止まりで正本（user-feedback-canon・skill）に載らず、
  次のセッションが素通りする事故が実際に起きた（canon 第VII章: 8/9 の MOGRT 転換・テロップ
  3階層が memory 止まりだった）。前回収穫マーカー以降に増えた「学びの候補」を機械で列挙し、
  canon/正本へ焼き込むか判定させるための道具。revision-checklist §E から毎セッション末に呼ぶ。

使い方:
  python3 harvest_check.py                 # 候補一覧を表示
  python3 harvest_check.py --mark          # 現時刻を収穫済みマーカーに記録
  python3 harvest_check.py --since-days 7  # マーカーが無いとき過去N日を対象（既定14）

探す場所（環境に無いものは黙ってスキップ）:
  1. memory ディレクトリ（--memory-dir / $VIDEO_OPS_MEMORY_DIR /
     ~/.claude/projects/*/memory の新しい順で最初に見つかったもの）
     → feedback_* / reference_* / project_* の新規・更新ファイル
  2. 案件ルート（--project-root、複数可）の LEARNINGS*.md / HANDOFF*.md / PROJECT-RULES.md
  3. Notion の学びページは API を叩かない（このスクリプトはオフライン専用）。
     セッション中に作った Notion ページは自分で一覧に加えること。

マーカー: <repo>/core/revision/.last_harvest（ISO8601 1行。git 管理外にしない=収穫履歴も資産）
"""

import argparse
import datetime as dt
import glob
import os
import sys

MARKER_NAME = ".last_harvest"


def find_memory_dir(explicit=None):
    if explicit:
        return explicit if os.path.isdir(explicit) else None
    env = os.environ.get("VIDEO_OPS_MEMORY_DIR")
    if env and os.path.isdir(env):
        return env
    cands = sorted(
        glob.glob(os.path.expanduser("~/.claude/projects/*/memory")),
        key=lambda p: os.path.getmtime(p),
        reverse=True,
    )
    return cands[0] if cands else None


def load_marker(marker_path, since_days):
    if os.path.isfile(marker_path):
        try:
            return dt.datetime.fromisoformat(open(marker_path).read().strip())
        except Exception:  # noqa: BLE001
            pass
    return dt.datetime.now() - dt.timedelta(days=since_days)


def newer_files(root, patterns, since_ts):
    out = []
    for pat in patterns:
        for p in glob.glob(os.path.join(root, pat)):
            if os.path.isfile(p) and os.path.getmtime(p) > since_ts:
                out.append((os.path.getmtime(p), p))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--memory-dir", default=None)
    ap.add_argument("--project-root", action="append", default=[])
    ap.add_argument("--since-days", type=int, default=14)
    ap.add_argument("--mark", action="store_true", help="現時刻を収穫済みとして記録")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    marker_path = os.path.join(here, "..", MARKER_NAME)
    marker_path = os.path.normpath(marker_path)

    if args.mark:
        with open(marker_path, "w") as f:
            f.write(dt.datetime.now().isoformat(timespec="seconds") + "\n")
        print(f"収穫済みマーカーを更新: {marker_path}")
        return 0

    since = load_marker(marker_path, args.since_days)
    since_ts = since.timestamp()
    print(f"=== 収穫チェック（{since.isoformat(timespec='seconds')} 以降の学び候補） ===")

    found = []

    mem = find_memory_dir(args.memory_dir)
    if mem:
        hits = newer_files(mem, ["feedback_*.md", "reference_*.md", "project_*.md"], since_ts)
        if hits:
            print(f"\n[memory] {mem}")
            for ts, p in sorted(hits, reverse=True):
                when = dt.datetime.fromtimestamp(ts).strftime("%m-%d %H:%M")
                print(f"  {when}  {os.path.basename(p)}")
            found += hits
    else:
        print("\n[memory] ディレクトリ未検出（--memory-dir か $VIDEO_OPS_MEMORY_DIR で指定可）")

    for root in args.project_root:
        hits = newer_files(
            root,
            ["LEARNINGS*.md", "**/LEARNINGS*.md", "HANDOFF*.md", "**/HANDOFF*.md",
             "PROJECT-RULES.md", "**/PROJECT-RULES.md"],
            since_ts,
        )
        if hits:
            print(f"\n[案件] {root}")
            for ts, p in sorted(set(hits), reverse=True):
                when = dt.datetime.fromtimestamp(ts).strftime("%m-%d %H:%M")
                print(f"  {when}  {os.path.relpath(p, root)}")
            found += hits

    print(f"\n候補 {len(found)} 件。各項目を判定すること:")
    print("  A) canon 追記対象（新種の指摘・事件）→ user-feedback-canon.md 第VII章以降へ")
    print("  B) 正本改訂対象 → TELOP-CRAFT / PRINCIPLES / 各SKILL → sync_core.sh push")
    print("  C) 案件フォーク限り → 案件の PROJECT-RULES.md へ")
    print("★セッション中に作った Notion の学びページはこの一覧に出ない — 自分で加えること。")
    print("判定と反映が済んだら: python3 harvest_check.py --mark")
    return 0


if __name__ == "__main__":
    sys.exit(main())
