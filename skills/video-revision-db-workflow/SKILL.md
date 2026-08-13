---
name: video-revision-db-workflow
description: Generic ledger-backed workflow for video production and revision projects, running on the VOPS Ledger over MCP. Use when a project manages videos, scripts, cuts, footage, correction requests, render py files, QA logs, delivery versions, or when the user says correction requests are in the management DB, wants a video management DB, asks to update revision status/history, or needs a reusable workflow across video projects.
---

# Video Revision DB Workflow

Use the **VOPS Ledger** as the operational ledger, not as a media store. MP4, py, wav, BGM, CTA, and intermediate assets stay on disk; the ledger records the paths, status, decisions, and history.

> ★★**映像管理DBの置き場所は VOPS Ledger（Cloudflare Workers + D1）**。Notion ではない（2026-08-12 改定）。
> ★**Notion には機能を1つも残さない**。承認シートは廃止、1秒分析シートと修正記録DBも台帳へ移した。
> 例外は「過去の Notion 案件を読むこと」だけ。
> **触り方は MCP が第一手段**（`ledger_query` / `ledger_get` / `ledger_upsert` / `ledger_history` /
> `schema_list` / `schema_edit` / `schema_add_column` / `ledger_flush`）。Notion MCP は使わない。
> **運用（キー文法・語彙・書式・監査・ゲート・「人が触るのは修正台帳と修正指示DBだけ」）は一切変えていない。**
> 既存の Notion 案件（案件V 等）は**据え置き**。新規案件のみ台帳で始める。
>
> ★★**映像管理DBの単一規範は `references/ledger-db-contract.md`**（db_key・キー文法・Write Contract・語彙・監査不変条件）。本スキルはその運用手順。
> ★バージョン管理・履歴保全の正式規約は `references/VERSIONING.md`（正本: `_video-core/revision/`）。命名規約（`render_<動画ID>_v<NN>_<slug>.py` ↔ 同v番号MP4）・修正案件ディレクトリ規約・履歴追記書式・更新トリガー・納品規約（cp -n / 採用版明記 / 本数検算）はそちらが正。
> ★着手前/実装/検品/納品前の具体手順は `references/revision-checklist.md` を毎回開いて1項目ずつ潰す。
> ★★★**案件で最も重要な成果物は「修正台帳」**（`revision_ledger`。ユーザーが修正指示を出す唯一の窓口）。
> 設計・作成・運用は `references/REVISION-LEDGER.md` を**動画を触る前に**全文読む。
> `ledger.md` はローカルの下書きであって修正台帳ではない（混同禁止）。
> ★★★**時系列と複数本運用は契約§10が絶対**: 時間軸のあるDBは「0秒から時系列」ビューを `schema_edit` の
> `set_view` + **`first: true`（既定ビュー）**で設定し、**`ledger_query` で実際に引いて先頭0秒を確認してから完了と言う**（ユーザーから3回指摘）。
> **動画ごとの分離は `scope: per-video`**（契約§10-2。`video_id` で分かれる。**動画ごとに別DBは作らない**）。
> ★納品前は `scripts/notion_gate.py vops:<project_id>`（export→autolink→audit→check_adoption_sync[A]-[F]を直列実行し、PASS/FAILを `project_ledger.納品ゲート結果` へスタンプ）を必ず通す。バリアント案件は `scripts/check_variant_dupes.py` も。新規修正案件のスカフォールドは `scripts/new_revision_project.py`。

## 台帳への接続（毎セッションの入口）

| やること | 手段 |
|---|---|
| どの会社に繋がっているか | `whoami`（HTTP MCP `vops-<会社>` の場合。`writable` も見る） |
| どのDBがあるか・列は何か | **`schema_list`**（db_key 一覧 / 1DBの列・型・選択肢・ビュー）。**推測で列名を書かない** |
| 行を読む | `ledger_query`（`where`=`[{key,op,value}]`、per-video は `video_id` で絞る） |
| 行を書く | `ledger_upsert`（**触った列だけ**。他の列は消えない。更新は新版として積まれる） |
| 版の変遷 | `ledger_history` / `ledger_get(version=N)` |
| 列・ビューを変える | `schema_edit`（`project_id` を付けると**その案件だけ**、省くと会社共通＝新規案件の初期値） |
| **DBを増やす** | `schema_edit` の **`create_db`**（`name` / `title_prop` / `scope`）。既存DBの意味を歪めずに入るなら増やさない |
| 種の増分を取り込む | `schema_sync`（テンプレに増えたDB・列を自社へ。追加のみ・冪等） |
| オフラインの滞留 | `ledger_flush`（stdio MCP / CLI の書き込みはキューに積まれ、復帰後に送られる。月1回は確認） |

