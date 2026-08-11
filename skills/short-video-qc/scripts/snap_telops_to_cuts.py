#!/usr/bin/env python3
"""テロップをカット境界に合わせる（カットの頭に文字の断片が入るのを防ぐ）。

なぜ要るか（2026-07-29 ユーザー指摘）:
> 「冒頭がうまく検出できず、次のカットの冒頭に文字が切れて入ってしまっていることがある。
>   例えば『45万』と表示する場合、1つのカットに『45万』まで入れなければいけないのに、
>   『45』で切れてしまい、次のカットの冒頭に『万』が入ってしまっている」
> 「必ずしも発話のタイミングに合わせる必要はない。少しずらしてもいいので、
>   見た目の整合性を優先してほしい」

それまでの検査はテロップ**同士**の切れ目しか見ておらず、
テロップが**カット境界をまたぐ**ことは一切見ていなかった。
18_ACTY では61枚中32枚が境界をまたぎ、うち7件が
「数値が割れる」「次カットの頭に1〜2文字だけ残る」状態だった。

やること:
  カット境界をまたぐテロップについて、境界の左右に出る文字を時間で按分して調べ、
  次のどれかに当たるなら**テロップの時刻をずらして**またぎを解消する。
    ・数値＋助数詞が割れる（45|万、20万|キロ 等）
    ・次カットの頭に残るのが N 文字以下（既定2文字）＝断片
    ・カットの頭に残るのが助詞・助動詞だけ

  ★まず「カット境界でテロップを割り直す」を試す。
    境界のいちばん近くにある**割ってよい位置**（数値＋助数詞の内側などは除く）で分け、
    その切れ目の時刻を境界にぴったり合わせる。こうするとカットの変わり目でテロップも変わり、
    断片が次カットの頭に残らない。割った結果が短すぎる枚は隣と併合する。

  割り直せない場合は、時刻をずらす。2通りから移動量の小さい方を選ぶ:
    (a) 前へ寄せる … テロップの終わりを境界まで縮め、次のテロップの頭を境界に合わせる
    (b) 後ろへ送る … テロップの頭を境界まで送る（そのぶん表示が遅れる）
  ★どちらも発話とのズレを生むが、ユーザー指示のとおり**見た目の整合性を優先**する。
  ただしズレの上限（既定0.35秒）を超える場合は動かさず、報告だけする。

使い方:
  python3 snap_telops_to_cuts.py <telops.json> <cutlist.json> \
      [--max-shift 0.35] [--frag 2] [--out telops_snapped.json] [--check-only]
"""
import json, re, sys, argparse

NUM_LEFT = re.compile(r"[0-9０-９]+[万億千百]?$")
CNT_RIGHT = re.compile(r"^(万|億|千|円|キロ|年|台|人|分|割)")
PARTICLE_RIGHT = re.compile(r"^[はがをにでもとやのねよか](?![ぁ-んァ-ヴ])")


def split_at(t, b):
    """テロップ t が境界 b で左右に何文字ずつ出るか（時間で按分）"""
    n = len(t["text"])
    if t["e"] - t["s"] <= 0:
        return t["text"], ""
    k = round(n * (b - t["s"]) / (t["e"] - t["s"]))
    k = max(0, min(n, k))
    return t["text"][:k], t["text"][k:]


HEAD_POS = ("名詞", "動詞", "形容詞", "副詞", "連体詞", "接続詞", "感動詞", "接頭辞", "形状詞")
NO_HEAD_POS = ("助詞", "助動詞", "接尾辞", "補助記号")
BAN_LEFT = re.compile(r"([0-9０-９]+[万億千百]?|じゃ|では|でも|って|とか|気に|目に|手に)$")
BAN_RIGHT = re.compile(r"^(キロ|円|万|年|台|人|分|割|なく|ない|なっ|して|する|しない)")
_tagger = None


