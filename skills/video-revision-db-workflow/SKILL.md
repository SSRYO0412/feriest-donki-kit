---
name: video-revision-db-workflow
description: Generic Notion-backed workflow for video production and revision projects. Use when a project manages videos, scripts, cuts, footage, correction requests, render py files, QA logs, delivery versions, or when the user says correction requests are in a Notion DB, wants a video management DB, asks to update revision status/history, or needs a reusable workflow across video projects.
---

# Video Revision DB Workflow

Use Notion as the operational ledger, not as a media store. MP4, py, wav, BGM, CTA, and intermediate assets stay on disk; Notion records the paths, status, decisions, and history.

> ★バージョン管理・履歴保全の正式規約は `references/VERSIONING.md`（正本: `_video-core/revision/`）。命名規約（`render_<動画ID>_v<NN>_<slug>.py` ↔ 同v番号MP4）・修正案件ディレクトリ規約・履歴追記書式・更新トリガー・納品規約（cp -n / 採用版明記 / 本数検算）はそちらが正。
> ★着手前/実装/検品/納品前の具体手順は `references/revision-checklist.md` を毎回開いて1項目ずつ潰す。
> ★★★**案件で最も重要な成果物は「修正台帳」**（Notion。ユーザーが修正指示を出す唯一の窓口）。
> 設計・作成・運用は `references/REVISION-LEDGER.md` を**動画を触る前に**全文読む。
> `ledger.md` はローカルの下書きであって修正台帳ではない（混同禁止）。
> ★★★**時系列と複数本運用は契約§10が絶対**: 時間軸のあるDBは「0秒から時系列」ビューを設定し
> **デフォルトビューも直し、query_database_viewで実際に引いて検証してから完了と言う**（ユーザーから3回指摘）。
> **動画ごとに別ページを作り、そのページの中にDBを置く**（契約§10-2・2026-08-08訂正。
> 以前の「1DBに全動画＋GROUP BY」は誤り。選択肢が動画/商材ごとに汚れ、0秒が複数現れて読めなくなる）。
> ★★**Notion DB群の単一規範は `references/notion-db-contract.md`**（キー文法・Write Contract・語彙・監査不変条件）。本スキルはその運用手順。
> ★納品前は `scripts/notion_gate.py`（export→autolink→audit→check_adoption_sync[A]-[F]を直列実行し、PASS/FAILをプロジェクト台帳へスタンプ）を必ず通す。バリアント案件は `scripts/check_variant_dupes.py` も。新規修正案件のスカフォールドは `scripts/new_revision_project.py`。

## Write Contract（誰が何を書くか。契約§2）

- **エージェントが書く(必須)**: テキストキー（`video_id`/`render_key`/`cut_key`。行作成時、手元にある文字列）、構造化フィールド（ステータス・採用状態・却下理由・根拠・フルパス・数値）。
- **エージェントが書く(条件付き)**: relation直書きは対象ページIDが既にコンテキストにある場合のみ。**IDを調べに行ってまで張らない**（VERARUSで100%省略された実証を踏まえ、リンクはスクリプトの仕事）。
- **スクリプトのみが書く(手打ち禁止列)**: relation一括（`notion_autolink.py`）、動画台帳の採用サマリ/最終v/採用MP4パス/採用pyパス（=レンダー行から生成する鏡）、整合、納品ゲート結果、VERSIONING§5書式の履歴行。
- **機械起票**: ビルド確定後 `notion_ingest_cutlist.py`（カット台帳・素材使用・テロップチェック）、**レンダーするたび** `notion_log_render.py`（レンダー行+QAログ行。却下版も1レンダー=1行）。

## Core Rule

Before editing any managed video project, read the project's Notion correction DB first. Treat `修正指示DB` rows with `ステータス` in `新規`, `確認中`, `設計済み`, `作業中`, `レンダー済み`, or `検品中` as active work unless the user says otherwise.

Never use the chat alone as the source of truth once a management DB exists. Update Notion after rendering, QA, and delivery.

## Generic Template

Template page:
`https://app.notion.com/p/3988866ade56813aa6e5f8662185ae0f`

