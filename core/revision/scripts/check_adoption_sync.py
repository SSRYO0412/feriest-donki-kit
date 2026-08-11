#!/usr/bin/env python3
"""採用版とローカルファイルの突合検算（VERSIONING.md §7）。

ローカルのレンダーpy/出力MP4をスキャンして動画IDごとの最新vを集計し、
管理DB(Notion動画台帳)からエクスポートした採用情報JSONと突き合わせる。

検出する不整合:
  [A] 採用vより新しいvがローカルに存在するのに採用記録が古いまま（DB更新漏れの疑い）
  [B] 採用vのMP4に対応するpyがローカルに見つからない（再生成不能）
  [C] 採用記録のパス(mp4/py)がローカルに実在しない
  [D] 同一(動画ID, v)のpyが複数ある（どれが正か曖昧）
  [E] MP4があるのに同じvのpyが無い（正本欠落。バッチpy運用なら--batch-py-okで抑制）
  [F] ローカルに存在する(動画ID, v)に対応するレンダー行が管理DBに無い（--renders指定時。
      却下版も1レンダー=1行で登録する契約の登録漏れ検出。notion_export_adopted.pyのrenders.jsonを渡す）
  [G] レンダーpyに「変更内容」「変更理由」を含むdocstringヘッダが無い（VERSIONING.md §2.1。
      py自身を修正記録の一次資料にする契約）。
      ★遡及しない（notion-db-contract.md §10「過去案件には遡及強制しない・新規からFAIL適用」）:
      規約制定日(2026-08-10)より新しいpyだけFAIL、それ以前のpyはWARN。
      --strict-py で全FAIL / --legacy-py-ok で全WARN に上書きできる。

使い方:
  python3 check_adoption_sync.py <scan_dir> [<scan_dir2> ...] \
      [--adopted adopted.json] [--renders renders.json] [--vid-pattern REGEX] [--batch-py-ok]

adopted.json の形式（Notion動画台帳から手動/MCPで書き出す）:
  {
    "0290": {"v": 32, "mp4": "/path/to/mov_..._v32.mp4", "py": "/path/to/render_0290_v32_ctafix.py"},
    "0181_05": {"v": 3,  "mp4": "...", "py": "..."}
  }
  ※ バリアント(顔あり/なし等)は "0290_noface" のようにID側で区別して両方登録する。

--vid-pattern: ファイル名から動画IDを抜く正規表現（named group 'vid' 必須）。
  既定: r'(?P<vid>\\d{3,4}(?:_\\d{2})?)'  （例: 0290 / 0181_05）
v の抽出: ファイル名中の '_v<数字>' または '-v<数字>'（最後に現れたもの）。

exit code: 不整合ゼロ=0 / 不整合あり=1
"""
import argparse
import ast
import datetime as dt
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

V_RE = re.compile(r"[_\-]v(\d+)(?=[._\-]|$)", re.IGNORECASE)
DEFAULT_VID_RE = r"(?P<vid>\d{3,4}(?:_\d{2})?)"

# [G] docstring規約(VERSIONING §2.1)の制定日。これより古いpyは非遡及でWARN。
# mtimeは編集・コピーで動くので厳密な作成日ではない（コピーで新しくなる＝安全側にFAIL）。
# 判定を機械的に固定したい場合は --strict-py / --legacy-py-ok で明示する。
DOCSTRING_RULE_EPOCH = dt.datetime(2026, 8, 10).timestamp()


def extract(name: str, vid_re: re.Pattern):
    """ファイル名から (vid, v) を抜く。どちらか取れなければ None。"""
    mv = None
    for m in V_RE.finditer(name):
        mv = int(m.group(1))  # 最後の _v<NN> を採用
    if mv is None:
        return None
    mi = vid_re.search(name)
    if not mi:
        return None
    return mi.group("vid"), mv


def docstring_ok(path: Path):
    """VERSIONING.md §2.1: モジュールdocstringに「変更内容」「変更理由」の両方があるか。
    構文エラー等で読めない場合も False（ヘッダ検査不能=契約不履行として扱う）。"""
    try:
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8", errors="replace")))
    except SyntaxError:
        return False
    return bool(doc) and "変更内容" in doc and "変更理由" in doc