def allowed_positions(text):
    """割ってよい文字位置。★文字レベルの推測ではなく形態素で判定する。

    最初の実装は文字レベルの正規表現だけで判定したため、
    「この金額45万円です」を「この金額4」/「5万円です」と**数字の途中で割った**。
    テロップを作るときと同じ規則（fugashiの文節頭のみ・禁止境界を除く）を使う。
    """
    global _tagger
    if _tagger is None:
        from fugashi import Tagger
        _tagger = Tagger()
    toks, pos, spans = list(_tagger(text)), 0, []
    for t in toks:
        j = text.find(t.surface, pos)
        if j < 0:
            j = pos
        spans.append((j, t))
        pos = j + len(t.surface)
    ok = []
    for k in range(1, len(spans)):
        j, t = spans[k]
        p1 = t.feature.pos1
        if p1 in NO_HEAD_POS or p1 not in HEAD_POS:
            continue
        prev = spans[k - 1][1]
        if prev.feature.pos1 in ("接頭辞", "副詞", "連体詞"):
            continue
        if re.fullmatch(r"[0-9０-９]+", prev.surface):
            continue
        if re.fullmatch(r"[ァ-ヴー]+", prev.surface) and re.fullmatch(r"[ァ-ヴー]+", t.surface):
            continue
        if BAN_LEFT.search(text[:j]) and BAN_RIGHT.match(text[j:]):
            continue
        ok.append(j)
    return ok