MCP サーバは2系統（同じ台帳）: **stdio `vops-ledger`**（社内。オフラインキュー付き）と
**HTTP `vops-<会社>`**（`vops-projects` / `vops-orgd` / `vops-projectf` / `vops-<your-org>`）。
スクリプトから触るときは既存の `notion_*.py` の**第1引数に `vops:<project_id>`** を渡す（`vops_ledger.py` が互換シム）。

## 標準の17DB（db_key が唯一の識別子。`collection://…` は旧 Notion 案件を読むときだけ）

★**DBの数は固定ではない。** 案件に必要な表が下表のどれにも当てはまらないなら
`schema_edit` の **`create_db`** で増やしてよい（作った直後から書ける・契約§0.3）。

| db_key | 名前 | scope | 役割 |
|---|---|---|---|
| `project_ledger` | プロジェクト台帳 | project | 共通ルール・案件/納品フォルダ・◆納品ゲート結果・◆修正巡目まとめ |
| `video_ledger` | 動画台帳 | project | 採用MP4/py・最終v・◆採用サマリ・◆過去修正メモ（=§5履歴）・残課題 |
| `asset_db` | 素材DB | project | 編集制約台帳。1素材×時間窓=1行（confirmed_by の窓のみ転記） |
| `cut_ledger` | カット台帳 | **per-video** | cut_key のレジストリ。**編集後の制作記録** |
| `asset_use_db` | 素材使用DB | project | どの素材がどの動画/カット/秒に出るか・なぜ |
| `revision_request_db` | 修正指示DB | project | **横断・方針レベル**の指示の受付 |
| `render_db` | レンダーpy管理DB | project | **版履歴の正本**。1レンダー=1行（却下版も） |
| `qa_log_db` | QAログDB | project | 検品結果と証跡パス・3軸/突合の数値 |
| `schedule_db` | 工程・スケジュールDB | **per-video** | 工程[0]〜[9]と停止点 |
| `telop_check_db` | テロップチェックDB | **per-video** | 1行=1ナレーション行（字/秒・文字数・表示秒数・RMS） |
| `transcript_db` | 文字起こしDB | **per-video** | ★1行=1セリフ。**全文をそのまま入れる**。AI一次判定(`AI採否`)→人が確定(`採否`) |
| `script_db` | 台本DB | **per-video** | 1行=1台本行。編集前の上流。DROP行も理由付きで残す |
| ★`revision_ledger` | 修正台帳 | **per-video** | ★**案件で最も重要な成果物**。1カット=1行 |
| `project_rules_db` | 案件ルール・つまずきDB | project | ★**案件の正本**。ルール（こうやる）とつまずき（こうなった）を `種別` で1つに。SessionStart で自動注入 |
| `revision_record_db` | 修正記録DB | project | ★py・スクリプトを作る/直すたびに1行（変更内容・変更理由・検証方法・採用状態） |
| `ref_sheet_db` | 参考動画1秒分析シート | **per-video** | ★1行=1秒。`video_id` に参考動画ID `ref_<slug>`・画像は `スクショパス` |
| `skill_db` | 関連スキルDB | project | ★この案件で使うスキル。**1ファイル=1行で本文ごと**持つので、GitHubが無い人でも `skill_sync install` で復元して使える |

★**標準17DBは減らさない・改名しない**（監査・ゲート・リンカーがキーで結合しているため）。
案件ごとの列の違いは**差分**で表す（`schema_edit` に `project_id` を付ける）。
★**増やしたDBは監査・ゲートの対象外**なので、納品の可否に関わる記録は標準DBへ書く。
★**Notion 検索で既存DBを探す手順は廃止**。`schema_list` が既存確認そのもの（同名DBの二重作成事故は構造的に起こらない）。

