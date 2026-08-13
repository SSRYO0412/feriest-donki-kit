---
name: short-video-pipeline
description: "ショート動画制作の全体ワークフロー（v2・3層分離）。新しい動画案件を始めるとき・カット編集/テロップ/SE/検品/レンダーの制作パイプラインを回すとき・『ワークフローで』『パイプラインで』『プロキシで確認』と言われたら使う。正本JSON→DAG自動再実行→ffmpegプロキシ→Gemini通し視聴→承認→Premiere配置の流れを、案件非依存エンジン（_video-core/pipeline）＋制作型テンプレ＋案件プロファイル1枚で運用する。"
user-invokable: true
---

# short-video-pipeline — ショート動画制作ワークフロー v2（入口）

> 正本の所在: 工程の詳細＝`~/.claude/skills/short-video-qc/references/WORKFLOW.md`／
> エンジン＝`~/.claude/skills/_video-core/pipeline/`／検品＝`short-video-qc`／
> インジェスト＝`footage-asset-db`（INGEST-WORKFLOW-v3）／選定＝`short-video-cut-craft`
> （参考ありは REF-DRIVEN-SELECTION.md・下位規則に SELECTION_PROTOCOL / CUT-QC-RULES）。
> 横断原則は `_video-core/PRINCIPLES.md`。本書は入口と設計原則の要約。

## 設計原則（6つ・2026-07-29ユーザー承認）

1. **正本はJSON/py。Premiereは純レンダラー** — 演出（ズーム・色・トランジション含む）は
   すべて正本に書く。Premiere側で演出を足すことは禁止（プロキシ承認の意味が壊れる）
2. **視聴の入れ子** — 組む前に守る「内容」（[3.5]採点ループ）と動きで守る「知覚」（[6]G19通し視聴）
   の二段。機械ゲートは視聴の裏付け役
3. **DAG自動再実行＋停止点** — 人の承認は[3]シート・[7]視聴、＋参照駆動案件は[2]内のビート整列承認（align）を加えた最大3箇所（2026-07-30決定）。明示指示でスキップ可（理由は必ずログ）
4. **高価な手戻りは組む前に消化** — 組み直し級は[3]で、微調整級だけが[6]以降に残る
5. **検出器・ゲートは陽性データで検証してから使う** — 実データ0件は「問題なし」と
   「検出器が壊れている」を区別できない
6. **採番はランナー自動＋git** — 「この正本の組→このプロキシ」を機械的に固定。手動 _vNN は廃止

## 全体フロー

```
[0] 素材インジェスト  ★正本=footage-asset-db INGEST-WORKFLOW-v3（Q0重要度→プロファイル→予算カード
                     →機械全コマ×agy16×Codex20の3層→conflict人裁定→asset_windows v2）
[0R] 参考分析        ★正本=reference-video-clone TIMELINE-SHEET（[R0]〜[R6]・1秒シート→
                     style_profile.json。+C/参照駆動案件のみ）
[1] 音声正本         語と無音の確定
[1.5] 台本化         ★正本=script-from-footage（台本なし案件のみ）: 使い/不使い選定→
                     参考トレース（行尺予算・ループ・絵変わりを台本時点で設計）→
                     R1〜R10検算→script.json正本化。承認は[2]align承認と統合
[2] 構成設計         ★正本=short-video-cut-craft。参考ありは REF-DRIVEN-SELECTION
                     （3軸評価S0〜S8・ビート整列承認=align停止点）／参考なしは従来5層。
                     供給不足スロットは v3 [W6]掘り直しへ戻るループ
[3.5] ★採点ループ    ←— 組む前の関門（★承認シートは2026-08-12 廃止。これが唯一の関門）
                     参照駆動=3軸スコアカード／従来=単一ルーブリック。Codex敵対採点で95点まで反復。
                     AI採点ループ=上限5R・機械ゲートループ=0件まで無制限
[4] アセンブリ       タイムライン→完成音声→telops.json確定（★様式入力=style_profile+telop_ledger・
                     同期/幅/文節/誤字は機械検査）→SE。telop_mode=premiereはテロップレンダーなし
[5] プロキシ合成     ffmpeg直・数十秒（telop_mode=premiereはテロップなし＝カット/テンポ/音に専念）
[6] G19通し視聴＋機械検品 → ★欠陥を級別ルーティング: 選定級→[2]S3〜S4再クエリ／アセンブリ級→[4]／
                     テロップ級→[8.5]。素材起因の発見は窓DBへ還流（数値正本=gates universal_thresholds）
[7] 人の視聴承認     ←— 停止点（telop_mode=premiereは「テロップなしのカット確認」と明記）
[8] Premiere配置     ★【トリム敷設】素材を切り出さずin点/out点で置く（PRINCIPLES §16・違反厳禁。
                     cutlistのsrc_in/src_outをそのまま渡す。place_premiere.py で配置jsxを生成）
                     →クリップ数＋尺(end-start)突合→★テロップ一括投入（telops.json+telop_ledger準拠。
                     ★実装は MOGRT v22 方式=TELOP-CRAFT[4]A。PNG方式は廃止・2026-08-09）→タイムラインdiff
[8.5] テロップ検品   全テロップのフレーム書き出し→px照合（measure_telop_px×telop_ledger）＋目視3点
                     （幅/改行/文字量）＋入りアニメ確認。修正は必ずtelops.jsonへ戻して再投入
[9] 本番レンダー     実測検品（short-video-qc G00〜G80）＋G19最終視聴。参照駆動は完成品を
                     1秒グリッドで参考と横並び照合（TIMELINE-SHEET [R6]）
[10] 学習ループ      公開後の維持率で基準値更新（将来）
```