def bad_split(left, right, frag):
    if NUM_LEFT.search(left) and CNT_RIGHT.match(right):
        return "数値が割れる"
    if 0 < len(right) <= frag:
        return f"次カットの頭に{len(right)}文字だけ残る"
    if right and PARTICLE_RIGHT.match(right) and len(right) <= frag + 1:
        return "次カットの頭が助詞だけになる"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("telops")
    ap.add_argument("cutlist")
    ap.add_argument("--max-shift", type=float, default=0.35)
    ap.add_argument("--frag", type=int, default=2)
    ap.add_argument("--out", default=None)
    ap.add_argument("--check-only", action="store_true")
    a = ap.parse_args()

    td = json.load(open(a.telops, encoding="utf-8"))
    tel = [dict(x) for x in (td["telops"] if isinstance(td, dict) else td)]
    cd = json.load(open(a.cutlist, encoding="utf-8"))
    bnd = [round(c["tl"], 3) for c in cd["cuts"]][1:]
    dur = cd.get("duration")

    fixed, left_over = [], []
    for b in bnd:
        for i, t in enumerate(tel):
            if not (t["s"] + 1e-6 < b < t["e"] - 1e-6):
                continue
            L, R = split_at(t, b)
            why = bad_split(L, R, a.frag)
            if not why:
                continue
            back = b - t["s"]        # 頭を境界へ送る移動量
            fwd = t["e"] - b         # 尻を境界へ縮める移動量
            if a.check_only:
                left_over.append((b, t["text"], L, R, why, min(back, fwd)))
                continue
            # ---- ①わずかなズレで済むなら、時刻をずらして解消する ----
            #    ★割り直しより優先する。割ると短い枚（0.1秒台）が生まれることがあるため。
            if min(back, fwd) > a.max_shift:
                # ---- ②大きくずれる場合だけ、カット境界で割り直す ----
                n, span = len(t["text"]), t["e"] - t["s"]
                cand = [(abs((t["s"] + span * k / n) - b), k) for k in allowed_positions(t["text"])]
                cand = [c for c in cand if c[0] <= 0.60]
                if cand:
                    _, k = min(cand)
                    A = {**t, "text": t["text"][:k], "e": round(b, 3)}
                    B = {**t, "text": t["text"][k:], "s": round(b, 3)}
                    tel[i:i + 1] = [A, B]
                    # 短すぎる枚は隣と併合する（上限13文字）
                    for j, side in ((0, -1), (1, +1)):
                        cur = tel[i + j]
                        nb = i + j + side
                        if cur["e"] - cur["s"] >= 0.45 or not (0 <= nb < len(tel)):
                            continue
                        if len(tel[nb]["text"]) + len(cur["text"]) > 13:
                            continue
                        if side < 0:
                            tel[nb]["text"] += cur["text"]; tel[nb]["e"] = cur["e"]
                        else:
                            tel[nb]["text"] = cur["text"] + tel[nb]["text"]; tel[nb]["s"] = cur["s"]
                        tel.pop(i + j)
                        break
                    fixed.append((b, t["text"], why, f"境界で「{t['text'][:k]}」/「{t['text'][k:]}」に割り直した"))
                    continue
                left_over.append((b, t["text"], L, R, why, min(back, fwd)))
                continue
            if back <= fwd:
                # 頭を境界へ送る。直前のテロップの尻を伸ばして穴を作らない
                if i > 0 and tel[i - 1]["e"] >= t["s"] - 1e-6:
                    tel[i - 1]["e"] = round(b, 3)
                t["s"] = round(b, 3)
                fixed.append((b, t["text"], why, f"頭を{back:.3f}秒 後ろへ送った"))
            else:
                # 尻を境界へ縮める。次のテロップの頭を境界へ寄せる
                if i + 1 < len(tel) and tel[i + 1]["s"] <= t["e"] + 1e-6:
                    tel[i + 1]["s"] = round(b, 3)
                t["e"] = round(b, 3)
                fixed.append((b, t["text"], why, f"尻を{fwd:.3f}秒 前へ縮めた"))

    # 短すぎる枚を、またぎを作らない範囲で隣と併合する
    #   （カット境界で割った結果、片側が極端に短くなることがある）
    def straddles(x):
        return any(x["s"] + 1e-6 < b < x["e"] - 1e-6 for b in bnd)

    merged = True
    while merged:
        merged = False
        for i, x in enumerate(tel):
            if x["e"] - x["s"] >= 0.30:
                continue
            for nb in (i - 1, i + 1):
                if not (0 <= nb < len(tel)):
                    continue
                if len(tel[nb]["text"]) + len(x["text"]) > 13:
                    continue
                cand = ({**tel[nb], "text": tel[nb]["text"] + x["text"], "e": x["e"]}
                        if nb < i else
                        {**tel[nb], "text": x["text"] + tel[nb]["text"], "s": x["s"]})
                if straddles(cand):
                    continue
                tel[min(i, nb)] = cand
                tel.pop(max(i, nb))
                merged = True
                break
            if merged:
                break

    # 検算: またぎが残っていないか
    rest = []
    for b in bnd:
        for t in tel:
            if t["s"] + 1e-6 < b < t["e"] - 1e-6:
                L, R = split_at(t, b)
                why = bad_split(L, R, a.frag)
                if why:
                    rest.append((b, t["text"], why))
    short = [t for t in tel if t["e"] - t["s"] < 0.30]

    print(f"カット境界 {len(bnd)}箇所 / テロップ {len(tel)}枚")
    if a.check_only:
        print(f"★問題のあるまたぎ: {len(left_over)}件")
        for b, txt, L, R, why, sh in left_over:
            print(f"  境界{b:7.3f}「{txt}」→「{L}」/「{R}」 … {why}（最小移動 {sh:.3f}秒）")
        sys.exit(0 if not left_over else 1)

    print(f"直した: {len(fixed)}件")
    for b, txt, why, how in fixed:
        print(f"  境界{b:7.3f}「{txt}」… {why} → {how}")
    if left_over:
        print(f"★動かせなかった（移動量が上限{a.max_shift}秒を超える）: {len(left_over)}件")
        for b, txt, L, R, why, sh in left_over:
            print(f"  境界{b:7.3f}「{txt}」→「{L}」/「{R}」 … {why}（最小移動 {sh:.3f}秒）")
    print(f"検算: 残るまたぎ {len(rest)}件 / 0.30秒未満の表示 {len(short)}枚")
    for x in rest:
        print(f"  ★{x}")

    out = a.out or a.telops.replace(".json", "_snapped.json")
    body = {**td, "telops": tel} if isinstance(td, dict) else tel
    if isinstance(body, dict):
        body["_snapped"] = {"cutlist": a.cutlist, "fixed": len(fixed),
                            "left_over": len(left_over), "max_shift": a.max_shift}
    json.dump(body, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"→ {out}")
    sys.exit(0 if not rest and not short else 1)


if __name__ == "__main__":
    main()
