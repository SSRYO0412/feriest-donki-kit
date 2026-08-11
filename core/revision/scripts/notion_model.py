#!/usr/bin/env python3
"""映像管理Notionプロジェクトの共有モデル（notion-db-contract.md の実装補助）。

- プロジェクトページID → DB役割(role)の解決（テンプレ複製・VERARUS等、命名ゆれをタイトル部分一致で吸収）
- プロパティ別名（テンプレ名 vs 案件名の差を吸収。例: 採用MP4パス ⇔ 現在の採用MP4）
- rollback_log.jsonl 付き patch（変更前値を記録してから書く。notion_rollback.py が逆適用）
- キー文法regex（契約 §1）
"""
import json
import os
import re
import time

from notion_rest import Notion, plain, rt

# ---- キー文法（契約 §1）----
VIDEO_ID_RE = re.compile(r"^\d{3,4}(_\d{2})?$")
RENDER_KEY_RE = re.compile(r"^(\d{3,4}(?:_\d{2})?)_v(\d+)(?:_([A-Za-z]\w*))?$")
CUT_KEY_RE = re.compile(r"^(\d{3,4}(?:_\d{2})?)_c(\d+)$")
VIDEO_ID_FIND = re.compile(r"\d{3,4}(?:_\d{2})?")

# ---- DB役割の解決（タイトル部分一致）----
ROLE_PATTERNS = {
    "video": r"動画台帳",
    "cut": r"カット台帳",
    "asset": r"素材DB",
    "asset_use": r"素材使用",
    "instruction": r"修正指示",
    "render": r"レンダー.{0,3}py管理|レンダー管理",
    "qa": r"QA.{0,3}(検品)?ログ",
    "telop": r"テロップチェック",
    "project": r"プロジェクト台帳",
}

# ---- プロパティ別名（role → 論理名 → 実プロパティ名の候補リスト。先に見つかった方を使う）----
PROP_ALIASES = {
    "video": {
        "video_id": ["video_id"],
        "title": ["動画名"],
        "adopted_rel": ["採用レンダー"],
        "adopted_summary": ["採用サマリ"],
        "mirror_v": ["最終v", "現在の採用v"],
        "mirror_mp4": ["採用MP4パス", "現在の採用MP4"],
        "mirror_py": ["採用pyパス", "現在の採用py"],
        "integrity": ["整合"],
        "status": ["ステータス"],
    },
    "render": {
        "render_key": ["render_key"],
        "video_id": ["video_id"],
        "v": ["v"],
        "v_legacy": ["v番号"],
        "variant": ["バリアント"],
        "adopt": ["採用状態"],
        "adopt_legacy": ["採用可否"],
        "reject_reason": ["却下理由"],
        "evidence": ["根拠"],
        "judged": ["判定日"],
        "py": ["pyパス", "py保存先"],
        "mp4": ["MP4パス", "出力MP4パス"],
        "video_rel": ["動画"],
        "instr_rel": ["修正指示", "関連修正指示"],
        "title": ["レンダー名", "出力名"],
        "legacy_video_name": ["対象動画名"],
        "reject_note": ["使わない理由"],
    },
    "instruction": {
        "video_ids": ["対象video_id"],
        "all_videos": ["全動画対象"],
        "status": ["ステータス"],
        "video_rel": ["動画"],
        "cut_id": ["対象cut id"],
        "legacy_video_names": ["対象動画名", "旧_対象動画名"],
        "title": ["指示タイトル"],
    },
    "qa": {
        "video_id": ["video_id"],
        "render_key": ["render_key"],
        "result": ["結果"],
        "video_rel": ["動画"],
        "render_rel": ["レンダー"],
        "instr_rel": ["修正指示"],
        "legacy_video_name": ["対象動画名"],
        "legacy_render_name": ["対象レンダー名", "レンダー名"],
        "title": ["QA名", "検品ログ名"],
    },
    "cut": {
        "cut_key": ["cut_key"],
        "video_id": ["video_id"],
        "cut_id": ["cut id"],
        "video_rel": ["動画"],
        "legacy_video_name": ["動画名"],
        "title": ["カット名"],
    },
    "asset_use": {
        "cut_key": ["cut_key"],
        "video_id": ["video_id"],
        "cut_id": ["cut id"],
        "video_rel": ["動画"],
        "cut_rel": ["カット"],
        "legacy_video_name": ["動画名"],
        "title": ["使用レコード名", "使用名"],
    },
    "telop": {
        "video_id": ["video_id"],
        "video_rel": ["動画"],
        "line_no": ["行No"],
        "cut_id": ["cut id"],
        "legacy_video_name": ["動画名", "旧_対象動画名", "対象動画名"],
        "title": ["行テキスト", "テロップ内容"],
        "status": ["ステータス"],
    },
    "project": {
        "gate": ["納品ゲート結果"],
        "title": ["プロジェクト名"],
    },
}


