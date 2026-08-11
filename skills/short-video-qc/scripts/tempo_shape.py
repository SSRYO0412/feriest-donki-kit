#!/usr/bin/env python3
"""テンポと尺を「形」として測る（中央値1つでの合否判定を禁止するための実装）。

なぜ要るか:
  過去に「ショット尺の中央値だけ参考比+40%」を「1指標だけ外れ」と報告して通した。
  参考動画は掴みで刻み・見せ場で溜め・オチで切る、という**時間の中の形**を持つ。
  スカラー1つでは形が消える。形を持たないデータで設計すれば出力も形を持たない。

何をするか:
  完成動画の全フレーム観察（G21の生出力）から「被写体が変わった位置」を拾い、
  ショット列を復元する。そのうえで:
    - 4分割（掴み/展開/山/締め）ごとのショット数・平均尺・最長尺
    - 参考動画の同じ数値との差
    - 「画が変わらない秒数」の分布
  を出す。★合否は出さない。判断はTEMPO.mdの③〜⑤で人とCodexが行う。

使い方:
  python3 tempo_shape.py <プロジェクトルート> <総尺秒> [--ref <参考のshape.json>] [--out qc/tempo_shape.json]
"""
import sys, os, re, json, argparse

# ★既定は時間の4等分だが、これは「各パートが25%」という自明な結果しか出ない。
#   尺配分を評価したいなら --sections で**内容による区切り**を秒で渡すこと。
#   例: --sections "掴み:0-15.3,展開:15.3-56,山:56-90,締め:90-108"
PARTS = [(0.00, 0.25, "掴み"), (0.25, 0.50, "展開"), (0.50, 0.75, "山"), (0.75, 1.00, "締め")]

def parse_sections(spec, dur):
    """"名前:開始-終了,..." を [(lo比, hi比, 名前)] に変換（秒指定）"""
    out = []
    for part in spec.split(","):
        name, rng = part.split(":")
        lo, hi = (float(x) for x in rng.split("-"))
        out.append((lo/dur, hi/dur, name.strip()))
    return out

def shots_from_obs(obs_dir, fps=30.0):
    """G21の全フレーム観察から、被写体が変わった位置でショットを区切る"""
    rec = {}
    for f in sorted(os.listdir(obs_dir)):
        if not f.endswith(".txt") or f.startswith("_"):
            continue
        for ln in open(f"{obs_dir}/{f}", encoding="utf-8", errors="replace"):
            m = re.match(r"\s*[-*]?\s*f(\d{5})\.jpg\s*[:：]?\s*(.+)", ln)
            if not m:
                continue
            subj = m.group(2).split("/")[0].strip()
            rec[int(m.group(1))] = subj
    if not rec:
        return []
    idx = sorted(rec)
    shots, s = [], idx[0]
    for a, b in zip(idx, idx[1:]):
        if rec[a] != rec[b]:
            shots.append({"start": round(s/fps, 3), "end": round(b/fps, 3),
                          "sec": round((b-s)/fps, 3), "subject": rec[a]})
            s = b
    shots.append({"start": round(s/fps, 3), "end": round(idx[-1]/fps, 3),
                  "sec": round((idx[-1]-s)/fps, 3), "subject": rec[idx[-1]]})
    return shots

def shape(shots, dur, parts=None):
    parts = parts or PARTS
    out = {"total_shots": len(shots), "duration": dur, "parts": []}
    L = sorted(s["sec"] for s in shots)
    out["median_sec"] = L[len(L)//2] if L else None
    out["max_sec"] = L[-1] if L else None
    out["shots_per_min"] = round(len(shots)/dur*60, 1) if dur else None
    for lo, hi, name in parts:
        seg = [s for s in shots if lo*dur <= s["start"] < hi*dur]
        if not seg:
            out["parts"].append({"name": name, "shots": 0}); continue
        ls = [s["sec"] for s in seg]
        out["parts"].append({
            "name": name, "range": [round(lo*dur, 1), round(hi*dur, 1)],
            "shots": len(seg), "avg_sec": round(sum(ls)/len(ls), 2),
            "max_sec": round(max(ls), 2),
            "share_pct": round(sum(ls)/dur*100, 1),
        })
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("duration", type=float)
    ap.add_argument("--obs", default=None)
    ap.add_argument("--ref", default=None)
    ap.add_argument("--sections", default=None,
                    help='内容による区切りを秒で指定。例 "掴み:0-15.3,展開:15.3-56,山:56-90,締め:90-108"')
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    obs = a.obs or f"{a.root}/qc/codex_view/frames_full"
    out = a.out or f"{a.root}/qc/tempo_shape.json"
    if not os.path.isdir(obs):
        print(f"★全フレーム観察が無い: {obs}  先にG21を実施すること"); sys.exit(2)

    shots = shots_from_obs(obs)
    parts = parse_sections(a.sections, a.duration) if a.sections else None
    sh = shape(shots, a.duration, parts)
    sh["sections_source"] = "内容による区切り（指定）" if a.sections else "★時間の4等分（尺配分は自明に25%になるため評価に使えない）"
    sh["shots"] = shots
    sh["_note"] = "合否は出さない。判断はTEMPO.mdの③〜⑤で人とCodexが行う"

    if a.ref and os.path.exists(a.ref):
        ref = json.load(open(a.ref, encoding="utf-8"))
        cmp_ = []
        for p, rp in zip(sh["parts"], ref.get("parts", [])):
            if not p.get("shots") or not rp.get("shots"):
                continue
            cmp_.append({
                "part": p["name"],
                "avg_sec": {"this": p["avg_sec"], "ref": rp["avg_sec"],
                            "diff_pct": round((p["avg_sec"]-rp["avg_sec"])/rp["avg_sec"]*100, 1)},
                "share_pct": {"this": p["share_pct"], "ref": rp["share_pct"],
                              "diff_pt": round(p["share_pct"]-rp["share_pct"], 1)},
            })
        sh["vs_ref"] = cmp_
        sh["ref_file"] = a.ref

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    json.dump(sh, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"総尺{a.duration}s / ショット{sh['total_shots']}個 / {sh['shots_per_min']}個per分 / 中央値{sh['median_sec']}s 最長{sh['max_sec']}s")
    for p in sh["parts"]:
        if p.get("shots"):
            print(f"  {p['name']:4s} {p['range'][0]:6.1f}-{p['range'][1]:6.1f}s: {p['shots']:3d}ショット 平均{p['avg_sec']:.2f}s 最長{p['max_sec']:.2f}s 尺配分{p['share_pct']}%")
    for c in sh.get("vs_ref", []):
        print(f"  ★{c['part']}: 平均尺 {c['avg_sec']['this']} vs 参考{c['avg_sec']['ref']} ({c['avg_sec']['diff_pct']:+.1f}%) / 尺配分 {c['share_pct']['diff_pt']:+.1f}pt")
    print(f"→ {out}")

if __name__ == "__main__":
    main()
