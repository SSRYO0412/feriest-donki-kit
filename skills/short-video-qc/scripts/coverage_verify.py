#!/usr/bin/env python3
"""並列全数観察の被覆を機械照合する（自己申告のCOUNTは証拠として使わない）。

なぜ要るか:
  「全数見た」という自己申告は水増しできる。返答本文に全ファイル名が実際に
  列挙されているかを照合し、1枚でも欠ければ不合格にする。
  並列実行では、あるスライスがレート制限や異常終了で落ちても
  「他が成功しているので全体は成功」に見えてしまう。これを防ぐのが本スクリプト。

coverage_check.py との違い:
  coverage_check.py … 単一ディレクトリ × codex_view形式のjson を照合
  coverage_verify.py … 並列出力（wNN.txt が複数）× スライス分割済みディレクトリ を照合
                       欠番がどのスライスで起きたかを特定し、再実行すべきスライスを出す

使い方:
  python3 coverage_verify.py <フレームディレクトリ(wNN/を含む)> <並列出力ディレクトリ> [--out qc/coverage_report.json]

判定:
  欠番が1枚でもあれば exit 1。欠番を含むスライス名を列挙するので、そのスライスだけ再実行する。
"""
import sys, os, json, argparse, collections

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frames_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--out", default="qc/coverage_report.json")
    a = ap.parse_args()

    blob = ""
    slices_seen = []
    for f in sorted(os.listdir(a.out_dir)):
        if f.endswith(".txt") and not f.startswith("_"):
            blob += open(f"{a.out_dir}/{f}", encoding="utf-8", errors="replace").read() + "\n"
            slices_seen.append(f[:-4])

    total, missing = 0, []
    owner = {}
    for s in sorted(os.listdir(a.frames_dir)):
        d = os.path.join(a.frames_dir, s)
        if not os.path.isdir(d):
            continue
        for img in sorted(os.listdir(d)):
            if not img.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            total += 1
            owner[img] = s
            stem = os.path.splitext(img)[0]
            if img not in blob and stem not in blob:
                missing.append(img)

    if total == 0:
        print(f"★{a.frames_dir} にスライス(wNN/)と画像が無い")
        sys.exit(2)

    bad_slices = sorted({owner[m] for m in missing})
    report = {
        "frames_dir": a.frames_dir,
        "out_dir": a.out_dir,
        "total_files": total,
        "listed": total - len(missing),
        "coverage_pct": round((total - len(missing)) / total * 100, 2),
        "missing_count": len(missing),
        "missing_examples": missing[:30],
        "slices_with_missing": bad_slices,
        "slices_responded": slices_seen,
        "verdict": "PASS" if not missing else "FAIL",
        "note": "自己申告のCOUNTではなく、返答本文へのファイル名列挙で判定している",
    }
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(report, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"対象 {total}枚 / 列挙 {total-len(missing)}枚 / 欠番 {len(missing)}枚 / 被覆率 {report['coverage_pct']}%")
    if missing:
        print(f"★再実行が必要なスライス: {bad_slices}")
        print(f"  欠番の例: {missing[:15]}")
        sys.exit(1)
    print("PASS: 全ファイルが返答に列挙されている")

if __name__ == "__main__":
    main()