## Write Contract（誰が何を書くか。契約§2）

- **エージェントが書く(必須)**: テキストキー（`video_id`/`render_key`/`cut_key`。行作成時、手元にある文字列。**`record_id` にも同じキーを使う**＝更新が冪等になり `ledger_history` がその行の変遷になる）、構造化フィールド（ステータス・採用状態・却下理由・根拠・フルパス・数値）。
- **エージェントが書く(条件付き)**: relation直書きは対象の `record_id` が既にコンテキストにある場合のみ。**IDを調べに行ってまで張らない**（案件Vで100%省略された実証を踏まえ、リンクはスクリプトの仕事）。
- **スクリプトのみが書く(手打ち禁止列)**: relation一括（`notion_autolink.py`）、`video_ledger` の採用サマリ/最終v/採用MP4パス/採用pyパス（=レンダー行から生成する鏡）、整合、納品ゲート結果、VERSIONING§5書式の履歴行。
- **機械起票**: ビルド確定後 `notion_ingest_cutlist.py`（`cut_ledger`・`asset_use_db`・`telop_check_db`）、**レンダーするたび** `notion_log_render.py`（`render_db` 行+`qa_log_db` 行。却下版も1レンダー=1行）。
- ★**`props` は差分パッチ**。変えた列だけ送る。送らなかった列は消えない。

## Core Rule

Before editing any managed video project, read the project's ledger first (`ledger_query`). Treat `revision_request_db` rows with `ステータス` in `新規`, `確認中`, `設計済み`, `作業中`, `レンダー済み`, or `検品中` as active work unless the user says otherwise.

Never use the chat alone as the source of truth once a management DB exists. Update the ledger after rendering, QA, and delivery.

## DB Roles

- `project_ledger`: project rules, root folder, delivery folder, client, status. ◆`納品ゲート結果` / ◆`修正巡目まとめ`（巡目ごとのまとめ・**追記のみ**）。
- `video_ledger`: video name/number, adopted MP4 path, adopted py path, latest v, `過去修正メモ`（**VERSIONING §5 の人間可読履歴はここ**。台帳にページ本文は無い。追記は read-modify-write）, remaining issues.
- `asset_db`: asset path, content, face rule, BGM/audio contamination, usable seconds, prohibited seconds, per-window verdict.
- `cut_ledger`: script/telop per cut, video seconds, source asset, source `tin`, duration, intent, face/crop policy. **編集後の制作記録**（修正指示の受付は下記の修正台帳）。
- ★`revision_ledger`: **案件で最も重要な成果物**。修正指示の受付窓口で 1カット=1行・`video_id` で動画ごとに分かれる。必須4列は `修正指示`(人が書く) / `採否`(採用/修正/DROP/HOLD・人が選ぶ) / `テロップ文言` / `動画内開始秒`。設計・作成・運用は `references/REVISION-LEDGER.md`。
- `asset_use_db`: which asset appears in which video/cut/seconds and why.
- `revision_request_db`: user correction intake and history. Do not delete completed rows.
- `render_db`: every render version, MP4 path, py path, intermediate assets, audio/BGM source, adopted/not adopted.
- `qa_log_db`: visual, audio, one-frame, BGM, CTA, telop, and source checks with evidence paths.
- `telop_check_db`: one row per narration/telop line — 字/秒 (chars/sec, spaces excluded), 文字数, 表示秒数, 元py, ステータス, 修正メモ. Use it when the project receives pace/volume/font-size flags (早い/遅い/大きい/小さい); the fix method is `references/telop-pace-volume-method.md` in the vo module (retime ALL lines to one target, iterate the target with user playback, per-line RMS uniformization).
- `script_db` / `schedule_db`: 台本行（レビュー4列・遷移3列）／工程と停止点。
- `project_rules_db`: ★**案件の正本**。決まったこと・転んだことを**その場で** `rules.py add`（後でまとめて、は必ず忘れる）。正本は台帳で、ローカルの `rules.jsonl` と案件スキルは生成物。
- `transcript_db`: **素材の全発話**。★選定せず全文を入れ切る／AIは `AI採否` だけ触り**人の `採否` を上書きしない**／`話者` と `採否` は選択列。タブで「全文/AIが採用/人が未確認/確定/食い違い」を切り替える。
- `skill_db`: **この案件で使うスキル**。着手時に読み、スキルを直したら `最終更新日` を更新する。
- `revision_record_db`: **py・スクリプトの変更1件=1行**（`render_db` はレンダー1本=1行。粒度が違うので混ぜない）。作った/直したその場で書く。却下版も残す。
- `ref_sheet_db`: 参考動画の1秒グリッド分析。設計と生成手順は `reference-video-clone/references/TIMELINE-SHEET.md`、投入は `ref_sheet_push.py`。

