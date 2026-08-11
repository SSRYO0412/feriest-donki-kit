#!/usr/bin/env python3
"""動画台帳+レンダーpy管理DB → adopted.json / renders.json エクスポート。

check_adoption_sync.py の入力(--adopted/--renders)を自動生成する(手動作成の穴を塞ぐ)。
採用の解決順: レンダーDBの `採用状態=採用` 行(契約の正) → 無ければレガシー `採用可否=採用`。
バリアント付き採用行は `<video_id>_<variant頭文字>` キー(例 0290_B)で出力する。

使い方: python3 notion_export_adopted.py <project_page_id> --out <dir>
出力: <dir>/adopted.json, <dir>/renders.json
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from notion_rest import Notion
from notion_model import Project, RENDER_KEY_RE, extract_video_id


def variant_suffix(variant):
    if not variant or variant == "なし":
        return ""
    return "_" + variant.split("_")[0]  # "A_顔あり" -> "_A"


def export(project_page_id, outdir):
    n = Notion()
    p = Project(n, project_page_id)
    if "render" not in p.dbs:
        sys.exit("ERROR: レンダーpy管理DBが見つからない")
    os.makedirs(outdir, exist_ok=True)

    registry = set()
    if "video" in p.dbs:
        for v in p.rows("video"):
            vid = v.get("video_id") or extract_video_id(v.get("title"))
            if vid:
                registry.add(vid)
    renders = []
    adopted = {}
    for r in p.rows("render"):
        vid = r.get("video_id") or               extract_video_id(r.get("legacy_video_name") or r.get("title"), registry or None) or               extract_video_id(r.get("py") or r.get("mp4"), registry or None)
        v = r.get("v")
        rk = r.get("render_key")
        if rk and not v:
            m = RENDER_KEY_RE.match(rk)
            if m:
                v = int(m.group(2))
        if v is None:
            import re as _re
            m = _re.search(r"v(\d+)", str(r.get("v_legacy") or ""))
            if m:
                v = int(m.group(1))
        adopt = r.get("adopt") or {"採用": "採用", "不採用": "却下", "検品待ち": "未判定",
                                   "破棄予定": "却下", "参考": "却下"}.get(r.get("adopt_legacy") or "", None)
        rec = {
            "render_key": rk, "video_id": vid, "v": v,
            "variant": r.get("variant"), "adopt": adopt,
            "py": r.get("py"), "mp4": r.get("mp4"),
            "page_id": r["_id"], "title": r.get("title"),
        }
        renders.append(rec)
        if adopt == "採用" and vid and v is not None:
            key = f"{vid}{variant_suffix(r.get('variant'))}"
            if key in adopted:
                print(f"WARN: 採用行が複数: {key} (audit不変条件違反。両方出力せず先勝ち)")
                continue
            adopted[key] = {"v": int(v), "mp4": rec["mp4"], "py": rec["py"],
                            "render_page_id": r["_id"]}

    json.dump(adopted, open(f"{outdir}/adopted.json", "w"), ensure_ascii=False, indent=1)
    json.dump(renders, open(f"{outdir}/renders.json", "w"), ensure_ascii=False, indent=1)
    print(f"✅ export: adopted={len(adopted)}件 / renders={len(renders)}行 -> {outdir}")
    n_missing_v = sum(1 for r in renders if r["v"] is None)
    if n_missing_v:
        print(f"WARN: v未設定のレンダー行 {n_missing_v}件(autolink/移行でrender_key付与が必要)")
    return adopted, renders


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("project_page_id")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    export(a.project_page_id, a.out)
