#!/usr/bin/env python3
"""挿入映像に「一瞬だけ人（演者・撮影者・第三者）が映り込む」箇所を検出する。

なぜ要るか（2026-07-29 ユーザー指摘）:
> 「一瞬だけ演者が映り込んでいるところを検出してほしい」

★試作で分かった落とし穴（同じ失敗を繰り返さないため必ず読むこと）:
  観察記録（Codexの自由記述）を「男性/人物/手/腕」でgrepしたら、
  **「助手席」の「手」に反応して 62/112枚が誤検出**した。
  逆に厳密な語（男性/店員/スタッフ）に絞ったら全素材0件になったが、
  これは「人がいない」の証明にはならない。**自由記述に書かれていないだけ**かもしれない。
  → 自由記述のgrepは使わない。次の2本立てにする。

  ①機械（このスクリプト）… モデル不要。**動きを補正したフレーム間の残差**を測り、
     「一部の領域だけが急に変わる」＝何かが入ってきた／出ていった、を検出する。
     人かどうかまでは判定できないので**候補を絞る道具**として使う。

     ★最初は「時間中央値フレームとの差」で作ったが、**人を合成した検証用クリップで
       検出0件**だった。素材がパンなので全フレームが中央値から大きく外れ、
       人の分（+25）が埋もれてz=1.96にしかならなかった。
       → 連続フレームを位相相関で位置合わせしてから引く方式に変えたところ、
         人が入るフレームで z=36.6、出るフレームで z=36.2 と明確に立った。
     ★検出器は必ず「陽性の検証用クリップ」で当たることを確かめてから使うこと。
  ②Codex（--prompt で雛形を出力）… 候補フレームに**定型の質問**を投げる。
     自由記述ではなく YES/NO で答えさせるので機械で集計できる。

使い方:
  python3 qc_intruder.py <broll.json> <素材ディレクトリ> [--fps 10]
        [--out qc/intruder.json] [--dump qc/intruder_frames] [--prompt qc/intruder_prompt.txt]
"""
import json, os, subprocess, argparse, glob
import numpy as np

QUESTION = """次の画像それぞれについて、**この形式だけ**で答えてください。自由記述は書かないでください。

<ファイル名> | 人:YES/NO | 位置:左/中央/右/なし | 大きさ:大/中/小/なし | 何:演者/撮影者/第三者/手や腕のみ/なし

判断の基準:
- 「人」には、体の一部（手・腕・肩・足）だけが写っている場合も YES に含めます。
- 車内の「助手席」「運転席」は座席の名前であって人ではありません。**座席は NO です。**
- 窓ガラスやミラーへの映り込みも、人と分かるなら YES にしてください。
"""