Data sources:
- `映像管理_プロジェクト台帳`: `collection://14d38984-2aca-4984-a030-5836cdde1357`
- `映像管理_動画台帳`: `collection://fe7b5afd-7907-4d7e-8a37-271762c6a33b`
- `映像管理_素材DB`: `collection://a4c926ef-6b83-4f3d-934e-df1734f7d1bb`
- `映像管理_カット台帳`: `collection://a825331a-fabe-4217-b61d-c40100157be8`
- `映像管理_素材使用DB`: `collection://88a1c8de-a36f-44bd-8eda-0acf5c979429`
- `映像管理_修正指示DB`: `collection://b55f8128-06fd-4e2a-b178-5700b7eecb47`
- `映像管理_レンダーpy管理DB`: `collection://c789aeb7-61e0-448f-a9bd-8a61566a069c`
- `映像管理_QAログDB`: `collection://5ea8dfe9-489b-496d-9b48-49fc8f6fed5d`
- `映像管理_テロップチェックDB`: `collection://76b37d99-f2b8-4fcf-a3f1-290f5fed17ba`
- `映像管理_台本DB`: `collection://adc9eb9b-52f2-4fab-8690-ea3956501ec4`（2026-07-30追加）
- `映像管理_工程・スケジュールDB`: `collection://fc2ed2db-e089-473e-ae07-34a440368c96`（2026-07-30追加）
- ★`映像管理_修正台帳`: `collection://c4e0ae61-7f24-4abf-95fa-d81ba09040f0`（2026-08-09追加。共有DB方式のとき使う）
- ★テンプレ実体「📋 修正台帳（テンプレ）」: `https://www.notion.so/green-card/3b78866ade56816683b5c6183f07265a`
  （親＋子ページ雛形＋**動画ごと専用DB(31列)**＋時系列ビュー入り。新規案件はこれを複製する）

★**12DB体制（2026-07-30に11DB化 → 2026-08-09に修正台帳を追加）**。契約§9のとおり台本DB・工程スケジュールDBを追加し、素材DBを窓粒度へ拡張、
QAログDBに3軸/突合の数値列を追加した。**新規案件で作る前に必ずNotion検索で既存インスタンスを確認する**
（同名DBの重複作成禁止・2026-07-30に実際の事故あり）。テンプレ更新時は既存複製へ**差分適用**する（複製し直さない）。

When creating a new project, use these DB types. The exact data source IDs may differ if the template is duplicated; fetch the project page and use its local `collection://...` IDs.

## DB Roles

- `プロジェクト台帳`: project rules, root folder, delivery folder, client, status.
- `動画台帳`: video name/number, adopted MP4 path, adopted py path, latest v, past fixes, remaining issues.
- `素材DB`: asset path, content, face rule, BGM/audio contamination, usable seconds, prohibited seconds.
- `カット台帳`: script/telop per cut, video seconds, source asset, source `tin`, duration, intent, face/crop policy. **編集後の制作記録**（修正指示の受付は下記の修正台帳）。
- ★`修正台帳`: **案件で最も重要な成果物**。修正指示の受付窓口で 1カット=1行・動画ごとに1DB。必須4列は `修正指示`(人が書く) / `採否`(採用/修正/DROP/HOLD・人が選ぶ) / `テロップ文言` / `動画内開始秒`。設計・作成・運用は `references/REVISION-LEDGER.md`。
- `素材使用DB`: which asset appears in which video/cut/seconds and why.
- `修正指示DB`: user correction intake and history. Do not delete completed rows.
- `レンダーpy管理DB`: every render version, MP4 path, py path, intermediate assets, audio/BGM source, adopted/not adopted.
- `QAログDB`: visual, audio, one-frame, BGM, CTA, telop, and source checks with evidence paths.
- `テロップチェックDB` (9th DB, per-line ledger): one row per narration/telop line — 字/秒 (chars/sec, spaces excluded), 文字数, 表示秒数, 元py, ステータス, 修正メモ. Create it when the project receives pace/volume/font-size flags (早い/遅い/大きい/小さい); the fix method is `references/telop-pace-volume-method.md` in the vo module (retime ALL lines to one target, iterate the target with user playback, per-line RMS uniformization).

## Adoption History (hard rules)

- **バージョン履歴の正本 = レンダーpy管理DBの全行**（v・採用状態・却下理由・根拠・判定日。却下版も1レンダー=1行で必ず登録する — 登録漏れはcheck_adoption_sync[F]が検出）。動画台帳の採用系セルはリンカーが書く鏡であり手打ちしない。
- **採用が動いた瞬間のエージェント操作は2つだけ**: ①レンダー行の`採用状態`をフリップ（新採用行→採用、旧採用行→旧採用） ②動画台帳の`採用レンダー`relationを差し替え。§5書式の履歴行（`YYYY-MM-DD: v<NN>採用 ← v<MM>却下(<理由>)。根拠=<実測/承認>。py=<path>`）・採用サマリ・鏡列は `notion_autolink.py --apply` が生成する。Batching updates for later is a violation.
- **A/Bバリアント併採用は1セルに詰め込まない**。バリアントはレンダー行の属性（`バリアント`select+render_keyサフィックス）とし、動画台帳の`採用レンダー`relationがバリアントごとに1本ずつ採用行を指す。不変条件: **(video_id, バリアント)ごとに採用=ちょうど1行**。
- **Append history with dates; never overwrite-erase.** Past adopted values, rejected v numbers with reasons, and the evidence basis stay in the record.
- **Never report "完了" while the gate is failing.** `notion_gate.py` のPASSスタンプ（プロジェクト台帳「納品ゲート結果」）を完了報告に引用する。Before starting any work, re-read `動画台帳` for the current adoption — the chat is not the source of truth.