## 人が書き込む口（UI）

`https://vops-ledger.<your-org>.workers.dev/` — 会社ID＋ページパスワードでログイン。
**表のセルを直接編集する**（行をクリックしてもページは開かない。確定した列だけが新版として送られる）。
`scope: per-video` のDBは**動画を選んでから中に入る**。
ユーザーへ渡すときは **URL ＋「どこに何を書くか」の1文**（納品ファイル名と全カット数を含める。`REVISION-LEDGER.md` §3.4）。

## Adoption History (hard rules)

- **バージョン履歴の正本 = `render_db` の全行**（v・採用状態・却下理由・根拠・判定日。却下版も1レンダー=1行で必ず登録する — 登録漏れはcheck_adoption_sync[F]が検出）。`video_ledger` の採用系セルはリンカーが書く鏡であり手打ちしない。
- **採用が動いた瞬間のエージェント操作は2つだけ**: ①`render_db` 行の`採用状態`をフリップ（新採用行→採用、旧採用行→旧採用） ②`video_ledger` の`採用レンダー`relationを差し替え。§5書式の履歴行（`YYYY-MM-DD: v<NN>採用 ← v<MM>却下(<理由>)。根拠=<実測/承認>。py=<path>`）・採用サマリ・鏡列は `notion_autolink.py --apply` が生成する。Batching updates for later is a violation.
- **A/Bバリアント併採用は1セルに詰め込まない**。バリアントはレンダー行の属性（`バリアント`select+render_keyサフィックス）とし、`video_ledger` の`採用レンダー`relationがバリアントごとに1本ずつ採用行を指す。不変条件: **(video_id, バリアント)ごとに採用=ちょうど1行**。
- **Append history with dates; never overwrite-erase.** 台帳は更新のたびに新版を積む（`ledger_history` で全版読める）が、**それに頼って `過去修正メモ` を省かない**。版履歴は「何が変わったか」であって「なぜ採用が動いたか」ではない。
- **Never report "完了" while the gate is failing.** `notion_gate.py vops:<project_id>` のPASSスタンプ（`project_ledger.納品ゲート結果`）を完了報告に引用する。Before starting any work, re-read `video_ledger` for the current adoption — the chat is not the source of truth.

## User Intake Rules

★**受付は2系統。粒度で使い分ける（どちらに書かれたものも指示として同格）。**

| | `revision_ledger`（★主） | `revision_request_db` |
|---|---|---|
| 粒度 | **1カット=1行** | 1指示=1行 |
| 並び | 動画の時間軸（0秒から） | 受付順 |
| 得意 | 「この絵をこう直して」＝対象が絵で特定できる指示 | 「全動画のテロップを大きく」＝横断・方針レベル |

**カット単位で特定できる指示は修正台帳へ。** 作り方・運用は `references/REVISION-LEDGER.md` を全文読む。

以下は `revision_request_db`（横断・方針レベル）の起票ルール:
- Use `revision_request_db` as the intake point.
- `対象video_id` must be an actual video id, not a vague label（カンマ区切り可。全動画なら `全動画対象` checkbox）。
- Use `全動画対象` only for instructions that truly apply to all videos.
- Put exact seconds in `対象秒数`（`10.5-13.0s` 形式）, type in `修正種別`, and concrete instructions in `指示内容`.
- Preserve completed instructions as history by setting `ステータス` to `修正完了` or `納品済み`; do not delete them.

