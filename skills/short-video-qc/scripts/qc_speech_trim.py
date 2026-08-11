#!/usr/bin/env python3
"""「話している内容として、カットしてよさそうな区間」の候補を出す。

なぜ要るか（2026-07-29 ユーザー指摘）:
> 「話している内容として、別にカットしちゃっていいだろうと思われるところを検出できないか」

出すもの（3種類）:
  A 内容語がほとんど無い区間 … フィラーと助詞だけで実質の情報が無い
  B 同じ言い回しの再出現     … 内容語を含む3形態素以上が離れて2回以上出る
  C 相槌だけの区間           … はい/そうですね/なるほど 等で完結している

★重要な制約:
  削除できるのは**前後に0.18秒以上の無音がある区間だけ**（言葉を言い切らせる規則）。
  切れない候補を並べても実行できないので、このスクリプトは
  **実際に切れるかどうかを先に判定して「実行可能」な候補だけを候補として立てる**。
  切れないものは参考として別枠に出す。

★試作で分かった落とし穴:
  ・3-gramをそのまま数えると「んですけど」「になって」など**機能語だけの並びが大量に出る**。
    → 内容語（名詞・動詞・形容詞・副詞）を1つ以上含む並びに限る。
  ・「ちょっと」「もう」は本当のフィラーのこともあれば意味を担うこともある。
    → 機械は候補を出すだけ。**採否は必ず人とCodexが1件ずつ決める**。

使い方:
  python3 qc_speech_trim.py <cutlist.json> <words.json> <env.npy> <音声の実尺秒>
        [--min-sec 0.6] [--out qc/speech_trim.json]
"""
import json, sys, argparse
import numpy as np

CONTENT = ("名詞", "動詞", "形容詞", "副詞")
FILLER = {"あの", "えー", "ええ", "まあ", "なんか", "その", "うん", "はい",
          "そう", "やっぱり", "もう", "ちょっと", "えっと", "あー"}
AIZUCHI = {"はい", "そうですね", "なるほど", "うわー", "おー", "いいですね",
           "あります", "どうぞ", "そうです"}
TH_DB, MIN_SIL = -42.0, 0.18


def silences(env_path, dur):
    env = np.load(env_path)
    hop = dur / len(env)
    db = 20 * np.log10(np.maximum(env, 1e-6))
    S = max(1, int(round(0.020 / hop)))
    pad = np.pad(db, (S // 2, S - S // 2 - 1), mode="edge")
    db = np.array([np.median(pad[i:i + S]) for i in range(len(db))])
    q, out, i = db < TH_DB, [], 0
    while i < len(q):
        if q[i]:
            j = i
            while j < len(q) and q[j]:
                j += 1
            if (j - i) * hop >= MIN_SIL:
                out.append((i * hop, j * hop))
            i = j
        else:
            i += 1
    return out


def cuttable(a, b, sil):
    """区間 [a,b] の前後に無音があり、切り出せるか"""
    pre = any(x <= a <= y for x, y in sil)
    post = any(x <= b <= y for x, y in sil)
    return pre and post


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cutlist")
    ap.add_argument("words")
    ap.add_argument("env")
    ap.add_argument("duration", type=float)
    ap.add_argument("--min-sec", type=float, default=0.6)
    ap.add_argument("--out", default="qc/speech_trim.json")
    a = ap.parse_args()

    from fugashi import Tagger
    tg = Tagger()
    cl = json.load(open(a.cutlist, encoding="utf-8"))["cuts"]
    w = json.load(open(a.words, encoding="utf-8"))
    words = w if isinstance(w, list) else w["words"]
    sil = silences(a.env, a.duration)

    def text_of(c):
        return "".join(x["word"] for x in words
                       if c["src_in"] <= x["start"] < c["src_out"])

    A, B, C = [], [], []

    # ---- A 内容語がほとんど無い / C 相槌だけ ----
    for c in cl:
        t = text_of(c)
        if not t.strip():
            continue
        toks = list(tg(t))
        if not toks:
            continue
        cw = [x for x in toks if x.feature.pos1 in CONTENT and x.surface not in FILLER]
        ratio = len(cw) / len(toks)
        d = c["src_out"] - c["src_in"]
        ok = cuttable(c["src_in"], c["src_out"], sil)
        rec = {"tl": round(c["tl"], 3), "sec": round(d, 3),
               "src": [round(c["src_in"], 3), round(c["src_out"], 3)],
               "text": t, "content_ratio": round(ratio, 3),
               "cuttable": ok,
               "why": ""}
        if ratio <= 0.15 and d >= a.min_sec:
            rec["why"] = f"内容語が{ratio*100:.0f}%しかない（フィラーと助詞のみ）"
            A.append(rec)
        stripped = t
        for k in sorted(AIZUCHI, key=len, reverse=True):
            stripped = stripped.replace(k, "")
        if len(stripped.strip("、。 ")) <= 2 and d >= a.min_sec:
            r2 = dict(rec)
            r2["why"] = "相槌だけで構成されている"
            C.append(r2)

    # ---- B 同じ言い回しの再出現（★内容語を含む並びに限る）----
    seen = {}
    for c in cl:
        t = text_of(c)
        toks = list(tg(t))
        for i in range(len(toks) - 2):
            g = toks[i:i + 3]
            if not any(x.feature.pos1 in CONTENT and x.surface not in FILLER for x in g):
                continue                      # 機能語だけの並びは数えない
            s = "".join(x.surface for x in g)
            if len(s) < 4:
                continue
            if s in seen and c["tl"] - seen[s][0] > 3.0:
                B.append({"phrase": s, "first_tl": round(seen[s][0], 3),
                          "again_tl": round(c["tl"], 3),
                          "first_text": seen[s][1][:40], "again_text": t[:40]})
                seen[s] = (c["tl"], t)
            elif s not in seen:
                seen[s] = (c["tl"], t)

    exec_A = [x for x in A if x["cuttable"]]
    exec_C = [x for x in C if x["cuttable"]]
    rep = {"cutlist": a.cutlist,
           "_note": "機械は候補を出すだけ。採否は人とCodexが1件ずつ決める。"
                    "cuttable=false は前後に無音が無く、切ると語が割れるため実行できない。",
           "low_content": A, "repeats": B, "aizuchi_only": C,
           "executable": {"low_content": len(exec_A), "aizuchi_only": len(exec_C)}}
    import os
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(rep, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"■ A 内容語が薄い区間: {len(A)}件（うち実際に切れる {len(exec_A)}件）")
    for x in A:
        print(f"  {'切れる' if x['cuttable'] else '切れない'} tl{x['tl']:7.2f} ({x['sec']:.2f}s) "
              f"内容語{x['content_ratio']*100:4.0f}% 「{x['text'][:34]}」")
    print(f"\n■ C 相槌だけの区間: {len(C)}件（うち実際に切れる {len(exec_C)}件）")
    for x in C:
        print(f"  {'切れる' if x['cuttable'] else '切れない'} tl{x['tl']:7.2f} ({x['sec']:.2f}s) 「{x['text'][:34]}」")
    print(f"\n■ B 同じ言い回しの再出現: {len(B)}件")
    for x in B:
        print(f"  「{x['phrase']}」 {x['first_tl']:.1f}秒 → {x['again_tl']:.1f}秒")
    print(f"\n→ {a.out}")


if __name__ == "__main__":
    main()
