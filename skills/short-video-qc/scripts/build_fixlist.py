#!/usr/bin/env python3
"""検品結果を「修正指示書」に変換する枠を作る（テンポ5段階判定の③〜⑤を強制する）。

なぜ要るか:
  検品は「どこがダメか」までしか出さない。制作側が必要とするのは
  「何に差し替えるか」であり、そこには③妥当性判断→④他素材から5候補→⑤5択
  という工程が要る。この工程を飛ばすと、指摘が指摘のまま放置される。

このスクリプトがやること:
  qc/tempo_report.json（codex_flagged など）と qc/codex_view/ の指摘を集めて、
  修正項目ごとに「未記入の必須欄」を持つ fixlist.json の骨組みを作る。
  ★点数や結論は書かない。埋めるのは人／Codexで、埋まるまで validate が通らない。

必須欄（1つでも空なら validate が FAIL）:
  step3_judgement : 動画種別 / 内容 / 前後の意味の繋がり / テロップとの関係 の4軸
  step4_candidates: 他素材の全時間窓からの候補（5件・seen必須）
                    ★seenは2系統を認める（2026-07-29 ユーザー承認）:
                      seen_claude … Claudeが1枚ずつReadした（evidence_scan.pyで検証）
                      seen_codex  … G20の素材全数観察でCodexが見た（coverage_verify.pyで検証済み）
                    却下候補は seen_codex で足りる。**採用した候補は seen_claude が必須**
                    （採用＝差し替え先なので、実物を自分の目で確認せずに指示を出さない）
  step5_choice    : 候補が無い場合の5択(a)〜(e)を全部スコア。(e)は codex_approval 必須
  decision        : 最終的に何をどう差し替えるか（実行可能な粒度で）

使い方:
  python3 build_fixlist.py <プロジェクトルート>            # 骨組みを作る
  python3 build_fixlist.py <プロジェクトルート> --validate  # 未記入を検査（空があれば exit 1）
"""
import sys, json, os, argparse

REQUIRED = ["step3_judgement", "step4_candidates", "step5_choice", "decision"]
AXES = ["video_type", "content", "context", "telop"]
CHOICES = ["a_zoom_crop", "b_back_to_main", "c_trim_speech", "d_rebalance", "e_keep_as_is"]

def skeleton(item_id, source, target, issue, severity):
    return {
        "id": item_id,
        "source": source,                 # どの検査から出た指摘か
        "target": target,                 # 秒数・ファイル名
        "issue": issue,
        "severity": severity,
        "step3_judgement": {a: "" for a in AXES},   # ③妥当性: 4軸すべて記入必須
        "step4_candidates": [],                     # ④候補5件（desc/score/seen_claude|seen_codex/tempo_impact/why/selected）
        "step5_choice": {c: {"score": None, "why": ""} for c in CHOICES},  # ⑤候補が無い場合の5択
        "decision": "",                             # 最終指示（実行可能な粒度）
        "codex_approval": None,                     # (e)を選ぶ場合は必須
    }

def build(root):
    tempo = {}
    tp = f"{root}/qc/tempo_report.json"
    if os.path.exists(tp):
        tempo = json.load(open(tp, encoding="utf-8"))
    items, n = [], 0
    for f in tempo.get("codex_flagged", []):
        n += 1
        items.append(skeleton(f"F-{n:03d}", "tempo_report.codex_flagged",
                              f"{f.get('start')}〜{f.get('end')}秒",
                              f.get("issue", ""), f.get("severity", "")))
    for f in tempo.get("machine_flagged", []):
        n += 1
        items.append(skeleton(f"F-{n:03d}", "tempo_report.machine_flagged",
                              f"{f.get('start')}〜{f.get('end')}秒",
                              "画が変わらない秒数が上限超過", "中"))
    out = {
        "_note": "検品結果を修正指示に変換する枠。必須欄が1つでも空なら validate が FAIL する。",
        "root": root,
        "items": items,
    }
    p = f"{root}/qc/fixlist.json"
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"→ {p}  修正項目 {len(items)}件の骨組みを作成（すべて未記入）")
    return p

def validate(root):
    p = f"{root}/qc/fixlist.json"
    d = json.load(open(p, encoding="utf-8"))
    bad = []
    for it in d["items"]:
        miss = []
        if not all(it["step3_judgement"].get(a) for a in AXES):
            miss.append("step3_judgement(4軸)")
        cands = it.get("step4_candidates") or []
        if len(cands) < 5:
            miss.append(f"step4_candidates(5件必須・現在{len(cands)}件)")
        else:
            for c in cands:
                if not (c.get("seen_claude") or c.get("seen_codex") or c.get("seen")):
                    miss.append("step4_candidates[].seen_claude|seen_codex(見た証拠)")
                    break
            for c in cands:
                if not c.get("tempo_impact"):
                    miss.append("step4_candidates[].tempo_impact")
                    break
            sel = [c for c in cands if c.get("selected")]
            if sel and not all(c.get("seen_claude") for c in sel):
                miss.append("採用候補の seen_claude(Claudeが実際にReadしたパス)")
        # 5択は「候補が無い場合」のみ必須。候補が5件あり decision が埋まっていれば不要
        if not cands and not all(v.get("score") is not None for v in it["step5_choice"].values()):
            miss.append("step5_choice(5択すべてのスコア)")
        if not it.get("decision"):
            miss.append("decision")
        if it.get("decision", "").startswith("e_") and not it.get("codex_approval"):
            miss.append("codex_approval((e)そのまま残す を選ぶ場合は必須)")
        if miss:
            bad.append({"id": it["id"], "target": it["target"], "missing": miss})
    rep = {"total": len(d["items"]), "incomplete": len(bad), "details": bad,
           "verdict": "PASS" if not bad else "FAIL"}
    json.dump(rep, open(f"{root}/qc/fixlist_validation.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"修正項目 {rep['total']}件 / 未記入 {rep['incomplete']}件")
    for b in bad[:20]:
        print(f"  {b['id']} {b['target']}: {', '.join(b['missing'])}")
    sys.exit(0 if not bad else 1)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--validate", action="store_true")
    a = ap.parse_args()
    validate(a.root) if a.validate else build(a.root)
