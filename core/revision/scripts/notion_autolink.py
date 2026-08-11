#!/usr/bin/env python3
"""テキストキー→relation の自動リンカー + 派生キャッシュ生成（契約 §2「スクリプトがコンパイラ」）。

やること(冪等・追記のみ):
 1. video_id 未設定の行に、レガシー列(動画名/対象動画名/タイトル/パス)から video_id を導出して書く
 2. video_id → 動画台帳行への relation を張る(render/qa/instruction/cut/asset_use/telop)
 3. render_key → レンダー行への relation を張る(qa)
 4. 動画台帳の派生キャッシュを採用レンダー行から生成(採用サマリ/mirror_v/mirror_mp4/mirror_py/整合/採用レンダーrelation)
 5. VERSIONING§5書式の履歴行を動画台帳ページ本文へ追記(未追記の採用変更のみ。既存本文と重複させない)

全patchは rollback_log.jsonl に変更前値つきで記録(notion_rollback.pyで逆適用可)。
既定 dry-run。--apply で書き込み。解決不能キーはレポートして続行(exit 2)。

使い方: python3 notion_autolink.py <project_page_id> [--apply] [--log <path>]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from notion_rest import Notion, rt
from notion_model import (Project, PatchLogger, rel_payload, rt_payload, sel_payload,
                          extract_video_id, default_log_path, RENDER_KEY_RE)

LINK_ROLES = ["render", "qa", "instruction", "cut", "asset_use", "telop"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_page_id")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--log", default=None)
    a = ap.parse_args()

    n = Notion()
    p = Project(n, a.project_page_id)
    log = PatchLogger(n, a.log or default_log_path("autolink"), dry_run=not a.apply)
    unresolved = []

    videos = p.rows("video")
    vid_index = {}
    for v in videos:
        vid = v.get("video_id") or extract_video_id(v.get("title"))
        if vid:
            vid_index[vid] = v
    # 動画台帳のvideo_id補完
    vprop = p.prop("video", "video_id")
    for v in videos:
        if not v.get("video_id"):
            vid = extract_video_id(v.get("title"))
            if vid and vprop:
                log.patch(v["_id"], vprop, rt_payload(vid), before_plain=v.get("video_id"),
                          note=f"video_id導出({v.get('title')})")
                v["video_id"] = vid

    renders = p.rows("render") if "render" in p.dbs else []
    rk_index = {}
    for r in renders:
        # video_id / render_key の補完
        vid = r.get("video_id") or               extract_video_id(r.get("legacy_video_name") or r.get("title"), set(vid_index) or None) or               extract_video_id(r.get("py") or r.get("mp4"), set(vid_index) or None)
        if vid and not r.get("video_id") and p.prop("render", "video_id"):
            log.patch(r["_id"], p.prop("render", "video_id"), rt_payload(vid),
                      note=f"video_id導出({r.get('title')})")
            r["video_id"] = vid
        rk = r.get("render_key")
        if r.get("v") is None and r.get("v_legacy"):
            import re as _re
            m = _re.search(r"v(\d+)", str(r["v_legacy"]))
            if m:
                r["v"] = int(m.group(1))
                if p.prop("render", "v"):
                    log.patch(r["_id"], p.prop("render", "v"), {"number": r["v"]},
                              note="v番号textから数値化")
        if not rk and vid and r.get("v") is not None:
            var = (r.get("variant") or "")
            suf = "" if not var or var == "なし" else "_" + var.split("_")[0]
            rk = f"{vid}_v{int(r['v'])}{suf}"
            if p.prop("render", "render_key"):
                log.patch(r["_id"], p.prop("render", "render_key"), rt_payload(rk),
                          note="render_key合成")
                r["render_key"] = rk
        if rk:
            rk_index[rk] = r

    # --- 2. video relation を全roleで張る ---
    for role in LINK_ROLES:
        if role not in p.dbs:
            continue
        rel_prop = p.prop(role, "video_rel")
        if not rel_prop:
            continue
        for row in (renders if role == "render" else p.rows(role)):
            existing = row.get("video_rel") or []
            vid = row.get("video_id") or extract_video_id(
                row.get("legacy_video_name") or row.get("legacy_video_names") or
                row.get("video_ids") or row.get("title"), set(vid_index) or None)
            if not vid:
                legacy = str(row.get("legacy_video_names") or row.get("legacy_video_name") or "")
                if role == "instruction" and ("全部" in legacy or row.get("all_videos")):
                    if p.prop("instruction", "all_videos") and not row.get("all_videos"):
                        log.patch(row["_id"], p.prop("instruction", "all_videos"), {"checkbox": True},
                                  note="全動画対象へ振替(旧:全部)")
                    continue
                if role == "qa" and ("全" in str(row.get("title") or "") or "全部" in legacy):
                    continue  # 全体QA行は動画単位リンク対象外
                unresolved.append((role, row["_id"], "video_id導出不能", str(row.get("title"))[:40]))
                continue
            # video_id列の補完(汎用)
            vp = p.prop(role, "video_id") or p.prop(role, "video_ids")
            cur = row.get("video_id") or row.get("video_ids")
            if vp and not cur:
                log.patch(row["_id"], vp, rt_payload(vid), note=f"{role}: video_id補完")
            target = vid_index.get(vid)
            if not target:
                unresolved.append((role, row["_id"], f"動画台帳に{vid}が無い", str(row.get("title"))[:40]))
                continue
            if target["_id"].replace("-", "") not in [x.replace("-", "") for x in existing]:
                log.patch(row["_id"], rel_prop, rel_payload(target["_id"]),
                          before_plain=existing, note=f"{role}: 動画relation({vid})")

    # --- 3. qa: render_key → レンダー relation ---
    if "qa" in p.dbs and p.prop("qa", "render_rel"):
        for row in p.rows("qa"):
            rk = row.get("render_key")
            if not rk:
                continue
            r = rk_index.get(rk)
            if not r:
                unresolved.append(("qa", row["_id"], f"render_key解決不能: {rk}", ""))
                continue
            existing = row.get("render_rel") or []
            if r["_id"].replace("-", "") not in [x.replace("-", "") for x in existing]:
                log.patch(row["_id"], p.prop("qa", "render_rel"), rel_payload(r["_id"]),
                          before_plain=existing, note=f"qa: レンダーrelation({rk})")

    # --- 4. 動画台帳の派生キャッシュ + 5. 履歴追記 ---
    adopted_by_vid = {}
    for r in renders:
        adopt = r.get("adopt") or {"採用": "採用", "不採用": "却下", "検品待ち": "未判定",
                                   "破棄予定": "却下", "参考": "却下"}.get(r.get("adopt_legacy") or "")
        if adopt == "採用" and r.get("video_id"):
            adopted_by_vid.setdefault(r["video_id"], []).append(r)

    for vid, v in vid_index.items():
        arows = adopted_by_vid.get(vid, [])
        if not arows:
            if p.prop("video", "integrity"):
                log.patch(v["_id"], p.prop("video", "integrity"), sel_payload("未リンク"),
                          before_plain=v.get("integrity"), note=f"{vid}: 採用レンダー行なし")
            continue
        # relation
        want = sorted(r["_id"] for r in arows)
        have = sorted(x for x in (v.get("adopted_rel") or []))
        if [w.replace("-", "") for w in want] != [h.replace("-", "") for h in have]:
            log.patch(v["_id"], p.prop("video", "adopted_rel"), rel_payload(*want),
                      before_plain=have, note=f"{vid}: 採用レンダーrelation({len(want)}本)")
        # サマリ・鏡列
        def vlabel(r):
            var = r.get("variant")
            pre = "" if not var or var == "なし" else f"{var}: "
            return pre

        summary = " / ".join(f"{vlabel(r)}v{int(r['v'])} {r.get('mp4') or '(MP4パス未記入)'}"
                             for r in arows if r.get("v") is not None)
        pairs = [("adopted_summary", summary),
                 ("mirror_v", " / ".join(f"{vlabel(r)}v{int(r['v'])}" for r in arows if r.get("v") is not None)),
                 ("mirror_mp4", " / ".join(f"{vlabel(r)}{r.get('mp4')}" for r in arows if r.get("mp4"))),
                 ("mirror_py", " / ".join(f"{vlabel(r)}{r.get('py')}" for r in arows if r.get("py")))]
        for logical, val in pairs:
            prop = p.prop("video", logical)
            if prop and val and (v.get(logical) or "") != val:
                log.patch(v["_id"], prop, rt_payload(val), before_plain=v.get(logical),
                          note=f"{vid}: {logical}鏡生成")
        if p.prop("video", "integrity") and v.get("integrity") != "OK":
            log.patch(v["_id"], p.prop("video", "integrity"), sel_payload("OK"),
                      before_plain=v.get("integrity"), note=f"{vid}: 整合OK")
        # 履歴追記(§5書式)。既存本文と重複しないよう「render_key採用」の行を探してから
        hist = time.strftime("%Y-%m-%d") + ": " + " / ".join(
            f"{vlabel(r)}v{int(r['v'])}採用 (py={r.get('py') or '?'})" for r in arows if r.get("v") is not None)
        marker = " / ".join(f"{vlabel(r)}v{int(r['v'])}採用" for r in arows if r.get("v") is not None)
        try:
            body = n.block_children(v["_id"])
            texts = []
            for b in body:
                t = b.get(b.get("type"), {})
                texts.append("".join(x.get("plain_text", "") for x in t.get("rich_text", [])))
            if marker and not any(marker in t for t in texts):
                if not a.apply:
                    print(f"  (dry) {vid}: 履歴追記 -> {hist}")
                else:
                    n.append_blocks(v["_id"], [{"object": "block", "type": "paragraph",
                                                "paragraph": {"rich_text": rt(hist)}}])
                    print(f"  {vid}: 履歴追記 -> {hist}")
        except RuntimeError as e:
            print(f"WARN: {vid} 本文追記失敗: {e}")

    print(f"\n{'✅ APPLY' if a.apply else '(dry-run)'} patch数={log.count} / log={log.log_path}")
    if unresolved:
        print(f"⚠ 解決不能 {len(unresolved)}件(要人間/エージェント判断):")
        for role, pid, why, hint in unresolved[:20]:
            print(f"  [{role}] {pid} {why} {hint}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
