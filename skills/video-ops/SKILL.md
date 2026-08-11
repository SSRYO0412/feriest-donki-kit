---
name: video-ops
description: "動画制作・修正案件の単一入口ルーター。新しい動画案件を始めるとき・どのスキルを使うか迷うとき・『動画案件』『映像案件』『ショート動画作りたい』『広告動画』『この参考みたいに作って』『修正依頼が来た』と言われたら、個別スキルより先に必ずこれを使う。5問で案件の型（時間骨格・レンダラー・素材リスク・量産形態・台帳方式）を確定し、該当スキル群と工程順へルーティングする。"
user-invokable: true
---

# video-ops — 動画案件の単一入口（ルーター）

> なぜ在るか: 9スキルの description マッチ任せでは「どれが発火するか」が確率的で、
> skill 不使用・工程飛ばしが再発した（canon 31/33）。入口を1つにし、
> ルーティングを質問票で決定化する。判定の正本は
> `_video-core/pipeline/references/PROJECT-ROUTER.md`（必ず参照）。

## 手順0（ルーティングの前に・PRINCIPLES §15）

**①案件memory → ②README.md → ③HANDOFF等の引き継ぎ書 → ④skill の順に全文読む。**
既存案件なら Notion の動画台帳・修正台帳も読む。「無い/未着手」と判断する前に
案件側の決定事項を確認する。ここを飛ばして下の質問に答えない。

## 5問ウィザード（回答は project.json に記録する）

| # | 質問 | 選択肢 → 帰結 |
|---|---|---|
| Q1 | **時間の骨格は誰か** | (a)収録発話=footage-first → 型A/D ／ (b)台本・コンテ+VO=script-first → 型B/C・**VO先行** ／ (c)参考タイムライン=reference-first → 完全転写・**構築前にモーラ/秒検算ゲート必須** |
| Q2 | **レンダラー** | Premiere（テロップ=MOGRT v22・プロキシ=AME低解像度）／ Remotion ／ ffmpeg ／ CapCut |
| Q3 | **素材リスク** | 手持ち撮影・撮影間移動が多い → **初回から STRICT 提案**（指摘を待たない） |
| Q4 | **量産形態** | 単発 → QC=FULL ／ シリーズ → 初号機FULL＋2本目以降DELTA（ユーザー承認で確定） |
| Q5 | **修正台帳の方式** | 商材・構成が動画ごとに違う → 動画ごと専用DB（既定）／ 同一構成バリアント量産 → 共有DB+リンクドビュー |

詳細な判定規則・各分岐の工程列は `PROJECT-ROUTER.md` が正本。

## ルーティング表（この型ならこのスキル群）

| 案件の形 | 入口の次に読む | 工程の背骨 |
|---|---|---|
| ショート動画 制作（型A/D: 収録あり） | `short-video-pipeline` | [0]footage-asset-db → [0R]reference-video-clone TIMELINE-SHEET → [1.5]script-from-footage（台本なし時）→ [2]short-video-cut-craft → [4-9]pipeline → 検品 short-video-qc |
| 商品広告・コンテ駆動（型C: script-first） | `PROJECT-ROUTER.md` 型C節 | コンテ検算 → 参考分析 → **供給ギャップ照会（試作前）** → VO/構築 → 検品 |
| 参考完全クローン（+C / reference-first） | `reference-video-clone` | TIMELINE-SHEET [R0]〜（[R0]で参考の完成度チェック）→ 完全転写 or 様式移植 |
| Premiere 自動操作を伴う全案件 | `premiere-bridge-ops`（絶対厳守13条） | 接続 → guard 3点照合 → 編集 → 書き出した画素で検証 |
| テロップ再現 | `short-telop-craft`（正本 TELOP-CRAFT） | [2-0]種別分類 → 実測 → **MOGRT v22**（PNG廃止） |
| 修正案件・納品後の直し | `video-revision-db-workflow` | 修正台帳全行 → 保持すべき修正列挙 → 実装 → notion_gate PASS |
| 素材のDB化だけ | `footage-asset-db`（INGEST-v3） | Q0重要度 → 予算カード → 3層インジェスト |
| 間の詰め/伸ばし・テンポ移植・テロップずれ・単語タイムスタンプ・強調解析 | `audio-precision`（正本 AUDIO-PRECISION） | [W]words正本 → [P]参考の間プロファイル → [E]間編集（語不可侵） → [V]実測ゲート → [T][S]テロップ同期検算 |

## 実行強制（読んだかどうかに依存しない仕組み）

- 各工程スクリプトは `preflight.py`（`_video-core/pipeline/scripts/`）で前提成果物を検査し、
  無ければ「何が先か」を表示して止まる。**順序はコードが守る**
- 案件フォークには SessionStart hook（案件現在地の自動注入）と
  PreToolUse hook（納品パス保護）が配線される（`_video-core/ops/hooks/`）
- 新案件のスカフォールドは `fork_project.py`（`_video-core/ops/scripts/`）——
  5問の回答から project.json・CLAUDE.md・hooks・Notion 12DB 生成までを一括で行う

## 締め（全案件共通）

- 検品の三大禁止: 観察の捏造／自己採点／工程スキップ（short-video-qc）
- 上書き禁止・却下版保持・採用が動いたら即 Notion（VERSIONING）
- セッション終了時に**収穫チェック**（revision-checklist §収穫 / `harvest_check.py`）——
  今回の学びを canon・正本へ焼き込んでから終える