## Work Loop

1. `whoami` で会社を確認 → `schema_list` で db_key と列を確認する（列名を推測しない）。
2. `ledger_query`（`db_key=revision_request_db`）で active な行を引く。
3. For each target video, read `video_ledger`（現採用）と過去の `revision_request_db` 行、`過去修正メモ` を読んでから計画する。List previous accepted fixes so they do not regress.
4. ★**`revision_ledger` の全行を読む**（`video_id` で絞る。`修正指示` が空でない行・`採否`＝修正/DROP の行を漏らさない）。そのうえで `cut_ledger`, `asset_use_db`, `asset_db` を見て、exact cut id, source asset, source seconds, face rule, intent を確定する。
5. Render from source/py/VO/BGM/intermediate assets. Do not directly patch the delivered MP4 unless the user explicitly authorizes an emergency patch.
6. Output a new v filename. Never overwrite.
7. `render_db` に MP4パス・pyパス・中間素材パス・音声ソース・BGMソースを記録（`notion_log_render.py`。`record_id`=`render_key`）。
8. Run the needed QA and record it in `qa_log_db`.
9. ★`revision_ledger` の行を埋める（`変更区分` / `使用素材名` / `tin`-`tout` / `DROP理由` / `変更履歴` / `修正日` → `ステータス`=修正済み。**触った列だけ** `ledger_upsert`）。あわせて `revision_request_db` の行も status / 完了日 / 対応後メモ を更新する。
10. When the user accepts or delivery is complete: flip `render_db` の採用状態 + `video_ledger` の採用レンダーrelation (Adoption History章の2操作)。
11. **セッション終了時**: `notion_autolink.py vops:<project_id> --apply`（relation・鏡列・履歴行の生成）。**オフラインだったセッションは `ledger_flush` で滞留を送る**。
12. **納品前・完了報告前**: `notion_gate.py vops:<project_id> --scan <ローカルpy/renders dir>`。PASS以外で完了報告しない。

## Non-Negotiables

- Keep the render py for every output.
- Keep intermediate assets, regenerated audio, CTA assets, slow/holdpad clips, and BGM sources.
- Do not make the final MP4 the source of truth.
- Do not overwrite output files.
- Do not revert previous accepted fixes while addressing a new correction.
- Touch only the target cut or target audio section unless the instruction explicitly requires broader change.
- For audio trouble that persists after trims/fades, regenerate the audio rather than masking the issue.
- For one-frame visual issues, inspect dense frame sequences rather than contact sheets alone.
- ★台帳の値が自分の記録と食い違ったら、**まず `ledger_history` を引く**。ユーザー操作の可能性を先に検討し、**上書きする前に確認する**（契約§10-5 の事故）。

## Status Semantics（正規語彙4系統。契約§4。混用は監査WARN/FAIL）

**`revision_request_db`**: 新規/確認中/設計済み/作業中/レンダー済み/検品中/修正完了/納品済み/却下/保留
- `新規`: user entered it; no work has started.
- `確認中`〜`検品中`: work in progress (read → plan → render → QA).
- `修正完了`: fix is done but not necessarily delivered. `納品済み`: delivered; keep as history.
- `却下`/`保留`: do not work unless the user reopens it.

**`render_db` `採用状態`**: 採用/却下/旧採用/未判定（旧採用=採用交代の履歴を行のまま保持）
**`qa_log_db` `結果`**: OK/NG/条件付きOK
**`video_ledger`**: 制作中/修正中/納品済み/アーカイブ

レガシー対応表（監査が変換提案）: 確認済み→OK / 修正済み→修正完了 / 要再確認→条件付きOK / 不採用→却下 / 検品待ち→未判定 / 破棄予定→却下 / 参考→却下。

★この4系統だけは**閉じた語彙**として扱う（台帳の select は既定 `open: true` なので、書けてしまう。書かない）。
それ以外の select（素材の種類・タグ等）は毎回増える前提で `schema_edit` の `add_options` で足す。
