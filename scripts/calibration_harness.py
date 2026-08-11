#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G92 較正ハーネス — レビュー機構が「実際に何を捕まえられるか」を数字にする。

★「Claudeでレビューしています」は品質の主張として空である。
   この案件で実際に起きた欠陥（.fork/known_defects.json）を意図的に注入し直し、
   **既知欠陥N件中M件を検出した／未検出はこれ** と言えるようにするための装置。

★Codex が無い環境で「検品通過」を名乗る根拠はここにしかない。
   隔離もレンズ分割も『共有文脈バイアス』を消すだけで、同一モデルの盲点は消えない。
   その残余がどれくらいかは、測って報告する以外に誠実な扱い方がない。

2つのモードがある。

  mechanical  欠陥を build/mp4 に実際に注入して機械ゲートを回し、
              「鳴るはずのゲートが鳴ったか」を自動で判定する。人の申告に依存しない。
  packet      機械では判定できない欠陥（訴求の弱さ・画の重複・ラベルと実画の食い違い）を
              注入した成果物とレンズ指示に仕立てて qc/calibration/packets/ に出す。
              隔離サブエージェントに渡し、返答を --score で取り込んで検出率を出す。

  python3 scripts/calibration_harness.py mechanical --build design/build_0801.json \\
      --mp4 <完成MP4> --out qc/calibration
  python3 scripts/calibration_harness.py packet     --build design/build_0801.json --out qc/calibration
  python3 scripts/calibration_harness.py score      --out qc/calibration
