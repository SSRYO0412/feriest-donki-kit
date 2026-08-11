#!/usr/bin/env python3
"""納品前必須ゲート（契約§9）。export → autolink --apply → audit → check_adoption_sync →
check_variant_dupes を直列実行し、結果をプロジェクト台帳(無ければ親ページ本文)へスタンプする。
PASS以外で完了報告禁止。

使い方:
  python3 notion_gate.py <project_page_id> --scan <ローカルpy/レンダーdir> [--scan ...]
      [--cutlist <カットリストJSON>]    # 素材重複チェック(VERSIONING §7)。複数可
      [--max-share N]                   # バッチ横断の使い回し上限(既定は check_variant_dupes 側)
      [--batch-py-ok] [--legacy-py-ok] [--strict-py]  # docstring検査[G]の適用範囲
      [--skip-local]  # SSD未マウント等でローカル検査[A]-[G]を飛ばす(理由がスタンプに残る)
      [--light]       # ★中間チェック用の簡易ゲート: export+audit+ローカル突合のみ・書き込みなし
                      #   (autolink --applyを実行しない/スタンプしない)。作業中に現在地を知るためのもの。
                      #   light の PASS は納品可の意味を持たない。納品前は必ずフルゲートを回す。

★素材重複チェック(check_variant_dupes)は --cutlist を渡さないと実行できない。
  未指定は SKIP として結果に明示され、スタンプにも残る（黙って省いたことにしない）。
  人間・フォーク・外部AIが全員見逃した重複を機械だけが検出した実績がある検査なので、
  カットリストがある案件では必ず渡すこと。
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from notion_rest import Notion, rt
from notion_model import Project, rt_payload, default_log_path


def run(cmd):
    print(f"\n$ {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout[-3000:])
    if r.stderr:
        print(r.stderr[-1000:])
    return r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_page_id")
    ap.add_argument("--scan", action="append", default=[])
    ap.add_argument("--cutlist", action="append", default=[],
                    help="カットリストJSON（素材重複チェック用・複数可）")
    ap.add_argument("--max-share", type=int, default=None,
                    help="バッチ横断で同一素材を使ってよい動画数の上限")
    ap.add_argument("--batch-py-ok", action="store_true")
    ap.add_argument("--legacy-py-ok", action="store_true")
    ap.add_argument("--strict-py", action="store_true")
    ap.add_argument("--skip-local", action="store_true")
    ap.add_argument("--light", action="store_true")
    a = ap.parse_args()

    outdir = str(Path(default_log_path("gate")).parent / f"gate_{time.strftime('%Y%m%d_%H%M%S')}")
    Path(outdir).mkdir(parents=True, exist_ok=True)
    steps = []

    rc = run([sys.executable, str(HERE / "notion_export_adopted.py"), a.project_page_id, "--out", outdir])
    steps.append(("export", rc))

    if a.light:
        steps.append(("autolink", "SKIP(--light: 書き込みなし)"))
    else:
        rc = run([sys.executable, str(HERE / "notion_autolink.py"), a.project_page_id, "--apply",
                  "--log", f"{outdir}/rollback_log.jsonl"])
        steps.append(("autolink", rc))  # rc=2(解決不能あり)はFAIL扱い

    rc = run([sys.executable, str(HERE / "notion_audit.py"), a.project_page_id])
    steps.append(("audit", rc))

    if a.skip_local:
        steps.append(("check_adoption_sync", "SKIP(--skip-local)"))
    elif a.scan:
        cmd = [sys.executable, str(HERE / "check_adoption_sync.py"), *a.scan,
               "--adopted", f"{outdir}/adopted.json", "--renders", f"{outdir}/renders.json"]
        if a.batch_py_ok:
            cmd.append("--batch-py-ok")
        if a.legacy_py_ok:
            cmd.append("--legacy-py-ok")
        if a.strict_py:
            cmd.append("--strict-py")
        rc = run(cmd)
        steps.append(("check_adoption_sync", rc))
    else:
        steps.append(("check_adoption_sync", "SKIP(--scan未指定)"))

    # 素材重複（VERSIONING §7）。人間・フォーク・外部AIが全員見逃した重複を
    # これだけが検出した実績がある。未指定は SKIP として結果に残す（黙って省かない）。
    if a.cutlist:
        cmd = [sys.executable, str(HERE / "check_variant_dupes.py"), *a.cutlist]
        if a.max_share is not None:
            cmd += ["--max-share", str(a.max_share)]
        rc = run(cmd)
        steps.append(("check_variant_dupes", rc))
    else:
        steps.append(("check_variant_dupes", "SKIP(--cutlist未指定)"))

    ok = all(rc == 0 for _, rc in steps if isinstance(rc, int))
    verdict = "PASS" if ok else "FAIL"
    detail = " / ".join(f"{name}={'OK' if rc == 0 else rc}" for name, rc in steps)

    if a.light:
        print(f"\n{'✅' if ok else '❌'} 簡易ゲート{verdict}: {detail} (log: {outdir})")
        print("★これは中間チェック（書き込み・スタンプなし）。lightのPASSは納品可を意味しない。"
              "納品前は必ずフルゲート（--lightなし）を回すこと。")
        return 0 if ok else 1

    stamp = f"{time.strftime('%Y-%m-%d %H:%M')} 納品ゲート{verdict}: {detail} (log: {outdir})"
    print(f"\n{'✅' if ok else '❌'} {stamp}")

    n = Notion()
    p = Project(n, a.project_page_id)
    try:
        if "project" in p.dbs and p.prop("project", "gate"):
            rows = p.rows("project")
            if rows:
                prev = rows[0].get("gate") or ""
                n.patch_page(rows[0]["_id"],
                             {p.prop("project", "gate"): rt_payload((stamp + "\n" + prev)[:1900])})
            else:
                n.append_blocks(p.page_id, [{"object": "block", "type": "paragraph",
                                             "paragraph": {"rich_text": rt(stamp)}}])
        else:
            n.append_blocks(p.page_id, [{"object": "block", "type": "paragraph",
                                         "paragraph": {"rich_text": rt(stamp)}}])
        print("スタンプ記録済み(プロジェクト台帳/親ページ)")
    except RuntimeError as e:
        print(f"WARN: スタンプ記録失敗: {e}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
