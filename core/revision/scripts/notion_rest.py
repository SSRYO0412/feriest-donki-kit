#!/usr/bin/env python3
"""Notion REST 共有モジュール（notion-db-contract.md 準拠のスクリプト群が共用）。

認証トークンの解決順（新たな永続化はしない）:
  1. 環境変数 NOTION_TOKEN
  2. --token-file で渡された一時ファイル（使用後は呼び出し側が削除）
  3. ~/.claude.json の mcpServers.notion 定義（既存の保存場所を読むだけ）
トークンは絶対にログ・stdoutへ出さない。

API バージョン 2022-06-28（database ベース）。指数バックオフ・ページネーション対応。

CLI:
  python3 notion_rest.py snapshot <page_id_or_db_id...> --out <dir>
      ページIDを渡すと配下の child_database を再帰列挙し、各DBの schema + 全行を
      <dir>/<db名>.schema.json / <db名>.rows.json に保存（バックアップ層2）。
"""

# --- VIDEO OPS ライセンスゲート（仕様§4.2・ローカル読取のみ・ネットワークなし） ---
def _vops_require(_feat):
    import sys as _s
    from pathlib import Path as _P
    _h = _P(__file__).resolve()
    _cands = [q for p in _h.parents for q in (p / "ops" / "license", p / "core" / "ops" / "license")]
    _cands.append(_P.home() / ".claude" / "skills" / "_video-core" / "ops" / "license")
    for _c in _cands:
        if (_c / "vops_license.py").exists():
            _s.path.insert(0, str(_c))
            import vops_license as _v
            _v.require(_feat)
            return
    print("⚠ VIDEO OPS: ライセンス機構が見つからない（導通不備）— 続行", file=_s.stderr)


_vops_require("ledger")
# --- ゲートここまで ---
import argparse
import json
import os
import re
import sys
import time
import ssl
import urllib.error
import urllib.request

API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def resolve_token(token_file=None):
    tok = os.environ.get("NOTION_TOKEN")
    if tok:
        return tok.strip()
    if token_file and os.path.exists(token_file):
        return open(token_file).read().strip()
    cfg = os.path.expanduser("~/.claude.json")
    if os.path.exists(cfg):
        try:
            d = json.load(open(cfg))
            for proj in d.get("projects", {}).values():
                srv = (proj.get("mcpServers") or {}).get("notion")
                if not srv:
                    continue
                headers = json.loads(srv.get("env", {}).get("OPENAPI_MCP_HEADERS", "{}"))
                auth = headers.get("Authorization", "")
                if auth.startswith("Bearer "):
                    return auth[len("Bearer "):].strip()
        except Exception:
            pass
    sys.exit("ERROR: Notionトークンが見つからない (NOTION_TOKEN / --token-file / ~/.claude.json)")