"""
import argparse, copy, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def P(*a): return os.path.join(ROOT, *a)

DEFECTS = json.load(open(P(".fork/known_defects.json"), encoding="utf-8"))
MATCHER = P("scripts/reference_match.py")


# ---------------------------------------------------------------- 注入

def rule_D2():
    """テロップ色が背景に埋もれるのを弾けるか。

    ★これだけは build/mp4 への注入では試せない。宣言色だけ変えても画素は元のままなので、
      宣言と焼き込みが食い違った偽の状況を測ることになる（＝何も検証していない）。
      判定するのは規則そのものなので、実際に踏んだ値と参考の実測値で直接テストする。

    ★この項目を作った時点では、背景を「テロップ色から60以上離れた画素」で定義していたため
      ΔRGB が構造的に60を下回れず、規則が原理的に空振りしていた。ハーネスがそれを検出した。
      背景をフチの幾何で取る実装に直してある。
    """
    T = json.load(open(P(".fork/REFERENCE-TARGETS.json"), encoding="utf-8"))["telop_contrast"]
    sys.path.insert(0, P("scripts"))
    from reference_match import dist, hex2rgb
    mind = T["min_delta"]
    cases = [(T["known_failure"]["telop"], T["known_failure"]["bg"], False,
              "実際に読めなくなった組み合わせ"),
             (T["samples"][0]["telop"], T["samples"][0]["bg"], True, "参考の実測（帯の下限側）"),
             (T["samples"][1]["telop"], T["samples"][1]["bg"], True, "参考の実測（帯の上限側）")]
    detail = []
    ok = True
    for tc, bg, want_pass, why in cases:
        d = dist(hex2rgb(tc), hex2rgb(bg))
        got = d >= mind
        ok &= (got == want_pass)
        detail.append({"telop": tc, "bg": bg, "delta": round(d, 1),
                       "expected": "PASS" if want_pass else "FAIL",
                       "got": "PASS" if got else "FAIL", "why": why})
    return ok, detail

def inj_D4(build, mp4, tmp):
    """最短ショットを参考の下限14F未満に割る。★c01を14F×2にして指摘された形"""
    b = copy.deepcopy(build)
    s = b["shots"][0]
    a, e = s["start_f"], s["end_f"]
    mid = a + 13                      # 13F ＝ 参考の最短14Fを1F下回る
    s["end_f"] = mid
    b["shots"].insert(1, {**copy.deepcopy(s), "name": s["name"] + "b",
                          "start_f": mid, "end_f": e})
    return b, mp4, "G90-1"

def inj_D9(build, mp4, tmp):
    """テロップ密度を無視して cuts/分 だけを参考に寄せた過剰分割。"""
    b = copy.deepcopy(build)
    out = []
    for s in b["shots"]:                       # 全ショットを2分割 → shots_per_telop が倍
        a, e = s["start_f"], s["end_f"]
        m = (a + e) // 2
        out.append({**copy.deepcopy(s), "end_f": m})
        out.append({**copy.deepcopy(s), "name": s["name"] + "b", "start_f": m, "end_f": e})
    b["shots"] = out
    return b, mp4, "G90-4"

def inj_D1(build, mp4, tmp):
    """1ショットだけ白飛びさせた動画を作る。★他が0.00%なのに1つだけ突出、の形を再現"""
    b = copy.deepcopy(build)
    s = b["shots"][4]                          # 中ほどのショットを選ぶ
    fps = b["fps"]
    t0, t1 = s["start_f"] / fps, s["end_f"] / fps
    out = os.path.join(tmp, "inj_D1.mp4")
    # 該当区間だけ露出を持ち上げて白飛びさせる
    vf = (f"curves=all='0/0 0.35/0.95 1/1':enable='between(t,{t0:.3f},{t1:.3f})'")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp4, "-vf", vf,
                    "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
                    "-an", out], check=True)
    return b, out, "G90-9"

MECH  = {"D1": inj_D1, "D4": inj_D4, "D9": inj_D9}
RULES = {"D2": rule_D2}

# ★機械では判定できないもの。ここを『機械で通ったから良い』と言い換えないこと
PACKET_ONLY = {
    "D3": "DBのラベルと実画の食い違い。実画を見ないと分からない → 目視レンズへ",
    "D5": "検算スクリプト自身の誤り。動画ではなくコードの欠陥 → コードレビューのレンズへ",
    "D6": "同種動作の連打がリテイク違いに見える → 意味と重複のレンズへ",
    "D7": "離れた位置の画が機能として被る → 重複のレンズへ",
    "D8": "訴求として弱い画 → 訴求のレンズへ",
}


def find(did):
    for k in ("measurable", "judgmental"):
        for d in DEFECTS[k]:
            if d["id"] == did:
                return d
    raise KeyError(did)


# ---------------------------------------------------------------- mechanical

def run_mechanical(a):
    os.makedirs(a.out, exist_ok=True)
    build = json.load(open(a.build, encoding="utf-8"))
    tmp = tempfile.mkdtemp(prefix="calib_")
    rows = []

    # まず素の状態を測る。ここが FAIL だらけだと『注入で鳴った』が意味を失う
    base = os.path.join(a.out, "baseline.json")
    subprocess.run([sys.executable, MATCHER, "--build", a.build, "--mp4", a.mp4,
                    "--out", base], capture_output=True)
    baseline = json.load(open(base, encoding="utf-8"))
    base_fail = {i["id"] for i in baseline["items"] if i["verdict"] == "FAIL"}
    print(f"baseline: {baseline['verdict']}  既存FAIL={sorted(base_fail) or 'なし'}\n")

    for did, fn in MECH.items():
        d = find(did)
        b, mp4, gate = fn(build, a.mp4, tmp)
        bp = os.path.join(tmp, f"build_{did}.json")
        json.dump(b, open(bp, "w", encoding="utf-8"), ensure_ascii=False)
        op = os.path.join(a.out, f"inject_{did}.json")
        subprocess.run([sys.executable, MATCHER, "--build", bp, "--mp4", mp4,
                        "--out", op], capture_output=True)
        res = json.load(open(op, encoding="utf-8"))
        got = {i["id"] for i in res["items"] if i["verdict"] == "FAIL"}
        # ★素の状態で既に鳴っていたゲートは「検出した」に数えない
        fired = gate in got and gate not in base_fail
        rows.append({"id": did, "title": d["title"], "expected_gate": gate,
                     "fired": fired, "all_fired": sorted(got - base_fail),
                     "detector": d["detector"], "lesson": d["lesson"]})
        print(f"  {'検出' if fired else '★未検出'}  {did} {d['title']}  "
              f"期待={gate}  実際に鳴った={sorted(got - base_fail)}")

    # 規則そのものの単体テスト（注入では試せない項目）
    for did, fn in RULES.items():
        d = find(did)
        ok, detail = fn()
        rows.append({"id": did, "title": d["title"], "expected_gate": d["detector"],
                     "fired": ok, "kind": "rule_unit_test", "cases": detail,
                     "detector": d["detector"], "lesson": d["lesson"]})
        print(f"  {'検出' if ok else '★未検出'}  {did} {d['title']}  （規則の単体テスト）")
        for c in detail:
            print(f"        {c['telop']} on {c['bg']} Δ={c['delta']:6.1f} "
                  f"期待={c['expected']} 実際={c['got']}  {c['why']}")

    n, m = len(rows), sum(1 for r in rows if r["fired"])
    res = {"gate": "G92", "mode": "mechanical", "n": n, "detected": m,
           "rate": round(m / n, 3) if n else 0,
           "pass_rule": DEFECTS["_pass_rule"]["measurable"],
           "verdict": "PASS" if m == n else "FAIL",
           "baseline_fail": sorted(base_fail),
           "not_mechanical": PACKET_ONLY,
           "_note": "★機械で鳴らせるのはここまで。残りは packet モードで独立レビューに掛ける。"
                    "『機械が全部通った＝良い』ではない（壊れていないことの証明にすぎない）",
           "rows": rows}
    json.dump(res, open(os.path.join(a.out, "mechanical.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\n{res['verdict']}  検出率 {m}/{n}  → {a.out}/mechanical.json")
    return 0 if res["verdict"] == "PASS" else 1


# ---------------------------------------------------------------- packet

PACKET_HEADER = """あなたはこの動画の制作者ではありません。制作側の理由も作業ログも渡されていません。
渡された成果物・参考の実測値・案件ルールだけを見て、**欠陥を探して指摘してください**。

