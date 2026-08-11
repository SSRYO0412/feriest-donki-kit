# ショート動画のフック・カット尺の基準（出典つき）

> なぜこのファイルが要るか:
> 2026-07-27の調査で数値だけを fixlist に書き、URL・日付・原文を残さなかった。
> 数値の出所を後から検証できない状態は「見ていないものを根拠にする」のと同じ構造なので、
> 2026-07-29に裏取りし直してここに固定した。**数値を使うときはこのファイルを引く。**
> 基準を更新するときは行を消さず、日付つきで追記する（却下した数値も残す）。

## 1. カット尺・視覚変化の密度

出典: [Aibrify「Short-Form Video Editing at Scale: Captions, B-Roll, and the 2026 Pacing Model」](https://aibrify.com/blog/short-form-video-editing-captions-b-roll-guide) （2026-04-22 公開・2026-07-29 に本文を取得して確認）

| 項目 | 数値 | 原文 |
|---|---|---|
| 視覚変化の密度 | **10秒あたり5〜7回** | "The target is 5–7 clicks per 10 seconds." |
| 遅い | 4回未満 | "Below 4, the pacing reads as slow and retention drops." |
| ノイズ | 8回超 | "Above 8, the pacing reads as noise." |
| 認識の下限 | **1.2秒** | "Shorter than 1.2 seconds, the brain cannot process what the shot was showing." |
| 挿入映像の尺 | 1.5〜3.0秒（60秒未満の動画） | — |

**「視覚変化」に数えるもの**（原文 "A cut. A camera move (push, pull, pan, tilt). A text overlay replacement. A zoom. A color shift. A reveal."）:
カット / カメラの動き（プッシュ・プル・パン・チルト） / テロップの差し替え / ズーム / 色の変化 / リビール

★重要な含意: **これは「編集回数」ではなく「刺激の密度」**。記事は
"a slow push-in can replace a cut if it delivers equivalent visual change" と述べており、
**カットを増やせない区間（実演中など）はズーム・テロップで密度を作ってよい**。
17_DECKVANのゲート開閉区間はこれに該当する。

## 2. カット間隔

出典: [OpusClip「The Ideal YouTube Shorts Length & Format for Retention (Data-Backed)」](https://www.opus.pro/blog/ideal-youtube-shorts-length-format-retention)

- 伸びているShortsは **2〜4秒に1カット**
- TikTok/Reelsは 1〜3秒のクリップ

参考: [vidpros「Video Clip Length: Ultimate Guide」](https://vidpros.com/video-clip-length/) — 広告・コマーシャルは2〜5秒ショット。
平均ショット長は1930年の12秒から現在約2.5秒まで短縮している。

## 3. フック（冒頭）

出典: [CapCut「Short-Form Video Hooks: First 3-Second Patterns」](https://www.capcut.com/create/short-form-video-hooks-first-3-second-patterns) ／
[HypeNest「TikTok Algorithm 2026: 7 Hooks for Retention」](https://hypenest.ai/blogs/tiktok-algorithm-2026-video-hooks-retention) ／
[Cloudix Digital「The 3-Second Hook Rule for 2026」](https://cloudixdigital.com/short-form-video-mastery-how-the-3-second-hook-rule-drives-social-discovery-and-roi/)（2026-07-29 検索で確認）

- 視聴者は **2〜3秒**で見続けるかを決める
- **離脱の大半は0〜3秒**に集中する
- 冒頭で**25%超**を失うと（"Hook Drop Delta"）プラットフォームがリーチを絞る
- 3秒時点の残存率が**70%超**の動画はバイラル化しやすい（Deloitte Digital Media Trends 2025/2026 の引用）
- 2026年、**3秒残存率がReels/Shortsのアルゴリズムの主要シグナル**になった
- **名乗り・挨拶・前置きから始めるのは完視聴率を最も下げる**

★2026-07-27版から訂正した数値:
- 旧「離脱の50〜60%が最初の3秒」→ 出典を再確認できず。**「離脱の大半が0〜3秒」「25%超失うとリーチが絞られる」に置き換える**
- 旧「冒頭3秒の離脱率65%超でレコメンド大幅制限」→ 同上。**「3秒残存70%超でバイラル化しやすい」を正とする**
- 旧「5秒時点で50%以上残るかが指標」→ 出典を再確認できず。**削除**

## 4. 歯止め（速く切りすぎない）

- Aibrify: 1.2秒未満のショットは認知過負荷になる — "Below 1.2 seconds, the brain treats the pacing as noise and tunes out."
- 一般則: 何か視覚的に意味のあることが**3〜5秒に1回**起きればエンゲージメントは保たれる（[motionedits](https://motionedits.com/the-art-of-pacing-how-we-edit-for-maximum-engagement/)）
- **ペースは物語に従う。話が運べる以上に速く切ると逆効果**

★この歯止めは飾りではない。2026-07-29の検算で、
**自分の書いた修正指示のうち6件が1.2秒未満だった**（Codexが3件、機械検算が残り3件を検出）。
基準を持たずに「テンポを上げる」と、認識されない画を置く指示になる。

## 5. 使い方（この基準を指示に落とすときの順序）

1. `tempo_shape.py` で完成動画の実測（10秒窓ごとの視覚変化回数・ショット尺の分布）を出す
2. 基準（1節・2節）と突き合わせて、遅い区間とノイズ区間を全数列挙する
3. 各区間で「カットを増やす」か「ズーム・テロップで密度を作る」かを、実演の有無で決める
   （実演中はカットで隠さない → 1節の "a slow push-in can replace a cut" を使う）
4. 挿入する素材は**実尺を検算**してから指定する。1.2秒未満と素材範囲外を機械で弾く
5. 全指示を反映したあと、**10秒窓の回数を再集計**する（増やす指示と減らす指示が同区間に立つ事故を防ぐ）
