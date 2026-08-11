#!/usr/bin/env python3
"""カットリストの素材重複 機械チェック（VERSIONING.md §7）。

人間の目視・フォークの自己申告・外部AI検証のいずれも見逃した重複を検出した実績がある
（案件V 0181_04 cut03 が v1/v2/v3 全てで同一クリップだった事故）。バリアント設計後・
レンダー前・納品前監査で必ず実行する。

チェック内容:
  [1] 同一動画内の素材重複（1カット=1素材ルール。前半/後半分割の2カット化も検出=同relは即NG）
  [2] バリアント間のカット位置ごと素材重複（同一台本のv1/v2/v3で cut i の素材が全て異なること）
  [3] バッチ横断の使い回し上限（同一relを使ってよい動画数の上限。既定3）

入力JSON形式（両対応）:
  {"0285_v1": [{"sid":"01","rel":"...","tin":2.0,...}, ...], "0285_v2": [...]}
  {"0285_v1": [["01","rel...",2.0,1.8,"text"], ...]}                # buildスクリプトのEリスト形式

使い方:
  python3 check_variant_dupes.py cutlists.json [more.json ...] \
      [--max-share 3] [--exempt REL ...] [--no-position-check]

バリアントの自動グループ化: 動画ID末尾の `_v<数字>` を外した名前が同じものを同一台本の
バリアント集合とみなす（0285_v1/0285_v2/0285_v3 → グループ 0285）。
異なる命名の場合は --group "idA,idB,idC" で明示する（複数回指定可）。

exit code: 違反ゼロ=0 / 違反あり=1
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

VSUF = re.compile(r"_v\d+$", re.IGNORECASE)


def load_cutlists(paths):
    data = {}
    for p in paths:
        d = json.loads(Path(p).read_text())
        if not isinstance(d, dict):
            sys.exit(f"{p}: トップレベルは {{動画ID: [cuts...]}} の dict であること")
        for vid, cuts in d.items():
            norm = []
            for c in cuts:
                if isinstance(c, dict):
                    norm.append({"sid": str(c.get("sid", len(norm) + 1)), "rel": c["rel"]})
                else:  # list/tuple: [sid, rel, tin, dur, text, ...]
                    norm.append({"sid": str(c[0]), "rel": c[1]})
            if vid in data:
                sys.exit(f"動画ID重複: {vid}（複数ファイルに同一IDがある。統合してから実行）")
            data[vid] = norm
    return data


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cutlists", nargs="+", help="カットリストJSON")
    ap.add_argument("--max-share", type=int, default=3,
                    help="同一relを使ってよい動画数の上限（既定3。案件ルールに合わせる）")
    ap.add_argument("--exempt", action="append", default=[],
                    help="チェック[1][3]から除外するrel（部分一致）。乱用しない")
    ap.add_argument("--group", action="append", default=[],
                    help='バリアント集合の明示 "idA,idB,idC"（省略時は _v<N> サフィックスで自動グループ化）')
    ap.add_argument("--no-position-check", action="store_true",
                    help="チェック[2]を省略（単発動画のみのバッチ用）")
    args = ap.parse_args()

    data = load_cutlists(args.cutlists)
    exempt = tuple(args.exempt)
    is_exempt = lambda rel: any(e in rel for e in exempt)
    issues = []

    # [1] 同一動画内の素材重複
    for vid, cuts in data.items():
        cnt = Counter(c["rel"] for c in cuts if not is_exempt(c["rel"]))
        for rel, n in cnt.items():
            if n > 1:
                sids = [c["sid"] for c in cuts if c["rel"] == rel]
                issues.append(f"[1] {vid}: 同一素材が{n}カットで使用 (sid={','.join(sids)}) {rel}")

    # [2] バリアント間のカット位置ごと重複
    if not args.no_position_check:
        groups = defaultdict(list)
        explicit = set()
        for g in args.group:
            ids = [x.strip() for x in g.split(",") if x.strip()]
            groups[ids[0] + "(明示)"] = ids
            explicit.update(ids)
        for vid in data:
            if vid in explicit:
                continue
            base = VSUF.sub("", vid)
            if base != vid:
                groups[base].append(vid)
        for base, ids in sorted(groups.items()):
            ids = [i for i in ids if i in data]
            if len(ids) < 2:
                continue
            n_cuts = min(len(data[i]) for i in ids)
            if len({len(data[i]) for i in ids}) > 1:
                issues.append(f"[2] {base}: バリアント間でカット数が不一致 " +
                              ", ".join(f"{i}={len(data[i])}" for i in ids) + "（設計を確認）")
            for pos in range(n_cuts):
                rels = {i: data[i][pos]["rel"] for i in ids}
                cnt = Counter(rels.values())
                for rel, n in cnt.items():
                    if n > 1:
                        dup_ids = [i for i, r in rels.items() if r == rel]
                        issues.append(f"[2] {base} cut位置{pos + 1}(sid={data[ids[0]][pos]['sid']}): "
                                      f"{n}バリアントで同一素材 ({','.join(dup_ids)}) {rel}")

    # [3] バッチ横断の使い回し上限
    rel_videos = defaultdict(set)
    for vid, cuts in data.items():
        for c in cuts:
            if not is_exempt(c["rel"]):
                rel_videos[c["rel"]].add(vid)
    for rel, vids in sorted(rel_videos.items(), key=lambda kv: -len(kv[1])):
        if len(vids) > args.max_share:
            issues.append(f"[3] 使い回し上限超過: {len(vids)}本(上限{args.max_share}) {rel}\n"
                          f"      使用動画: {', '.join(sorted(vids))}")

    n_videos = len(data)
    n_cuts = sum(len(c) for c in data.values())
    print(f"検査対象: {n_videos}動画 / {n_cuts}カット / ユニーク素材 {len(rel_videos)}件")
    print()
    for i in issues:
        print("FAIL", i)
    if issues:
        print(f"\n❌ 違反 {len(issues)} 件。素材を差し替えてから再実行（内容の正確性が保てない差し替えは"
              f"無理をせず、上限を守れない事情を報告に明記して判断を仰ぐ）。")
        return 1
    print("✅ 素材重複なし（同一動画内・バリアント位置・バッチ上限すべてOK）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