★あなたの仕事は肯定ではなく否定です。迷ったら却下側に倒してください。
★「問題なさそう」で終える回答は、この工程では失敗です。必ず具体的な箇所を挙げてください。
★指摘は「どこが」「なぜ悪いか」「どう直すか」の3点を必ず書いてください。

# レンズ（この観点だけを見る。他の観点は他のレビュアーが見ています）
{lens}

# 参考動画の実測値（これが正）
{targets}

# 見る対象
{payload}

# 出力（JSONのみ）
{{"findings":[{{"where":"...","why":"...","fix":"..."}}], "verdict":"NG|OK"}}
"""

def run_packet(a):
    d = os.path.join(a.out, "packets")
    os.makedirs(d, exist_ok=True)
    build = json.load(open(a.build, encoding="utf-8"))
    T = json.load(open(P(".fork/REFERENCE-TARGETS.json"), encoding="utf-8"))
    lenses = json.load(open(P(".fork/lenses/lenses.json"), encoding="utf-8"))["lenses"]
    made = []
    for did, why in PACKET_ONLY.items():
        de = find(did)
        # ★渡すのは成果物だけ。inject（何を仕込んだか）も lens の trap（実例）も渡さない。
        #   どちらも答えそのものなので、混ぜると検出率が実力より高く出てハーネスが無意味になる。
        #   trap は本番のレビューでは有用だが、較正では伏せる。
        payload = {"video_id": build.get("video_id"),
                   "shots": [{k: v for k, v in s.items()
                              if not k.startswith("_") and k != "zoom_waiver"}
                             for s in build["shots"]],
                   "telops": [{k: v for k, v in t.items() if k != "note"}
                              for t in build["telops"]]}
        # detector が指すゲート番号からレンズを引く（無ければ detector 名をそのまま使う）
        key = de["detector"].split("/")[0].strip().split()[0]
        lens = next((l for l in lenses if key and key in l.get("covers", "")), None)
        lens_txt = (f"{lens['id']} {lens['name']}\n{lens['question']}"
                    if lens else de["detector"])
        for rnd in (1, 2, 3):
            f = os.path.join(d, f"{did}_r{rnd}.md")
            open(f, "w", encoding="utf-8").write(PACKET_HEADER.format(
                lens=lens_txt,
                targets=json.dumps({"tempo": T["tempo"],
                                    "telop_grammar": T["telop_grammar"]["tiers"]},
                                   ensure_ascii=False, indent=1),
                payload=json.dumps(payload, ensure_ascii=False, indent=1)))
            made.append(os.path.basename(f))
    idx = {"gate": "G92", "mode": "packet", "packets": made,
           "how_to_run": "各パケットを隔離サブエージェント（作業ログを渡さない新しい文脈）に"
                         "1つずつ渡す。3ラウンドの回答を qc/calibration/answers/<name>.json に"
                         "保存してから score モードを回す",
           "decision": "2/3多数決。可否が割れたら却下側に倒す",
           "pass_rule": DEFECTS["_pass_rule"]["judgmental"],
           "_honest": "★これは同一モデルによるレビューである。モデル多様性は回復していない。"
                      "検出率が基準を満たしても、その事実は消えない",
           "expected": {k: find(k)["expected"] for k in PACKET_ONLY}}
    json.dump(idx, open(os.path.join(a.out, "packet_index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"{len(made)} パケットを {d} に出力（{len(PACKET_ONLY)}欠陥 × 3ラウンド）")
    print("→ 隔離サブエージェントに1つずつ渡し、回答を qc/calibration/answers/ に置いてから score")
    return 0


# ---------------------------------------------------------------- score

def run_score(a):
    ad = os.path.join(a.out, "answers")
    if not os.path.isdir(ad):
        print(f"★{ad} が無い。packet モードの回答をここに置いてから実行する"); return 1
    idx = json.load(open(os.path.join(a.out, "packet_index.json"), encoding="utf-8"))
    rows = []
    for did in PACKET_ONLY:
        votes = []
        for rnd in (1, 2, 3):
            f = os.path.join(ad, f"{did}_r{rnd}.json")
            if not os.path.exists(f):
                votes.append(None); continue
            ans = json.load(open(f, encoding="utf-8"))
            # ★「NGと言ったか」ではなく「その欠陥を指したか」で数える。
            #   別の理由でNGにした回答を検出に数えると、検出率が実力より高く出る
            hit = any(k in json.dumps(fd, ensure_ascii=False)
                      for fd in ans.get("findings", [])
                      for k in find(did)["expected"].replace("。", " ").split())
            votes.append(bool(hit))
        got = [v for v in votes if v is not None]
        detected = sum(1 for v in got if v) >= 2       # 2/3多数決
        rows.append({"id": did, "title": find(did)["title"], "votes": votes,
                     "detected": detected, "answered_rounds": len(got),
                     "expected": find(did)["expected"]})
        print(f"  {'検出' if detected else '★未検出'}  {did} {find(did)['title']}  votes={votes}")
    n = len(rows); m = sum(1 for r in rows if r["detected"])
    ok = n and m / n >= 0.75
    res = {"gate": "G92", "mode": "score", "n": n, "detected": m,
           "rate": round(m / n, 3) if n else 0,
           "verdict": "PASS" if ok else "FAIL",
           "pass_rule": idx["pass_rule"],
           "undetected": [r["id"] + " " + r["title"] for r in rows if not r["detected"]],
           "_report_rule": DEFECTS["_pass_rule"]["reporting"],
           "_honest": idx["_honest"], "rows": rows}
    json.dump(res, open(os.path.join(a.out, "score.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\n{res['verdict']}  検出率 {m}/{n}")
    if res["undetected"]:
        print("★未検出（伏せずに報告する）: " + " / ".join(res["undetected"]))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["mechanical", "packet", "score"])
    ap.add_argument("--build")
    ap.add_argument("--mp4")
    ap.add_argument("--out", default="qc/calibration")
    a = ap.parse_args()
    return {"mechanical": run_mechanical, "packet": run_packet, "score": run_score}[a.mode](a)

if __name__ == "__main__":
    sys.exit(main())