## User Intake Rules

★**受付は2系統。粒度で使い分ける（どちらに書かれたものも指示として同格）。**

| | `修正台帳`（★主） | `修正指示DB` |
|---|---|---|
| 粒度 | **1カット=1行** | 1指示=1行 |
| 並び | 動画の時間軸（0秒から） | 受付順 |
| 得意 | 「この絵をこう直して」＝対象が絵で特定できる指示 | 「全動画のテロップを大きく」＝横断・方針レベル |

**カット単位で特定できる指示は修正台帳へ。** 作り方・運用は `references/REVISION-LEDGER.md` を全文読む。

以下は `修正指示DB`（横断・方針レベル）の起票ルール:
- Use `修正指示DB` as the intake point.
- `対象動画名` must be an actual video name/number, not a vague label.
- Keep `全部` as an option, but use it only for instructions that truly apply to all videos.
- When a new script/video arrives, add the real video name or number to the `対象動画名` options.
- Put exact seconds in `対象秒数`, type in `修正種別`, and concrete instructions in `指示内容`.
- Preserve completed instructions as history by setting `ステータス` to `修正完了` or `納品済み`; do not delete them.

## Codex Work Loop

1. Fetch the project page and DB schemas.
2. Query active `修正指示DB` rows.
3. For each target video, read `動画台帳` and past `修正指示DB` rows before planning. List previous accepted fixes so they do not regress.
4. ★**修正台帳の全行を読む**（`修正指示` が空でない行・`採否`＝修正/DROP の行を漏らさない）。そのうえで `カット台帳`, `素材使用DB`, `素材DB` を見て、exact cut id, source asset, source seconds, face rule, intent を確定する。
5. Render from source/py/VO/BGM/intermediate assets. Do not directly patch the delivered MP4 unless the user explicitly authorizes an emergency patch.
6. Output a new v filename. Never overwrite.
7. Record the MP4 path, py path, intermediate asset paths, audio source, and BGM source in `レンダーpy管理DB`.
8. Run the needed QA and record it in `QAログDB`.
9. ★修正台帳の行を埋める（`変更区分` / `使用素材名` / `tin`-`tout` / `DROP理由` / `変更履歴` / `修正日` → `ステータス`=修正済み）。あわせて修正指示DBの行も update the correction row with status, completion date, and response memo (関連レンダーはレンダー行側のrelationで辿れる).
10. When the user accepts or delivery is complete: flip レンダー行の採用状態 + 動画台帳の採用レンダーrelation (Adoption History章の2操作).
11. **セッション終了時**: `notion_autolink.py <project_page> --apply`（relation・鏡列・履歴行の生成）。
12. **納品前・完了報告前**: `notion_gate.py <project_page> --scan <ローカルpy/renders dir>`。PASS以外で完了報告しない。

## Non-Negotiables

- Keep the render py for every output.
- Keep intermediate assets, regenerated audio, CTA assets, slow/holdpad clips, and BGM sources.
- Do not make the final MP4 the source of truth.
- Do not overwrite output files.
- Do not revert previous accepted fixes while addressing a new correction.
- Touch only the target cut or target audio section unless the instruction explicitly requires broader change.
- For audio trouble that persists after trims/fades, regenerate the audio rather than masking the issue.
- For one-frame visual issues, inspect dense frame sequences rather than contact sheets alone.

## Status Semantics（正規語彙4系統。契約§4。混用は監査WARN/FAIL）

**修正指示DB**: 新規/確認中/設計済み/作業中/レンダー済み/検品中/修正完了/納品済み/却下/保留
- `新規`: user entered it; no work has started.
- `確認中`〜`検品中`: work in progress (read → plan → render → QA).
- `修正完了`: fix is done but not necessarily delivered. `納品済み`: delivered; keep as history.
- `却下`/`保留`: do not work unless the user reopens it.

**レンダーpy管理DB `採用状態`**: 採用/却下/旧採用/未判定（旧採用=採用交代の履歴を行のまま保持）
**QAログDB `結果`**: OK/NG/条件付きOK
**動画台帳**: 制作中/修正中/納品済み/アーカイブ

レガシー対応表（監査が変換提案）: 確認済み→OK / 修正済み→修正完了 / 要再確認→条件付きOK / 不採用→却下 / 検品待ち→未判定 / 破棄予定→却下 / 参考→却下。