class Project:
    """1つの映像管理プロジェクト（親ページ配下のDB群）。"""

    def __init__(self, notion: Notion, page_id: str):
        self.n = notion
        self.page_id = page_id.replace("-", "")
        self.dbs = {}       # role -> db_id
        self.titles = {}    # role -> db title
        self.schemas = {}   # role -> schema dict (lazy)
        for db_id, title in notion.find_child_databases(self.page_id):
            for role, pat in ROLE_PATTERNS.items():
                if re.search(pat, title or "") and role not in self.dbs:
                    self.dbs[role] = db_id
                    self.titles[role] = title

    def schema(self, role):
        if role not in self.schemas:
            self.schemas[role] = self.n.get_database(self.dbs[role])
        return self.schemas[role]

    def prop(self, role, logical):
        """論理名→そのDBに実在するプロパティ名。無ければNone。"""
        props = self.schema(role)["properties"]
        for cand in PROP_ALIASES.get(role, {}).get(logical, []):
            if cand in props:
                return cand
        return None

    def rows(self, role):
        """全行を [{'_id', '_props', <論理名>: 値, ...}] で返す（別名解決済みプレーン値）。"""
        out = []
        for r in self.n.query_database(self.dbs[role]):
            row = {"_id": r["id"], "_props": r["properties"]}
            for logical in PROP_ALIASES.get(role, {}):
                name = self.prop(role, logical)
                if name and name in r["properties"]:
                    row[logical] = plain(r["properties"][name])
            out.append(row)
        return out


class PatchLogger:
    """rollback_log.jsonl 付き patch。変更前値を記録してから書く（契約: 層3ロールバック）。"""

    def __init__(self, notion: Notion, log_path: str, dry_run: bool = True):
        self.n = notion
        self.log_path = log_path
        self.dry = dry_run
        self.count = 0

    def patch(self, page_id, prop_name, new_payload, before_plain=None, note=""):
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "page_id": page_id,
            "prop": prop_name,
            "before": before_plain,
            "after_payload": new_payload,
            "note": note,
            "dry_run": self.dry,
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        if not self.dry:
            self.n.patch_page(page_id, {prop_name: new_payload})
        self.count += 1

    def create(self, database_id, properties, note=""):
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "create_in": database_id,
            "properties_summary": {k: str(v)[:120] for k, v in properties.items()},
            "note": note,
            "dry_run": self.dry,
        }
        created_id = None
        if not self.dry:
            res = self.n.create_page(database_id, properties)
            created_id = res["id"]
            entry["created_page_id"] = created_id
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.count += 1
        return created_id


def rel_payload(*page_ids):
    return {"relation": [{"id": p} for p in page_ids if p]}


def rt_payload(text):
    return {"rich_text": rt(text)}


def sel_payload(name):
    return {"select": {"name": name}}


def extract_video_id(text, registry=None):
    """自由テキスト(動画名・パス等)から video_id を推定。

    registry(動画台帳のvideo_id集合)を渡すと、候補(長い順)をレジストリと照合して解決する。
    例: "mov_ugc_0284_01_v9.mp4" は素朴には 0284_01 にマッチするが、レジストリに 0284 しか
    無ければ 0284 を返す(納品ファイル名の _01 連番と 0181_05 型の台本IDの曖昧性を解消)。
    """
    if not text:
        return None
    s = str(text)
    cands = []
    for m in VIDEO_ID_FIND.finditer(s):
        full = m.group(0)
        cands.append(full)
        if "_" in full:
            cands.append(full.split("_")[0])
    if registry:
        for c in cands:  # 出現順・長い形優先(finditerの順で full → prefix)
            if c in registry:
                return c
        # 一意プレフィックス解決: "0284" がレジストリの "0284_01" 1件だけに前方一致するなら採用
        for c in cands:
            hits = [r for r in registry if r == c or r.startswith(c + "_")]
            if len(hits) == 1:
                return hits[0]
        return None
    return cands[0] if cands else None


def default_log_path(prefix="rollback_log"):
    d = os.environ.get("CLAUDE_JOB_DIR")
    base = os.path.join(d, "tmp") if d else "."
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, f"{prefix}_{time.strftime('%Y%m%d_%H%M%S')}.jsonl")
