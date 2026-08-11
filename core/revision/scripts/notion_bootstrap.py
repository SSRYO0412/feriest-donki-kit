#!/usr/bin/env python3
"""notion_bootstrap.py — 12DB体制を自ワークスペースへ生成（DISTRIBUTION.md §4・2026-08-10 新設）

「テンプレDB URL を複製」方式は特定ワークスペース依存のため、配布先は schema-as-code
（notion-12db-schema.json = notion-db-contract.md §3/§9 の機械可読ミラー）から生成する。

使い方:
  # 案件ハブページ直下に project スコープ8DBを生成 → mapping JSON を保存
  python3 notion_bootstrap.py <parent_page_id> --out db_map.json [--dry-run]

  # 動画ページ配下に per-video スコープ4DB（カット台帳/修正台帳/テロップチェック/台本DB）を生成
  python3 notion_bootstrap.py <video_page_id> --scope per-video --video-id 0290 \
      --map db_map.json --out db_map_0290.json

2パス生成: ①relation以外のプロパティでDB作成 → ②生成済みIDでrelationをPATCH追加。
relation先が未生成（per-videoからprojectスコアDBへ等）の場合は --map で過去の生成結果を渡す。
解決できないrelationはWARNしてスキップする（relationはautolinkの派生物なので致命ではない。契約§2）。

注意:
- 実行前に必ずNotion検索で既存インスタンスを確認する（契約§9「重複作成の禁止」。同名DBの
  二重管理事故が実際に起きている）。このスクリプトは存在確認をしない＝呼ぶ側の責務。
- ビューはREST APIで作成不可。生成後に §10-1 の時系列ビューをMCP/UIで設定し、
  実クエリで「先頭0秒・末尾最終行」を検証してから完了と言う（スクリプトが最後に表示する）。
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from notion_rest import Notion, rt  # noqa: E402

# 2026-08-11 改名: 13DB化に伴い notion-db-schema.json が正（旧名は1リリースの間同内容コピー）
SCHEMA_DEFAULT = HERE.parent / "references" / "notion-db-schema.json"


def build_props(db_def):
    props = {db_def["title_prop"]: {"title": {}}}
    props.update(db_def["properties"])
    return props


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("parent_page_id", help="生成先の親ページID（案件ハブ or 動画ページ）")
    ap.add_argument("--schema", default=str(SCHEMA_DEFAULT))
    ap.add_argument("--scope", choices=["project", "per-video", "all"], default="project")
    ap.add_argument("--video-id", help="per-video 時のDB名接頭辞（例: 0290 → 『0290 カット台帳』）")
    ap.add_argument("--map", help="既存生成結果の mapping JSON（relation解決に使う）")
    ap.add_argument("--out", help="生成結果 mapping JSON の保存先")
    ap.add_argument("--dry-run", action="store_true", help="APIを呼ばず生成計画だけ表示")
    ap.add_argument("--with-rules", action="store_true",
                    help="案件ルールDB（optional_feature=rules）も作成する（rulesライセンス有効時）")
    ap.add_argument("--token-file")
    a = ap.parse_args()

    enabled_optional = {"rules"} if a.with_rules else set()
    schema = json.loads(Path(a.schema).read_text())
    dbs = {k: v for k, v in schema["databases"].items()
           if (a.scope == "all" or v["scope"] == a.scope)
           and (not v.get("optional_feature") or v["optional_feature"] in enabled_optional)}
    if not dbs:
        sys.exit(f"ERROR: scope={a.scope} に該当するDBが schema に無い")
    if a.scope in ("per-video", "all") and not a.video_id and a.scope == "per-video":
        print("WARN: --video-id 未指定。per-video DB名に接頭辞が付かない（複数動画で名前が衝突する）")

    id_map = {}
    if a.map:
        id_map.update(json.loads(Path(a.map).read_text()))

    def display_name(key, d):
        if d["scope"] == "per-video" and a.video_id:
            return f"{a.video_id} {d['name']}"
        return d["name"]

    print(f"=== 生成計画: scope={a.scope} → {len(dbs)}DB (parent={a.parent_page_id}) ===")
    for key, d in dbs.items():
        rels = ", ".join(f"{r['prop']}→{r['target']}" for r in d["relations"]) or "なし"
        print(f"  [{key}] {display_name(key, d)}  props={len(d['properties']) + 1}  relations={rels}")
    if a.dry_run:
        print("\n--dry-run: API呼び出しなし。")
        return 0

    n = Notion(token_file=a.token_file)

    # ★冪等モード（2026-08-11・13DB移行対応）: 親ページ配下の既存 child_database を
    #   名前で検出し、存在するものはスキップして差分のみ作成する。
    #   12DB 済みの環境に対して再実行すると「13番目だけ追加」になる
    existing = {}
    cursor = None
    while True:
        path = f"/blocks/{a.parent_page_id}/children?page_size=100"
        if cursor:
            path += f"&start_cursor={cursor}"
        resp = n.req("GET", path)
        for b in resp.get("results", []):
            if b.get("type") == "child_database":
                existing[b["child_database"]["title"]] = b["id"]
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
    if existing:
        print(f"既存DB {len(existing)} 件を検出（同名はスキップ＝冪等）")

    created_keys = []
    # パス1: relation以外で作成（既存はスキップして id を再利用）
    for key, d in dbs.items():
        name = display_name(key, d)
        if name in existing:
            id_map[key] = existing[name]
            print(f"skip    [{key}] {name}（既存: {existing[name]}）")
            continue
        body = {
            "parent": {"type": "page_id", "page_id": a.parent_page_id},
            "title": rt(name),
            "properties": build_props(d),
        }
        resp = n.req("POST", "/databases", body)
        id_map[key] = resp["id"]
        created_keys.append(key)
        print(f"created [{key}] {name} → {resp['id']}")

    # パス2: relation を追加（★今回作成した分のみ。既存DBのプロパティは触らない）
    for key, d in dbs.items():
        if key not in created_keys:
            continue
        add = {}
        for r in d["relations"]:
            target_id = id_map.get(r["target"])
            if not target_id:
                print(f"WARN: [{key}].{r['prop']} → {r['target']} のIDが未解決"
                      f"（--map で過去の生成結果を渡すか、後で autolink に任せる）")
                continue
            add[r["prop"]] = {"relation": {"database_id": target_id, "single_property": {}}}
        if add:
            n.req("PATCH", f"/databases/{id_map[key]}", {"properties": add})
            print(f"relations [{key}]: {', '.join(add)}")

    if a.out:
        Path(a.out).write_text(json.dumps(id_map, ensure_ascii=False, indent=2))
        print(f"\nmapping 保存: {a.out}（per-video 生成時に --map で渡す）")

    print("\n★残タスク（REST API では不可・契約§10-1）:")
    print("  1. 時系列ビューを MCP(create_view/update_view) か UI で設定（デフォルトビューも直す）")
    print("  2. 設定後に実クエリで『先頭が0秒・末尾が最終行』を検証してから完了と言う")
    print("  3. プロジェクト台帳に案件1行を起票し、project.json の notion 節へDB IDを転記")
    return 0


if __name__ == "__main__":
    sys.exit(main())
