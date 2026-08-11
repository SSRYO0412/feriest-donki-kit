#!/usr/bin/env python3
"""variant_confer.py — 複数案×知覚合議（[4]）の準備。案件非依存。

ソルバのパラメータを振ってN案を生成し、各案の rough proxy を合成、
agy / Codex への審査プロンプト一式を出力する。**合議と裁定はClaudeが行い記録する**
（スコアで勝者を決めない——スコアは絞り込み、合格は視聴のみ）。

使い方:
  python3 variant_confer.py <profile> --grid '[{"density":1.0},{"density":0.6},{"reserve":0}]'
出力: work/variants/vN/broll.json + proxy.mp4 + qc/variants_judging.md（審査手順書）
"""
import json, os, sys, subprocess, argparse, shutil

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("profile")
    ap.add_argument("--grid", required=True, help="JSON配列: 各案のソルバparam")
    a = ap.parse_args()
    prof = json.load(open(a.profile, encoding="utf-8"))
    root = prof["root"]
    grid = json.loads(a.grid)

    def P(rel):
        return rel if os.path.isabs(rel) else os.path.join(root, rel)

    vdir = P("work/variants")
    os.makedirs(vdir, exist_ok=True)
    rows = []
    for i, params in enumerate(grid, 1):
        d = os.path.join(vdir, f"v{i}")
        os.makedirs(d, exist_ok=True)
        br = os.path.join(d, "broll.json")
        cmd = [sys.executable, os.path.join(HERE, "select_solver.py"), a.profile,
               "--out", br, "--dry"] + \
              [x for k, v in params.items() for x in ("--param", f"{k}={v}")]
        subprocess.run(cmd, check=True)
        # rough proxy: brollを差し替えて合成（正本は触らない）
        prof2 = dict(prof)
        prof2["artifacts"] = dict(prof["artifacts"])
        prof2["artifacts"]["broll"] = br
        prof2["artifacts"]["proxy_out"] = os.path.join(d, "proxy.mp4")
        pp = os.path.join(d, "profile.json")
        json.dump(prof2, open(pp, "w", encoding="utf-8"), ensure_ascii=False)
        subprocess.run([sys.executable, os.path.expanduser(
            "~/.claude/skills/_video-core/pipeline/scripts/render_proxy.py"), pp],
            check=True)
        rows.append((f"v{i}", params, br, os.path.join(d, "proxy.mp4")))

    md = ["# 複数案の審査（合議はClaudeが行い、結果をここに追記して記録する）", ""]
    for name, params, br, px in rows:
        md += [f"## {name}  params={json.dumps(params, ensure_ascii=False)}",
               f"- broll: {br}", f"- proxy: {px}",
               f"- agy: `agy --print-timeout 20m --sandbox --dangerously-skip-permissions "
               f"--model {prof.get('gemini_model','gemini-3.6-flash-high')} -p \"{px} を通しで視聴し、"
               f"挿入映像の意味一致・流れ・テンポの違和感を時刻付きで列挙\"`",
               f"- Codex(gpt-5.5) 敵対: broll.json と台帳を渡し「1対1不一致/指示語/実演/重複/"
               f"先出しを潰しに行け」", ""]
    md += ["## 裁定（Claude記入欄）", "- 勝者: ", "- グラフト: ", "- 根拠: "]
    op = P("qc/variants_judging.md")
    open(op, "w", encoding="utf-8").write("\n".join(md))
    print(f"{len(rows)}案 → {vdir} / 審査手順 {op}")


if __name__ == "__main__":
    main()
