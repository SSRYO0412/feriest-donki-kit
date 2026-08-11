# データ形式（スキーマ）

> バリデータの原則: **必須項目が1つでも欠けたレコードがあれば、その工程はFAILとして停止する。**
> スキップフラグはどのスキーマにも存在しない（意図的に用意しない）。

## gates.json（qc/gates.json — gates.template.json をコピーして使う）

```json
{
  "project": "<案件名>",
  "created_at": "<ISO8601>",
  "gates": [
    {"id": "G00", "name": "参考動画ハッシュ照合", "executor": "claude", "tool": "sha256sum",
     "evidence": "qc/ref_hash.json", "pass_condition": "hash一致", "status": "pending"}
  ]
}
```
- `status` は pending / pass / fail の三値のみ。**skip は存在しない**
- `evidence` が空文字の工程は登録できない（バリデータで弾く）

## video_profile.json（qc/video_profile.json）

```json
{
  "type": "vertical_short | horizontal | long",
  "no_change_limit_sec": 2.5,
  "silence_limit_sec": 0.25,
  "min_shot_sec": 0.40,
  "subject_tag_max_repeat": 2,
  "basis": "参考動画<名>の実測: <根拠>"
}
```

## slots.json（設計証跡・制作側が作る。検品はこれを検査する）

```json
{
  "beats": [
    {
      "id": "B03",
      "section": "山",
      "pace": "溜め",
      "need": "見せ場の実体を画で見せる",
      "elements": {
        "main_cut":  {"candidates": [/*5件*/], "selected": 0},
        "insert":    {"candidates": [/*5件*/], "selected": 2},
        "telop":     {"candidates": [/*5件*/], "selected": 1},
        "animation": {"candidates": [/*5件*/], "selected": 4},
        "se":        {"candidates": [/*5件*/], "selected": 0}
      }
    }
  ]
}
```

各 candidate（**5件必須**・「置かない/切らない/出さない」を必ず1件含む）:
```json
{
  "desc": "素材Xの2.3〜4.8秒（フラットの別アングル）",
  "score": 90,
  "score_basis": "内容一致45/寄り引き12/新鮮さ15/尺10/画質8",
  "tempo_impact": "-5.6秒（画が変わらない区間が10.1→4.5秒に）",
  "seen": ["qc/frames/X_2.3.jpg", "qc/frames/X_3.5.jpg"],
  "why": "見せ場の実感を語る区間なので実体の画が正しい"
}
```
- `seen` が空の候補は無効（見ずに点を付けた証拠）。**seenは2系統**（2026-07-29 ユーザー承認）:
  - `seen_claude` … Claudeが1枚ずつReadしたパス。`evidence_scan.py` がセッション記録と突合して検証
  - `seen_codex` … G20/G21/G22の全数観察でCodexが見たもの。`coverage_verify.py` が被覆100%を検証済み
  - **却下候補は `seen_codex` で足りるが、採用候補（差し替え先）は `seen_claude` が必須**
    ——実物を自分の目で確認せずに差し替え指示を出さない、という線引き
- `tempo_impact` が空の候補は無効（テンポとの往復をしていない証拠）

## decisions.json（ルール衝突の記録）

```json
{
  "decisions": [
    {
      "id": "D-001",
      "rule_kept": "R-短ショット0件",
      "rules_affected": ["R-語を言い切る"],
      "tradeoff": "断片を削除区間に回すと語尾0.1秒が欠けるリスク",
      "reason": "波形実測で該当区間は無発話と確認したため削除を採用",
      "codex_approval": "qc/codex_view/decision_D-001.json"
    }
  ]
}
```

## claude_seen.json（Claudeが読んだ画像の申告）

```json
{"seen": ["qc/frames/f0001.jpg", "qc/frames/f0002.jpg"]}
```
- evidence_scan.py の実測と突合され、**申告にあるのに実Readが無いものが1件でもあればFAIL**

## codex_view/*.json（Codex観察の生記録）

```json
{
  "target_dir": "<パス>",
  "total_files": 51,
  "prompt": "<送った依頼文全文>",
  "response": "<Codexの返答全文・無編集>",
  "self_reported": "51/51"
}
```
- coverage_check.py が `response` に全ファイル名が列挙されているかを照合

## scoring/（採点）

- `agent.json` / `codex.json`: `{"total": 93, "items": {"内容一致": {"score": 27, "max": 30, "reasons": ["..."]}}, "graded_by": "..."}`
- `final.json`: 合議の結果。**このファイルが無い限り報告書に点数は出ない**
```json
{
  "total": 92,
  "items": { "...": {"agent": 27, "codex": 25, "agreed": 25, "discussion": "s015の説得力不足はCodexの指摘が妥当。低い方を採用"} },
  "process": "1往復の相互指摘を経て合意"
}
```
- 合意できない項目は**低い方を採用**する

## tempo_report.json / machine_report.json / consistency_report.json

- TEMPO.md / PIPELINE.md 参照。共通原則: 全リストは**全数**（上位N件への切り捨て禁止。切り捨てる場合はその旨と件数を明記）
