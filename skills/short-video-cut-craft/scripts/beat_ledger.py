#!/usr/bin/env python3
"""beat_ledger.py — 発話をビート台帳（供給の正本・骨格）に落とす。案件非依存。

自動で埋める欄:
  t0/t1/text/pos_pct（源尺に対する位置%）/gap_before/deixis_hits（指示語）/
  demo_suspect（実演疑い: 指示語+見せ動詞の語彙）/mention_tags（mention_mapの逆引き）/
  redundancy_group（正規化3-gram Jaccard で同内容の反復・言い直しをクラスタ）

Claudeが著述する欄（コードに埋めない）:
  function（フック/価格/信頼/正直訴求/CTA/つなぎ）/ emotion（山/谷/上り）/
  broll_policy（allow/forbid/preserve）/ policy_reason

実演疑い(demo_suspect)は**疑いの列挙**であって確定ではない。採否に使う前に該当フレームを
agyへYES/NO定型質問で見せて事実化する（SKILL.md 原則4）。

使い方: python3 beat_ledger.py <profile> [--gap 0.8] [--out qc/beat_ledger.json]
"""
import json, os, re, sys, argparse

DEIXIS = ["こちら", "これ", "こう", "こういった", "ここ", "そちら", "この", "ご覧"]
DEMO_VERBS = ["見て", "見せ", "紹介", "確認でき", "かけたり", "開け", "押し", "触"]


def norm(s):
    return re.sub(r"[、。！？!?・\s「」（）()…〜ー]", "", s)


def ngrams(s, n=3):
    s = norm(s)
    return {s[i:i + n] for i in range(max(0, len(s) - n + 1))}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("profile")
    ap.add_argument("--gap", type=float, default=0.8, help="ビート境界とみなす語間ギャップ秒")
    ap.add_argument("--out", default="qc/beat_ledger.json")
    a = ap.parse_args()
    prof = json.load(open(a.profile, encoding="utf-8"))
    root = prof["root"]

    def P(rel):
        return rel if os.path.isabs(rel) else os.path.join(root, rel)

    w = json.load(open(P(prof["artifacts"]["words"]), encoding="utf-8"))
    words = w if isinstance(w, list) else w["words"]
    dur = prof["source"]["aroll_duration"]
    mmap_p = P("qc/mention_map.json")
    mmap = json.load(open(mmap_p, encoding="utf-8")) if os.path.exists(mmap_p) else {}

    # --- ビート分割（語間ギャップ） ---
    beats, cur = [], None
    for x in words:
        if cur and x["start"] - cur["t1"] < a.gap:
            cur["t1"] = max(cur["t1"], x["end"])
            cur["text"] += x["word"]
        else:
            if cur:
                beats.append(cur)
            cur = {"t0": x["start"], "t1": x["end"], "text": x["word"]}
    if cur:
        beats.append(cur)

    # --- 自動欄 ---
    prev_end = 0.0
    for i, b in enumerate(beats):
        b["beat"] = f"b{i+1:02d}"
        b["pos_pct"] = round(100 * b["t0"] / dur, 1)
        b["gap_before"] = round(b["t0"] - prev_end, 2)
        prev_end = b["t1"]
        b["deixis_hits"] = [d for d in DEIXIS if d in b["text"]]
        b["demo_suspect"] = bool(b["deixis_hits"]) and any(v in b["text"] for v in DEMO_VERBS) \
            or any(v in b["text"] for v in ("見てください", "紹介して", "ご覧"))
        b["mention_tags"] = sorted({tag for tag, ws in mmap.items()
                                    if not tag.startswith("_") and any(x in b["text"] for x in ws)})
        b["mention_times"] = {}            # タグ→言及語の実時刻（アンカーに使う）
        # 著述欄（Claudeが埋める）
        b["function"] = ""
        b["emotion"] = ""
        b["broll_policy"] = ""
        b["allow_tags"] = []               # allowするタグの限定（空=mention_tags全部）
        b["policy_reason"] = ""

    # --- 言及時刻（文字ストリームで語を跨ぐキーワードも拾う） ---
    for b in beats:
        ws = [x for x in words if b["t0"] - 0.01 <= x["start"] <= b["t1"] + 0.01]
        rec, ch_t = "", []
        for x in ws:
            t = x["word"]
            if not t:
                continue
            st = (x["end"] - x["start"]) / len(t)
            for k, ch in enumerate(t):
                rec += ch
                ch_t.append(x["start"] + st * k)
        for tag in b["mention_tags"]:
            for kw in mmap.get(tag, []):
                i = rec.find(kw)
                if i >= 0:
                    b["mention_times"][tag] = round(ch_t[i], 2)
                    break

    # --- 冗長グループ（3-gram Jaccard >= 0.5 を連結） ---
    groups, gid = {}, 0
    sets = [ngrams(b["text"]) for b in beats]
    for i in range(len(beats)):
        for j in range(i + 1, len(beats)):
            if not sets[i] or not sets[j]:
                continue
            jac = len(sets[i] & sets[j]) / len(sets[i] | sets[j])
            if jac >= 0.5:
                g = groups.get(i) or groups.get(j)
                if g is None:
                    gid += 1
                    g = f"R{gid}"
                groups[i] = groups[j] = g
    for i, b in enumerate(beats):
        b["redundancy_group"] = groups.get(i, "")

    doc = {"_note": "ビート台帳（供給の正本）。自動欄はコード、function/emotion/broll_policy/"
                    "policy_reason はClaudeが著述する。demo_suspect は疑い——採否に使う前に"
                    "agyフレーム確認で事実化すること。",
           "duration": dur, "gap": a.gap, "beats": beats}
    op = P(a.out)
    os.makedirs(os.path.dirname(op), exist_ok=True)
    json.dump(doc, open(op, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    n_red = len(set(groups.values()))
    n_dx = sum(1 for b in beats if b["deixis_hits"])
    print(f"ビート {len(beats)} / 冗長グループ {n_red} / 指示語hit {n_dx}ビート / "
          f"実演疑い {sum(1 for b in beats if b['demo_suspect'])}ビート → {a.out}")
    for b in beats:
        fl = ("D" if b["deixis_hits"] else "-") + ("!" if b["demo_suspect"] else "-")
        print(f"  {b['beat']} {b['t0']:7.2f}-{b['t1']:7.2f} {b['pos_pct']:5.1f}% [{fl}]"
              f"{('[' + b['redundancy_group'] + ']') if b['redundancy_group'] else ''} "
              f"{b['text'][:34]}  {','.join(b['mention_tags'])}")


if __name__ == "__main__":
    main()