## 5正典の接続（2026-07-30整合）

```
footage-asset-db（供給: INGEST-v3 → asset_windows v2）
      ↓ 窓                          ↑ [W6]掘り直し（選定中の供給不足）
reference-video-clone TIMELINE-SHEET（需要: 1秒シート → style_profile.json）
      ↓ 台本設計値・スロット譜
script-from-footage（台本化[1.5]: 使い選定→参考トレース→script.json）※台本なし(型A系)案件のみ
      ↓ 台本ビート
short-video-cut-craft REF-DRIVEN-SELECTION（選定: 3軸評価 S0〜S8）
      ↓ cutlist / broll
short-video-pipeline（本書: DAG [3]〜[9]・停止点 align/sheet/watch）
      ↓ プロキシ / 本番
short-video-qc（検品: G00〜G80。gates universal_thresholds＝数値の単一正本）
      ↑ 還流: 検品知見→窓DB（windows.py set）／判断→grammar.jsonl（検品するたび資産が賢くなる）
```

## 新しい案件の始め方（3層分離）

0. **★案件文書を先に全文読む**（PRINCIPLES §15）: ①案件memory → ②README.md →
   ③HANDOFF等の引き継ぎ書 → ④skill の順。「無い/未着手」と判断する前に案件側の決定事項を確認する。
   続いて **`_video-core/pipeline/references/PROJECT-ROUTER.md` の5問**で案件の型・時間骨格・
   レンダラー・QCプロファイルを確定する（時間骨格が script-first / reference-first の案件は
   [1]→[1.5] の順序が変わる。ルーターが正）
1. **制作型を合成で決める**（2軸×修飾×素材規模。詳細は `_video-core/pipeline/README.md`）:
   基底型= 型A 撮って出しフリートーク（収録×台本なし）／型D 台本×演者（収録×台本あり）／
   型B 台本×生成VO（生成×台本あり）。修飾= +C 参考クローン（どの型にも前置可）。
   例: 参考あり・台本あり・演者が話す・素材豊富 → **型D＋C＋フルインジェスト**
2. `_video-core/pipeline/references/project-profile.template.json` を案件ルートへ `project.json` として複製し、
   **実測値**（閾値・素材実尺・参考の構造比率）・NGルール・レンダラー種別を埋める
   （★スパインや型テンプレに数値を書き足さない。案件間で変わるものは全部ここ）
3. `nodes-typeA.template.json`（型Bは未整備・次の型B案件の実物で作る）を `work/nodes.json` へ複製し、
   cmds を案件スクリプトに差し替える
4. 既存成果物がある移行案件は `pipeline.py <project.json> baseline` で基線化

## 日常の回し方

```bash
P=~/.claude/skills/_video-core/pipeline/scripts
python3 $P/pipeline.py project.json status            # 何が古いか・何が承認待ちか
python3 $P/pipeline.py project.json run               # 変わったノードと下流だけ自動再実行
python3 $P/pipeline.py project.json approve sheet --by <名前>
python3 $P/pipeline.py project.json run --skip-approval "<理由>"   # 明示スキップ（記録される）
python3 $P/render_proxy.py project.json               # プロキシ単体（通常はDAG経由）
python3 $P/render_proxy.py project.json --full        # 本番解像度（校正・最終視聴用）
```

