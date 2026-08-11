#!/usr/bin/env python3
"""Codex観察の被覆検証: 返答本文に対象ディレクトリの全ファイル名が列挙されているかを機械照合する。

なぜ要るか:
  「全数見た」という自己申告だけでは水増しできる。返答本文にファイル名が1行ずつ
  現れることを機械チェックし、欠番があれば不合格にする。
  （51枚丸投げテストで、正しい全数処理なら s001〜s051 が返答に全て現れることを確認済み）

使い方:
  python3 coverage_check.py <対象ディレクトリ> <codex_view保存json（複数可）> [--out qc/coverage_report.json]

判定:
  各ファイルについて、次のいずれかが response に現れれば「列挙あり」とみなす:
    ①完全なファイル名 ②拡張子を除いたstem ③stemの先頭トークン（[_ .]区切り）が
    ディレクトリ内で一意な場合のみそのトークン（例: s020_B_032.767.jpg → "s020"）。
  1つでも現れなければ exit 1。
  ※依頼テンプレ側でも「完全なファイル名を行頭に書く」ことを要求する（CODEX.md）。
"""
import sys, json, os, argparse, re

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target_dir")
    ap.add_argument("views", nargs="+")
    ap.add_argument("--out", default="qc/coverage_report.json")
    a = ap.parse_args()

    files = sorted(f for f in os.listdir(a.target_dir)
                   if re.search(r"\.(jpg|jpeg|png|webp)$", f, re.I))
    if not files:
        print(f"★対象ディレクトリに画像が無い: {a.target_dir}")
        sys.exit(2)

    blob = ""
    self_reports = []
    for vp in a.views:
        d = json.load(open(vp, encoding="utf-8"))
        blob += d.get("response", "") + "\n"
        if d.get("self_reported"):
            self_reports.append(d["self_reported"])

    # 先頭トークン（一意なもののみ許容）
    def head(f):
        return re.split(r"[_.]", os.path.splitext(f)[0])[0]
    from collections import Counter
    head_count = Counter(head(f) for f in files)

    missing = []
    for f in files:
        stem = os.path.splitext(f)[0]
        h = head(f)
        ok = (f in blob) or (stem in blob) or (head_count[h] == 1 and h in blob)
        if not ok:
            missing.append(f)

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    report = {
        "target_dir": a.target_dir,
        "total_files": len(files),
        "listed_in_response": len(files) - len(missing),
        "missing": missing,
        "self_reported": self_reports,
        "verdict": "PASS" if not missing else "FAIL",
    }
    json.dump(report, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"対象 {len(files)}枚 / 返答に列挙 {len(files)-len(missing)}枚 / 自己申告 {self_reports}")
    if missing:
        print(f"★欠番 {len(missing)}件: {missing[:20]}")
        sys.exit(1)
    print("PASS: 全ファイルが返答に列挙されている")

if __name__ == "__main__":
    main()