class Notion:
    def __init__(self, token=None, token_file=None):
        self.token = token or resolve_token(token_file)

    def req(self, method, path, body=None, max_retry=6):
        url = API + path
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(max_retry):
            r = urllib.request.Request(url, data=data, method=method, headers={
                "Authorization": f"Bearer {self.token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            })
            try:
                with urllib.request.urlopen(r, timeout=60) as resp:
                    return json.loads(resp.read())
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504) and attempt < max_retry - 1:
                    wait = float(e.headers.get("Retry-After") or (2 ** attempt))
                    time.sleep(min(wait, 30))
                    continue
                detail = e.read().decode()[:300]
                raise RuntimeError(f"{method} {path} -> {e.code}: {detail}") from None
            except (urllib.error.URLError, ssl.SSLError, ConnectionError, TimeoutError):
                # 2026-08-02: SSLV3_ALERT_BAD_RECORD_MAC で長時間バッチが落ちたため
                # 一過性のネットワーク障害もリトライ対象に含める
                if attempt < max_retry - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise

    # --- 基本操作 ---
    def get_page(self, page_id):
        return self.req("GET", f"/pages/{page_id}")

    def patch_page(self, page_id, properties=None, archived=None):
        body = {}
        if properties is not None:
            body["properties"] = properties
        if archived is not None:
            body["archived"] = archived
        return self.req("PATCH", f"/pages/{page_id}", body)

    def create_page(self, database_id, properties, children=None):
        body = {"parent": {"database_id": database_id}, "properties": properties}
        if children:
            body["children"] = children
        return self.req("POST", "/pages", body)

    def get_database(self, db_id):
        return self.req("GET", f"/databases/{db_id}")

    def update_database(self, db_id, properties=None, title=None):
        body = {}
        if properties is not None:
            body["properties"] = properties
        if title is not None:
            body["title"] = [{"type": "text", "text": {"content": title}}]
        return self.req("PATCH", f"/databases/{db_id}", body)

    def query_database(self, db_id, filter=None, page_size=100):
        """全行をページネーションで取得して返す。"""
        rows, cursor = [], None
        while True:
            body = {"page_size": page_size}
            if filter:
                body["filter"] = filter
            if cursor:
                body["start_cursor"] = cursor
            res = self.req("POST", f"/databases/{db_id}/query", body)
            rows += res.get("results", [])
            if not res.get("has_more"):
                return rows
            cursor = res.get("next_cursor")

    def block_children(self, block_id):
        out, cursor = [], None
        while True:
            path = f"/blocks/{block_id}/children?page_size=100"
            if cursor:
                path += f"&start_cursor={cursor}"
            res = self.req("GET", path)
            out += res.get("results", [])
            if not res.get("has_more"):
                return out
            cursor = res.get("next_cursor")

    def append_blocks(self, block_id, children):
        return self.req("PATCH", f"/blocks/{block_id}/children", {"children": children})

    def find_child_databases(self, page_id):
        """ページ配下の child_database を [(db_id, title), ...] で返す。"""
        out = []
        for b in self.block_children(page_id):
            if b.get("type") == "child_database":
                out.append((b["id"], b["child_database"].get("title", "")))
        return out


# --- 値の取り出しヘルパー（プロパティ型を吸収してプレーン値に）---
def plain(prop):
    t = prop.get("type")
    v = prop.get(t)
    if t in ("title", "rich_text"):
        return "".join(x.get("plain_text", "") for x in (v or []))
    if t == "select":
        return (v or {}).get("name")
    if t == "multi_select":
        return [x["name"] for x in (v or [])]
    if t == "status":
        return (v or {}).get("name")
    if t == "number":
        return v
    if t == "checkbox":
        return v
    if t == "date":
        return (v or {}).get("start")
    if t == "relation":
        return [x["id"] for x in (v or [])]
    if t in ("created_time", "last_edited_time"):
        return v
    if t == "files":
        return [f.get("name") for f in (v or [])]
    if t == "unique_id":
        v = v or {}
        return f"{v.get('prefix') or ''}{v.get('number')}"
    return v


def rt(text):
    """rich_text/title 書き込み用の値。"""
    return [{"type": "text", "text": {"content": str(text)[:2000]}}]


def _safe_name(s):
    return re.sub(r"[^\w぀-ヿ一-鿿-]+", "_", s)[:60] or "untitled"


def snapshot(n, ids, outdir):
    os.makedirs(outdir, exist_ok=True)
    dbs = []
    for i in ids:
        i = i.replace("collection://", "").replace("-", "")
        # ページなら配下DBを列挙、DBならそのまま
        try:
            found = n.find_child_databases(i)
        except RuntimeError:
            found = []
        if found:
            dbs += found
        else:
            try:
                meta = n.get_database(i)
                title = "".join(x.get("plain_text", "") for x in meta.get("title", []))
                dbs.append((i, title))
            except RuntimeError as e:
                print(f"WARN: {i} はページでもDBでもない: {e}")
    total_rows = 0
    for db_id, title in dbs:
        name = _safe_name(title)
        try:
            schema = n.get_database(db_id)
        except RuntimeError as e:
            if "linked database" in str(e):
                print(f"  SKIP(リンクドビュー・実体なし): {title}")
                continue
            raise
        rows = n.query_database(db_id)
        total_rows += len(rows)
        json.dump(schema, open(f"{outdir}/{name}.schema.json", "w"), ensure_ascii=False, indent=1)
        json.dump(rows, open(f"{outdir}/{name}.rows.json", "w"), ensure_ascii=False, indent=1)
        print(f"  {title}: schema + {len(rows)}行 -> {name}.*.json")
    print(f"✅ snapshot: {len(dbs)}DB / {total_rows}行 -> {outdir}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["snapshot"])
    ap.add_argument("ids", nargs="+", help="ページID or DB ID (collection://可)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--token-file")
    a = ap.parse_args()
    n = Notion(token_file=a.token_file)
    snapshot(n, a.ids, a.out)
