#!/usr/bin/env python3
"""修正・量産案件のスカフォールド（VERSIONING.md §3 のディレクトリ規約で作成）。

使い方:
  python3 new_revision_project.py <project-root>/<案件名> [--videos 0290 0291 ...]

作成物:
  sources/ vo/ bgm/ cta/ intermediates/ renders/ py/ qa/ delivery/ + ledger.md
  --videos 指定時は renders/<vid>/ と ledger.md の動画別セクションも生成。
"""
import argparse
import sys
from datetime import date
from pathlib import Path

DIRS = ["sources", "vo", "bgm", "cta", "intermediates", "renders", "py", "qa", "delivery"]

LEDGER_HEADER = """# 修正台帳 — {name}

> 採用状態の正本は管理DB（Notion動画台帳）。このファイルは作業中のミラー/下書き。
> 規約: `references/VERSIONING.md` / チェックリスト: `references/revision-checklist.md`
> 履歴は日付付き追記・上書き消去厳禁。書式:
> `YYYY-MM-DD: v<NN>採用 ← v<MM>却下(<理由>)。根拠=<実測/承認>。py=render_<vid>_v<NN>_<slug>.py`

作成日: {today}

## 案件共通ルール（案件開始時に埋める）
- 納品仕様（解像度/fps/形式/命名）:
- 素材ルール（顔出し/写り込み/禁止素材/表記）:
- 音声（声質モデル/BGMと頭出し）:
- 納品先パス:
- 管理DB（NotionページURL/collection ID）:

"""

LEDGER_VIDEO = """## {vid}
- 現在の採用MP4:
- 現在の採用py:
- 採用v:
- バリアント（顔あり/なし等、双方採用なら両方併記）:
- 保持すべき過去修正（回帰チェック対象の差分表）:
  - （まだなし）
- 残課題:
- 更新履歴（日付付き追記・消去禁止）:
  - {today}: 台帳作成

"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", help="案件ルート（作成される）")
    ap.add_argument("--videos", nargs="*", default=[], help="動画ID一覧")
    args = ap.parse_args()

    root = Path(args.root).expanduser()
    if root.exists() and any(root.iterdir()):
        sys.exit(f"ERROR: {root} は空でない。既存案件を上書きしない（別名で作るか手動で確認）")
    root.mkdir(parents=True, exist_ok=True)
    for d in DIRS:
        (root / d).mkdir(exist_ok=True)
    for vid in args.videos:
        (root / "renders" / vid).mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    ledger = LEDGER_HEADER.format(name=root.name, today=today)
    for vid in args.videos:
        ledger += LEDGER_VIDEO.format(vid=vid, today=today)
    (root / "ledger.md").write_text(ledger)

    print(f"✅ 作成: {root}")
    print("   " + " ".join(d + "/" for d in DIRS))
    print(f"   ledger.md（動画 {len(args.videos)} 件分のセクション込み）" if args.videos else "   ledger.md")
    print("次: ledger.md の案件共通ルールを埋め、管理DB（動画台帳）と紐づけること。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