- G19視聴は `agy --print-timeout 20m --sandbox --dangerously-skip-permissions --model <profileのモデル> -p "<絶対パス>..."`
  ★相対パス不可／指摘は候補（テロップ文言は480p誤読が混ざる→原寸で裏取り）／1フレーム級は機械ゲート担当
  ★視聴対象は**凍結コピー**（qc/proxy_g19_rNNNN.mp4）にしてから渡す——視聴中にDAGがproxyを
  上書きすると視聴が壊れる（R2 r0014で実際に起こしかけた）。どのrunを見たかの記録にもなる
- 実証実績（18_PJO）: 99入力→91.344秒（設計と完全一致）。通し視聴が機械全ゲート通過の
  真欠陥4件（テロップ取り込みミス2・相槌結合1・知覚的な音のブチ切り1）を検出

## 実装状態（2026-07-29時点）

| 部品 | 状態 |
|---|---|
| A. DAGランナー / B. プロキシ合成器 | ✅ 実装・実証済み |
| 型Aノードグラフ・案件プロファイル雛形 | ✅ |
| G19通し視聴（陽性コントロール3/3） | ✅ ゲート登録済み |
| C.（廃止）承認シート | ❌ **2026-08-12 削除**（使われなかった）。`notion_sheet.py`・ノード `sheet`/`sheet_approval`・NotionテンプレDBを廃止。組む前は[3.5]採点ループ、組んだ後は[6]G19＋[7]視聴承認が担う |
| D. タイムラインdiff `timeline_diff.py` | ✅ 実装・18で検証（手削除を「欠け」・残存を「余分」として各1件だけ正確に検出） |
| E. git運用 | ✅ 18で開始（.gitignoreで重量物除外・ランナー自動commit稼働） |
| 型D: script_align.py（テイク/カバレッジ/逸脱/表記マップ） | ✅ 実装・陽性検証済み（裏側の会話を逸脱として1件だけ正確に検出・ティーレス→キーレスを表記マップで捕捉） |
| 型D/型Bノードグラフ雛形 | ✅ 作成（型Dのcmdsの一部と型Bの中身は実案件の初日に具体化） |
| 素材DBの窓レイヤ（asset_windows） | ✅ 正式昇格（2026-07-29）。windows.py＋qc_inserts --windows-db 接続を陽性/陰性で検証済み |
| カット・剪定エンジン（skill `short-video-cut-craft`） | ✅ 新設（2026-07-29）。ビート台帳/ペーシング実測/全体最適ソルバ/複数案合議/判断文法の5層。18_R2で初回転検証済み（10挿入・qc違反0・温存予約が機械で効く） |
| インジェストv3（footage-asset-db） | ✅ 確定（2026-07-30）。陽性検証済み（正解20窓一致率100%・Codex760/760枚エラー0・conflict2件が正しい箇所）。★windows.py/qc_insertsのv2テーブル接続は初回転タスク |
| 参考動画1秒分析（reference-video-clone TIMELINE-SHEET） | ✅ 確定（2026-07-30）。07参考G2で初回転済み（52行シート・完全再現昇格[R3.5]・Codex敵対検証「概ね十分」） |
| 参照駆動カット選定（cut-craft REF-DRIVEN・3軸評価） | ✅ 正典化（2026-07-30）。実装スクリプト（slot_score_build/axis_scorecard）は初回転で実データと共に構築 |
| 台本化（skill `script-from-footage`・[1.5]） | ✅ 正典化（2026-07-30）。T0〜T8＋SCRIPT-RULES 10条＋フォールバック・ラダー。実装スクリプト4本は初回転で構築 |

## 禁止・鉄則（要約）

- 上書き禁止・却下版保持（git化後はgit履歴が担う）
- 検品の三大禁止: 観察の捏造／自己採点／工程スキップ
- 統計ゲートは落第検出専用。合格は知覚ゲート（視聴）でのみ出す
- 採用が変わったらその場で台帳（`video_ledger` / `render_db`・VOPS Ledger）を更新（未更新のまま完了報告しない）
