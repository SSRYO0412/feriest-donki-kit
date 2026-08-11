#!/usr/bin/env python3
"""検品報告の自動生成。制作者（Claude）が点数や「完了」を手書きできない構造にする。

強制事項:
  - 見出し: gates.json に pending/fail が1つでもあれば「【未完了】」に固定。
    「完了」の語はこのスクリプト以外が出力してはならない。
  - 点数: qc/scoring/final.json（合議の結果）が存在するときのみ記載。手書き禁止。
  - 「全数」表記: 分母/分子を必ず併記（このスクリプトが自動挿入）。
  - 未実施工程: 自動列挙。隠せない。

使い方:
  python3 make_report.py <プロジェクトルート> [--out qc/report.md]
"""

# --- VIDEO OPS ライセンスゲート（仕様§4.2・ローカル読取のみ・ネットワークなし） ---
def _vops_require(_feat):
    import sys as _s
    from pathlib import Path as _P
    _h = _P(__file__).resolve()
    _cands = [q for p in _h.parents for q in (p / "ops" / "license", p / "core" / "ops" / "license")]
    _cands.append(_P.home() / ".claude" / "skills" / "_video-core" / "ops" / "license")
    for _c in _cands:
        if (_c / "vops_license.py").exists():
            _s.path.insert(0, str(_c))
            import vops_license as _v
            _v.require(_feat)
            return
    print("⚠ VIDEO OPS: ライセンス機構が見つからない（導通不備）— 続行", file=_s.stderr)


_vops_require("qc")
# --- ゲートここまで ---
import sys, json, os, argparse, datetime

def load(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    R = a.root.rstrip("/")
    out = a.out or f"{R}/qc/report.md"

    gates = load(f"{R}/qc/gates.json")
    if not gates:
        print("★qc/gates.json が無い。Phase 0 から始めること。")
        sys.exit(2)

    rows, not_done = [], []
    for g in gates["gates"]:
        st = g.get("status", "pending")
        ev = g.get("evidence", "")
        ev_exists = os.path.exists(f"{R}/{ev}") if ev else False
        # statusがpassでも証跡ファイルが無ければ未実施として扱う（申告より証跡を優先）
        effective = "pass" if (st == "pass" and ev_exists) else ("fail" if st == "fail" else "pending")
        if effective != "pass":
            not_done.append(g)
        rows.append((g["id"], g["name"], g["executor"], effective,
                     ev if ev_exists else f"{ev}（無し）"))

    n_nd = len(not_done)
    heading = "【未完了】検品報告" if n_nd > 0 else "【検品通過】検品報告"

    lines = [f"# {heading}", "",
             f"- 生成: {datetime.datetime.now().isoformat(timespec='seconds')}",
             f"- 対象: {R}",
             f"- **未実施/不合格: {n_nd}件**", ""]

    if n_nd:
        lines.append("## ★未実施・不合格の工程（これらが揃うまで「検品通過」ではない）")
        for g in not_done:
            lines.append(f"- {g['id']} {g['name']}（実行主体: {g['executor']} / 証跡: {g['evidence']}）")
        lines.append("")

    # 点数は合議ファイルが存在するときのみ
    final = load(f"{R}/qc/scoring/final.json")
    lines.append("## 採点（合議制）")
    if final and "total" in final:
        lines.append(f"- 合意スコア: **{final['total']}点**（{final.get('process','')}）")
        for k, v in (final.get("items") or {}).items():
            lines.append(f"  - {k}: agent {v.get('agent')} / codex {v.get('codex')} → 合意 {v.get('agreed')}")
    else:
        lines.append("- （未採点。qc/scoring/final.json が存在しないため点数は記載できない）")
    lines.append("")

    # 観察の被覆（分母/分子の自動挿入）
    lines.append("## 観察の被覆（全数表記は分母/分子つきでしか書けない）")
    cov = load(f"{R}/qc/coverage_report.json")
    if cov:
        # coverage_check.py は listed_in_response、coverage_verify.py は listed を出す（両対応）
        listed = cov.get("listed_in_response", cov.get("listed"))
        pct = cov.get("coverage_pct")
        pct_s = f"・{pct}%" if pct is not None else ""
        lines.append(f"- Codex観察: {listed}/{cov['total_files']}{pct_s}（{cov['verdict']}）")
    ev = load(f"{R}/qc/evidence_report.json")
    if ev:
        lines.append(f"- Claude実Read: {ev['actually_read_unique']}枚 / 申告 {ev['claimed_count']}件 / 捏造疑い {len(ev['fabricated'])}件（{ev['verdict']}）")
    lines.append("")

    # 機械検査
    mach = load(f"{R}/qc/machine_report.json")
    lines.append("## 機械検査（『壊れていない』の証明であり『良い』の証明ではない）")
    if mach:
        d = mach["duration"]
        lines.append(f"- 尺: {d['actual_sec']}s（設計{d['design_sec']}s）{'OK' if d['ok'] else 'FAIL'}")
        lines.append(f"- 黒フレーム {len(mach['black_frames'])}件 / 孤立 {len(mach['isolated_frames'])}件 / 無音 {len(mach['silences'])}件 / AV差 {mach['av_length_diff_sec']}s")
        lines.append(f"- 画が変わらない区間: {len(mach['no_change_segments'])}件（全件テンポ5段階判定へ）")
    else:
        lines.append("- （未実施）")
    lines.append("")

    # 工程表
    lines.append("## 工程表")
    lines.append("| ID | 工程 | 実行主体 | 状態 | 証跡 |")
    lines.append("|----|------|---------|------|------|")
    for r in rows:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |")
    lines.append("")
    lines.append("> 所見（数値の記載禁止・数値は上のセクションが自動で埋める）:")
    lines.append("> ")

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(lines))
    print(f"→ {out}")
    print(f"見出し: {heading} / 未実施 {n_nd}件")
    sys.exit(0 if n_nd == 0 else 1)

if __name__ == "__main__":
    main()
