#!/usr/bin/env python3
"""レンダー完了ごとの機械起票（契約§9。却下版も1レンダー=1行・QAログの記録漏れを構造的に防ぐ）。

- レンダー行を render_key で冪等upsert(採用状態は既定「未判定」。採用確定は後で採用状態フリップ)
- --qa "種別:結果:内容[:証跡パス]" (複数可) でQAログ行も同時起票(render_key/video_id/relation付き)
- 動画relationは動画台帳から自動解決

使い方(レンダーするたび実行):
  python3 notion_log_render.py <project_page_id> --video-id 0290_01 --v 33 \
      [--variant A_顔なし] --py <fullpath> --mp4 <fullpath> \
      [--intermediates <path>] [--audio <src>] [--bgm <src>] \
      [--adopt 未判定|採用|却下] [--reject-reason "..."] [--evidence "..."] \
      [--qa "目視:OK:全カット窓確認:qa/0290_v33/"] [--apply]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from notion_rest import Notion, rt
from notion_model import (Project, PatchLogger, rt_payload, rel_payload, sel_payload,
                          extract_video_id, default_log_path, RENDER_KEY_RE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_page_id")
    ap.add_argument("--video-id", required=True)
    ap.add_argument("--v", type=int, required=True)
    ap.add_argument("--variant", default=None, help="A_顔なし / B_顔あり 等(案件の選択肢に従う)")
    ap.add_argument("--py", required=True, help="レンダーpyフルパス(無い場合は『py不要(理由: ...)』定型)")
    ap.add_argument("--mp4", required=True)
    ap.add_argument("--intermediates", default=None)
    ap.add_argument("--audio", default=None)
    ap.add_argument("--bgm", default=None)
    ap.add_argument("--adopt", default="未判定", choices=["未判定", "採用", "却下", "旧採用"])
    ap.add_argument("--reject-reason", default=None)
    ap.add_argument("--evidence", default=None)
    ap.add_argument("--qa", action="append", default=[], help='"種別:結果:内容[:証跡パス]"')
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--log", default=None)
    a = ap.parse_args()

    suf = "" if not a.variant or a.variant == "なし" else "_" + a.variant.split("_")[0]
    render_key = f"{a.video_id}_v{a.v}{suf}"
    if not RENDER_KEY_RE.match(render_key):
        sys.exit(f"ERROR: render_key文法違反: {render_key}(契約§1)")

    n = Notion()
    p = Project(n, a.project_page_id)
    log = PatchLogger(n, a.log or default_log_path("log_render"), dry_run=not a.apply)

    video_row = None
    for v in p.rows("video"):
        if (v.get("video_id") or extract_video_id(v.get("title"))) == a.video_id:
            video_row = v
            break
    if not video_row:
        print(f"WARN: 動画台帳に {a.video_id} が無い(relationなしで起票)")

    rprop = lambda l: p.prop("render", l)
    sp = p.schema("render")["properties"]
    title_prop = next(k for k, v in sp.items() if v["type"] == "title")
    props = {
        rprop("render_key"): rt_payload(render_key),
        rprop("video_id"): rt_payload(a.video_id),
        rprop("v"): {"number": a.v},
        rprop("adopt"): sel_payload(a.adopt),
        rprop("py"): rt_payload(a.py),
        rprop("mp4"): rt_payload(a.mp4),
    }
    if a.variant and rprop("variant"):
        props[rprop("variant")] = sel_payload(a.variant)
    if a.reject_reason and rprop("reject_reason"):
        props[rprop("reject_reason")] = rt_payload(a.reject_reason)
    if a.evidence and rprop("evidence"):
        props[rprop("evidence")] = rt_payload(a.evidence)
    for arg, logical, fallback in ((a.intermediates, None, "中間素材フォルダ"),
                                   (a.audio, None, "使用VO"), (a.bgm, None, "使用BGM")):
        if arg and fallback in sp:
            props[fallback] = rt_payload(arg)
    if video_row and rprop("video_rel"):
        props[rprop("video_rel")] = rel_payload(video_row["_id"])

    existing = next((r for r in p.rows("render") if r.get("render_key") == render_key), None)
    if existing:
        for k, v in props.items():
            log.patch(existing["_id"], k, v, note=f"log_render: {render_key}(更新)")
        render_page = existing["_id"]
    else:
        props[title_prop] = {"title": rt(f"{a.video_id} v{a.v}{' ' + a.variant if a.variant else ''}")}
        render_page = log.create(p.dbs["render"], props, note=f"log_render: {render_key}(新規)")
    print(f"{'✅' if a.apply else '(dry)'} レンダー行 {render_key} ({a.adopt})")

    # QAログ起票
    qsp = p.schema("qa")["properties"] if "qa" in p.dbs else {}
    for spec in a.qa:
        parts = spec.split(":")
        kind, result = parts[0], parts[1] if len(parts) > 1 else "OK"
        content = parts[2] if len(parts) > 2 else ""
        evidence = parts[3] if len(parts) > 3 else ""
        qprops = {
            p.prop("qa", "video_id"): rt_payload(a.video_id),
            p.prop("qa", "render_key"): rt_payload(render_key),
            p.prop("qa", "result"): sel_payload(result),
        }
        qtitle = next(k for k, v in qsp.items() if v["type"] == "title")
        if "検品種別" in qsp:
            qprops["検品種別"] = {"multi_select": [{"name": kind}]}
        if "問題内容" in qsp and content:
            qprops["問題内容"] = rt_payload(content)
        elif "確認内容" in qsp and content:
            qprops["確認内容"] = rt_payload(content)
        for name in ("証跡パス", "スクショ/フレーム画像"):
            if name in qsp and evidence and qsp[name]["type"] == "rich_text":
                qprops[name] = rt_payload(evidence)
        if "確認日" in qsp:
            qprops["確認日"] = {"date": {"start": time.strftime("%Y-%m-%d")}}
        if video_row and p.prop("qa", "video_rel"):
            qprops[p.prop("qa", "video_rel")] = rel_payload(video_row["_id"])
        if render_page and render_page != "dry" and p.prop("qa", "render_rel"):
            qprops[p.prop("qa", "render_rel")] = rel_payload(render_page)
        qprops[qtitle] = {"title": rt(f"QA_{render_key}_{kind}")}
        log.create(p.dbs["qa"], qprops, note=f"log_render: QA {render_key} {kind}")
        print(f"{'✅' if a.apply else '(dry)'} QAログ {render_key} {kind}:{result}")

    print(f"\npatch/create数={log.count} / log={log.log_path}")
    print("採用確定時: レンダー行の採用状態を「採用」へ、旧採用行を「旧採用」へフリップ →"
          " notion_autolink.py --apply で鏡列・履歴が生成される")
    return 0


if __name__ == "__main__":
    sys.exit(main())