def frame_height(path, W):
    """同じフィルタで1フレームだけ書き出し、実際の高さを読む（回転メタデータ対策）"""
    import tempfile
    from PIL import Image
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as t:
        tmp = t.name
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vframes", "1",
                    "-vf", f"scale={W}:-2", tmp], check=True)
    h = Image.open(tmp).size[1]
    os.unlink(tmp)
    return h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("broll")
    ap.add_argument("srcdir")
    ap.add_argument("--fps", type=int, default=10)
    ap.add_argument("--out", default="qc/intruder.json")
    ap.add_argument("--dump", default="qc/intruder_frames")
    ap.add_argument("--prompt", default="qc/intruder_prompt.txt")
    ap.add_argument("--k", type=float, default=6.0,
                    help="中央値からの外れ幅。検証用クリップでは人の出入りが z=36 まで立ったので"
                         "6.0 でも十分に拾える（低くしすぎるとパンの揺らぎを拾う）")
    a = ap.parse_args()

    br = json.load(open(a.broll, encoding="utf-8"))
    ins = br["inserts"] if isinstance(br, dict) else br
    os.makedirs(a.dump, exist_ok=True)
    for f in glob.glob(a.dump + "/*.jpg"):
        os.remove(f)

    hits, checked = [], 0
    for x in ins:
        name = x["src"]
        path = os.path.join(a.srcdir, name)
        if not os.path.exists(path):
            print(f"  ★素材が無い: {path}")
            continue
        s0, s1 = x["src_in"], x["src_in"] + x["dur"]
        W = 160
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{s0}", "-to", f"{s1}", "-i", path,
             "-vf", f"fps={a.fps},scale={W}:-2", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
            capture_output=True).stdout
        # ★出力の縦横は ffprobe の width/height から計算してはいけない。
        #   素材には rotation=-90 が付いており、ffmpeg は回転後（縦）で出力するのに
        #   ffprobe は回転前（横 1920x1080）を返す。この食い違いで reshape が
        #   でたらめな配列になり、**人を合成した検証用クリップでも検出0件**になっていた。
        #   実際に1フレーム書き出して、その寸法を使う。
        H = frame_height(path, W)
        n = len(raw) // (W * H)
        if n < 4:
            continue
        g = np.frombuffer(raw[:n * W * H], dtype=np.uint8).reshape(n, H, W).astype(np.float32)
        checked += n
        # ★動きを補正してから引く（パン素材でも「入ってきたもの」だけが残るように）
        import cv2
        BS = 16
        score = np.zeros(n)
        for i in range(1, n):
            (dx, dy), _ = cv2.phaseCorrelate(g[i - 1], g[i])
            M = np.float32([[1, 0, dx], [0, 1, dy]])
            warp = cv2.warpAffine(g[i - 1], M, (W, H), flags=cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_REPLICATE)
            d = np.abs(g[i] - warp)
            bl = d[:H // BS * BS, :W // BS * BS].reshape(H // BS, BS, W // BS, BS).mean(axis=(1, 3))
            score[i] = bl.max()
        v = score[1:]
        m, mad = np.median(v), np.median(np.abs(v - np.median(v))) + 1e-9
        z = (score - m) / (1.4826 * mad)
        z[0] = 0.0
        idx = np.where(z > a.k)[0]
        if len(idx) == 0 or len(idx) >= n * 0.6:
            continue                      # 全編で変わるならパン。一部だけが「入ってきた」
        runs, cur = [], [idx[0]]
        for i in idx[1:]:
            if i - cur[-1] <= 2:
                cur.append(i)
            else:
                runs.append(cur); cur = [i]
        runs.append(cur)
        for r in runs:
            dur = (r[-1] - r[0] + 1) / a.fps
            t0 = s0 + r[0] / a.fps
            tag = "一瞬だけ" if dur < 0.5 else "短時間"
            fn = f"{a.dump}/{name.split('.')[0]}_{t0:.2f}.jpg"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0}", "-i", path,
                            "-vframes", "1", "-vf", "scale=360:-2", fn])
            hits.append({"src": name, "tl_in": x["tl_in"], "src_t": round(t0, 3),
                         "sec": round(dur, 3), "kind": tag,
                         "peak_z": round(float(z[r].max()), 2), "frame": fn})

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump({"broll": a.broll, "checked_frames": checked,
               "_note": "機械は『一部の領域が短時間だけ大きく変わった』ことしか分からない。"
                        "人かどうかは --prompt の定型質問でCodexに確認し、最後は目で見る。",
               "hits": hits}, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if hits:
        files = "\n".join(os.path.abspath(h["frame"]) for h in hits)
        open(a.prompt, "w", encoding="utf-8").write(QUESTION + "\n対象:\n" + files + "\n")

    print(f"調べたフレーム {checked}枚 / 候補 {len(hits)}件")
    for h in hits:
        print(f"  {h['src']:<14} 素材{h['src_t']:5.2f}秒 tl{h['tl_in']:6.2f} "
              f"{h['kind']}({h['sec']:.2f}s) 外れ{h['peak_z']}σ → {os.path.basename(h['frame'])}")
    print(f"→ {a.out}" + (f" / 質問文 {a.prompt}" if hits else ""))
    print("★機械だけで結論を出さない。候補フレームは必ず目で見ること。")


if __name__ == "__main__":
    main()
