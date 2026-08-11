#!/usr/bin/env python3
"""rollback_log.jsonl の逆適用（層3ロールバック。notion_autolink/移行スクリプトのpatchを巻き戻す）。

- patch行: `before` のプレーン値を該当プロパティへ書き戻す(rich_text/select/relationを型推定)
- create行: `created_page_id` をアーカイブ(削除でなくarchived=true。復元可能)
- dry_run=true で記録された行はスキップ

使い方: python3 notion_rollback.py --log rollback_log.jsonl [--apply] [--last N]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from notion_rest import Notion, rt


def payload_from_before(after_payload, before):
    """afterのpayload型に合わせてbeforeプレーン値を書き戻しpayload化。"""
    if "relation" in after_payload:
        ids = before if isinstance(before, list) else ([] if before is None else [before])
        return {"relation": [{"id": i} for i in ids]}
    if "select" in after_payload:
        return {"select": ({"name": before} if before else None)}
    if "rich_text" in after_payload:
        return {"rich_text": rt(before or "")}
    if "checkbox" in after_payload:
        return {"checkbox": bool(before)}
    if "number" in after_payload:
        return {"number": before}
    if "date" in after_payload:
        return {"date": ({"start": before} if before else None)}
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--last", type=int, help="末尾N件だけ巻き戻す")
    a = ap.parse_args()
    entries = [json.loads(l) for l in open(a.log) if l.strip()]
    entries = [e for e in entries if not e.get("dry_run")]
    if a.last:
        entries = entries[-a.last:]
    entries.reverse()  # 逆順に適用
    n = Notion()
    done = skip = 0
    for e in entries:
        if "created_page_id" in e:
            print(f"{'(dry)' if not a.apply else ''} archive: {e['created_page_id']} ({e.get('note','')})")
            if a.apply:
                n.patch_page(e["created_page_id"], properties=None, archived=True)
            done += 1
            continue
        if "prop" not in e:
            skip += 1
            continue
        pl = payload_from_before(e.get("after_payload") or {}, e.get("before"))
        if pl is None:
            print(f"SKIP(型不明): {e['page_id']} {e['prop']}")
            skip += 1
            continue
        print(f"{'(dry)' if not a.apply else ''} revert: {e['page_id']} {e['prop']} <- {str(e.get('before'))[:60]}")
        if a.apply:
            n.patch_page(e["page_id"], {e["prop"]: pl})
        done += 1
    print(f"\n{'✅ 巻き戻し' if a.apply else '(dry-run)'} {done}件 / skip {skip}件")


if __name__ == "__main__":
    main()
