#!/usr/bin/env python3
"""読み取り専用監査（notion-db-contract.md §8 の不変条件を実装）。FAILあり=exit 1。

検査項目:
 [K] キー文法違反(video_id/render_key/cut_key がregex不一致)
 [ONE] (video_id, バリアント)ごとに採用状態=採用がちょうど1行(0=WARN未確定, 2+=FAIL)
 [PATH] 採用行・鏡列の非パス値(`pyなし`単体/`各build_*`/`詳細(py)?未確認`/`〜参照`のみ 等)。定型 `py不要(理由: ...)` は許可
 [VOCAB] ステータス語彙のドリフト(契約§4正規語彙 + レガシー対応表で変換提案)
 [REL] キーはあるのにrelation欠落(=autolink未実行。件数のみ、FAILにしない)
 [ORPH] cut_key孤児(カット台帳に無いcut_keyの参照)・プレースホルダ(`未確認`等)
 [MIR] 動画台帳の鏡列と採用レンダー行の不一致
 [STALE] レンダー行が存在する動画の修正指示が非終端ステータスのまま(WARN)

使い方: python3 notion_audit.py <project_page_id> [--strict-legacy]
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from notion_rest import Notion
from notion_model import (Project, VIDEO_ID_RE, RENDER_KEY_RE, CUT_KEY_RE, extract_video_id)

CANON = {
    "instruction": {"新規", "確認中", "設計済み", "作業中", "レンダー済み", "検品中",
                    "修正完了", "納品済み", "却下", "保留"},
    "render_adopt": {"採用", "却下", "旧採用", "未判定"},
    "qa_result": {"OK", "NG", "条件付きOK"},
    "video": {"制作中", "修正中", "納品済み", "アーカイブ"},
}
LEGACY_MAP = {"確認済み": "OK", "修正済み": "修正完了", "要再確認": "条件付きOK",
              "不採用": "却下", "検品待ち": "未判定", "破棄予定": "却下", "参考": "却下"}
NONPATH = re.compile(r"^(pyなし.*|各\s*\S+.*|.*詳細(py)?未確認.*|.*参照$|原版名.*)$")
PY_OK_FORM = re.compile(r"^py不要\(理由:.+\)$")
TERMINAL = {"納品済み", "修正完了", "却下", "保留"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_page_id")
    ap.add_argument("--strict-legacy", action="store_true",
                    help="レガシー語彙をWARNでなくFAILにする")
    a = ap.parse_args()
    n = Notion()
    p = Project(n, a.project_page_id)
    fails, warns = [], []

    videos = p.rows("video")
    vid_set = {v.get("video_id") or extract_video_id(v.get("title")) for v in videos} - {None}
    renders = p.rows("render") if "render" in p.dbs else []
    cuts = p.rows("cut") if "cut" in p.dbs else []
    cut_keys = {c.get("cut_key") for c in cuts if c.get("cut_key")}

    # [K] キー文法
    for v in videos:
        vid = v.get("video_id")
        if vid and not VIDEO_ID_RE.match(vid):
            fails.append(f"[K] 動画台帳 video_id文法違反: {vid}")
    for r in renders:
        rk = r.get("render_key")
        if rk and not RENDER_KEY_RE.match(rk):
            fails.append(f"[K] レンダー render_key文法違反: {rk}")
    for c in cuts:
        ck = c.get("cut_key")
        if ck and not CUT_KEY_RE.match(ck):
            fails.append(f"[K] カット台帳 cut_key文法違反: {ck}")

    # [ONE] 採用ちょうど1
    from collections import defaultdict
    adopted = defaultdict(list)
    for r in renders:
        adopt = r.get("adopt") or LEGACY_MAP.get(r.get("adopt_legacy") or "", None) or \
                ("採用" if (r.get("adopt_legacy") == "採用") else None)
        if adopt == "採用":
            vid = r.get("video_id") or extract_video_id(r.get("legacy_video_name") or r.get("title"), vid_set or None)
            adopted[(vid, r.get("variant") or "なし")].append(r)
    for (vid, var), rows in adopted.items():
        if len(rows) > 1:
            fails.append(f"[ONE] ({vid},{var}) 採用行が{len(rows)}本: "
                         + ", ".join(str(r.get('render_key') or r.get('title')) for r in rows))
    for vid in vid_set:
        if not any(k[0] == vid for k in adopted):
            warns.append(f"[ONE] {vid}: 採用行なし(未確定)")

    # [PATH] 非パス値
    for r in renders:
        for f in ("py", "mp4"):
            val = (r.get(f) or "").strip()
            if val and NONPATH.match(val) and not PY_OK_FORM.match(val):
                fails.append(f"[PATH] レンダー{r.get('render_key') or r.get('title')} {f}が非パス値: {val[:50]}")
    for v in videos:
        for f in ("mirror_py", "mirror_mp4"):
            val = (v.get(f) or "").strip()
            if val and NONPATH.match(val) and not PY_OK_FORM.match(val):
                fails.append(f"[PATH] 動画台帳{v.get('video_id')} {f}が非パス値: {val[:50]}")

    # [VOCAB]
    def vocab(rowset, field, canon_key, label):
        canon = CANON[canon_key]
        for row in rowset:
            val = row.get(field)
            if val and val not in canon:
                sug = LEGACY_MAP.get(val)
                msg = f"[VOCAB] {label}: 「{val}」は正規語彙でない" + (f" → 提案: {sug}" if sug else "")
                (fails if a.strict_legacy else warns).append(msg)

    vocab(p.rows("instruction") if "instruction" in p.dbs else [], "status", "instruction", "修正指示DB")
    vocab(renders, "adopt", "render_adopt", "レンダーDB採用状態")
    vocab(p.rows("qa") if "qa" in p.dbs else [], "result", "qa_result", "QAログ結果")
    vocab(videos, "status", "video", "動画台帳ステータス")

    # [REL] relation欠落(情報)
    rel_missing = 0
    for role in ("render", "qa", "instruction", "telop", "cut", "asset_use"):
        if role not in p.dbs or not p.prop(role, "video_rel"):
            continue
        for row in p.rows(role):
            has_key = row.get("video_id") or row.get("video_ids") or \
                      extract_video_id(row.get("legacy_video_name") or row.get("legacy_video_names") or "")
            if has_key and not row.get("video_rel"):
                rel_missing += 1
    if rel_missing:
        warns.append(f"[REL] キーはあるがrelation未設定: {rel_missing}行 → notion_autolink.py --apply を実行")

    # [ORPH] cut_key孤児・プレースホルダ
    for role in ("instruction", "asset_use", "telop"):
        if role not in p.dbs:
            continue
        for row in p.rows(role):
            cid = (row.get("cut_id") or "").strip()
            if cid in ("未確認", "不明", "?"):
                fails.append(f"[ORPH] {role}: cut idがプレースホルダ「{cid}」")
            elif cid and CUT_KEY_RE.match(cid) and cut_keys and cid not in cut_keys:
                fails.append(f"[ORPH] {role}: cut_key孤児 {cid}(カット台帳に無い)")
    for c in cuts:
        if (c.get("cut_id") or "").strip() in ("未確認", "不明"):
            fails.append(f"[ORPH] カット台帳: cut idプレースホルダ({c.get('title')})")

    # [MIR] 鏡列整合
    for v in videos:
        vid = v.get("video_id") or extract_video_id(v.get("title"))
        arows = [r for (k, var), rows in adopted.items() if k == vid for r in rows]
        if not arows:
            continue
        vs = sorted(str(int(r["v"])) for r in arows if r.get("v") is not None)
        mv = v.get("mirror_v") or ""
        if vs and not all(f"v{x}" in mv for x in vs):
            warns.append(f"[MIR] {vid}: 鏡列v({mv[:40]})と採用行(v{','.join(vs)})が不一致 → autolinkで再生成")

    # [STALE]
    if "instruction" in p.dbs:
        vids_with_renders = {r.get("video_id") for r in renders} - {None}
        for row in p.rows("instruction"):
            st = row.get("status")
            tvids = set(re.findall(r"\d{3,4}(?:_\d{2})?", str(row.get("video_ids") or "") +
                                   str(row.get("legacy_video_names") or "")))
            is_all = row.get("all_videos") or "全部" in str(row.get("legacy_video_names") or "")
            if st == "新規" and ((tvids & vids_with_renders) or (is_all and renders)):
                warns.append(f"[STALE] 修正指示「{str(row.get('title'))[:30]}」が新規のままだが対象動画にレンダー行あり")

    print(f"監査対象: {p.titles}")
    print(f"\n=== FAIL ({len(fails)}) ===")
    for f in fails:
        print(" ", f)
    print(f"=== WARN ({len(warns)}) ===")
    for w in warns:
        print(" ", w)
    if fails:
        print("\n❌ FAILあり。解消するまで納品・完了報告不可(契約§8)。")
        return 1
    print("\n✅ 監査PASS(WARNは改善余地)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