def scan(dirs, vid_re):
    pys = defaultdict(list)   # (vid, v) -> [Path]
    mp4s = defaultdict(list)  # (vid, v) -> [Path]
    for d in dirs:
        for p in Path(d).rglob("*"):
            if not p.is_file():
                continue
            if p.suffix == ".py":
                r = extract(p.name, vid_re)
                if r:
                    pys[r].append(p)
            elif p.suffix.lower() in (".mp4", ".mov"):
                r = extract(p.name, vid_re)
                if r:
                    mp4s[r].append(p)
    return pys, mp4s


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scan_dirs", nargs="+")
    ap.add_argument("--adopted", help="採用情報JSON（動画台帳エクスポート）")
    ap.add_argument("--renders", help="全レンダー行JSON（notion_export_adopted.pyのrenders.json。検査[F]用）")
    ap.add_argument("--vid-pattern", default=DEFAULT_VID_RE)
    ap.add_argument("--batch-py-ok", action="store_true",
                    help="バッチpy運用（1つのpyが複数動画を出す）のため [E] py欠落を警告に留める")
    ap.add_argument("--legacy-py-ok", action="store_true",
                    help="[G] docstringヘッダ欠落を常にWARNへ降格（既定は規約制定日以降のpyのみFAIL）")
    ap.add_argument("--strict-py", action="store_true",
                    help="[G] を全pyにFAIL適用（非遡及の既定を外す。案件の全pyを規約準拠にした後の維持用）")
    args = ap.parse_args()
    if args.legacy_py_ok and args.strict_py:
        sys.exit("--legacy-py-ok と --strict-py は同時指定できない")

    vid_re = re.compile(args.vid_pattern)
    if "vid" not in vid_re.groupindex:
        sys.exit("--vid-pattern には named group (?P<vid>...) が必要")

    pys, mp4s = scan(args.scan_dirs, vid_re)
    adopted = {}
    if args.adopted:
        adopted = json.loads(Path(args.adopted).read_text())
    render_rows = None
    if args.renders:
        rows = json.loads(Path(args.renders).read_text())
        render_rows = {(r.get("video_id"), int(r["v"])) for r in rows
                       if r.get("video_id") and r.get("v") is not None}

    issues, warns = [], []
    all_vids = sorted({k[0] for k in pys} | {k[0] for k in mp4s} | set(adopted))

    print(f"{'動画ID':<12}{'py最新v':>8}{'mp4最新v':>9}{'採用v':>7}  状態")
    print("-" * 60)
    for vid in all_vids:
        py_vs = sorted(v for (i, v) in pys if i == vid)
        mp4_vs = sorted(v for (i, v) in mp4s if i == vid)
        py_max = py_vs[-1] if py_vs else None
        mp4_max = mp4_vs[-1] if mp4_vs else None
        ad = adopted.get(vid, {})
        ad_v = ad.get("v")
        marks = []

        local_max = max([x for x in (py_max, mp4_max) if x is not None], default=None)
        if ad_v is not None and local_max is not None and local_max > ad_v:
            issues.append(f"[A] {vid}: ローカル最新 v{local_max} > 採用 v{ad_v} — DB更新漏れ or 未採用の新版。動画台帳を確認せよ")
            marks.append("A")
        if ad_v is not None and (vid, ad_v) not in pys:
            if args.batch_py_ok:
                warns.append(f"[B] {vid}: 採用 v{ad_v} の単体pyが無い（バッチpy運用として許容。pyパスを動画台帳で確認）")
            else:
                issues.append(f"[B] {vid}: 採用 v{ad_v} を再生成できるpyがローカルに無い")
                marks.append("B")
        for key in ("mp4", "py"):
            path = ad.get(key)
            if path and not Path(path).exists():
                issues.append(f"[C] {vid}: 採用記録の{key}パスが実在しない: {path}")
                marks.append("C")
        for v in py_vs:
            files = pys[(vid, v)]
            if len(files) > 1:
                issues.append(f"[D] {vid}: v{v} のpyが{len(files)}個ある: " + ", ".join(f.name for f in files))
                marks.append("D")
            for f in files:
                if docstring_ok(f):
                    continue
                msg = f"[G] {vid}: {f.name} にdocstringヘッダ(変更内容/変更理由)が無い（VERSIONING §2.1）"
                if args.strict_py:
                    legacy = False
                elif args.legacy_py_ok:
                    legacy = True
                else:  # 既定: 非遡及（規約制定日より古いpyはWARN）
                    legacy = f.stat().st_mtime < DOCSTRING_RULE_EPOCH
                if legacy:
                    warns.append(msg + "（規約制定日より前のpy＝非遡及でWARN。直すなら次の版から）")
                else:
                    issues.append(msg)
                    marks.append("G")
        for v in mp4_vs:
            if (vid, v) not in pys:
                msg = f"[E] {vid}: v{v} のMP4に同vのpyが無い"
                if args.batch_py_ok:
                    warns.append(msg + "（バッチpy運用として許容）")
                else:
                    issues.append(msg)
                    marks.append("E")

        if render_rows is not None:
            base_vid = vid.split("_")[0] if not re.match(r"^\d{3,4}_\d{2}$", vid) else vid
            for v in sorted(set(py_vs) | set(mp4_vs)):
                if (vid, v) not in render_rows and (base_vid, v) not in render_rows:
                    issues.append(f"[F] {vid}: v{v} のレンダー行が管理DBに無い(却下版も1レンダー=1行で登録する契約)")
                    marks.append("F")

        print(f"{vid:<12}{str(py_max or '-'):>8}{str(mp4_max or '-'):>9}{str(ad_v if ad_v is not None else '-'):>7}  {','.join(sorted(set(marks))) or 'OK'}")

    print()
    for w in warns:
        print("WARN", w)
    for i in issues:
        print("FAIL", i)
    if not adopted:
        print("NOTE: --adopted 未指定のためローカル整合([D][E])のみ検査した。納品前は必ず動画台帳エクスポートと突合すること。")
    print()
    if issues:
        print(f"❌ 不整合 {len(issues)} 件。解消するまで「完了」報告・納品をしないこと（VERSIONING.md §4/§7）。")
        return 1
    print("✅ 採用整合OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
