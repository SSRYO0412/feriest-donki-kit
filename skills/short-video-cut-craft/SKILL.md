---
name: short-video-cut-craft
description: "ショート動画のカット・剪定（選定）専門スキル。A-rollのどの発話を生かす/捨てるか・型Dのテイク選定・B-rollの割当・各カットの尺とテンポを、意味整合×全体構成×参考実測ペーシング×知覚合議で決める。『カット選定』『素材選定』『剪定』『テンポ調整』『どの素材を当てるか』のタスク、および short-video-pipeline の [2]構成設計 の中身として使う。"
user-invokable: true
---

# short-video-cut-craft — カット・剪定専門（ショート動画）

> 位置づけ: `short-video-pipeline` の [2]構成設計 の中身。エンジン=このskillのscripts（案件非依存）、
> 数値（重み・カーブ・閾値）=案件プロファイル、規則語彙=`references/JUDGMENT-GRAMMAR.md`（育てる資産）。
> 横断原則は `_video-core/PRINCIPLES.md`、検品は `short-video-qc`、選定の下位規則は
> `reference-video-clone/references/CUT-QC-RULES.md`（着手前 全文読み・従来どおり）。

## 核の見方

**選定とは「有限の素材資源を、参考実測のテンポ/構成の需要カーブに、意味整合とセンスを
保ったまま割り当てる問題」である。** A-rollのどの発話を生かすか・どのテイクを採るか・
B-rollをどこに置くか・各カットを何秒にするかは、全部この同じ問題のインスタンス。

## 絶対原則（違反厳禁）

1. **スコアは絞り込みと違反防止まで。合格は視聴でしか出さない**（Goodhartの実証:
   全数値PASSの機械編集が差し戻された）。最終選定は複数案の rough proxy を
   agy＋Codex＋Claude の3者合議で決める
2. **情緒・センスの判断はClaudeが書く。コードのif文に埋めない**。コードは列挙・検算・
   描画だけ（beat_ledger の function/emotion/broll_policy はClaude authoring欄）
3. **数値は案件ごと実測**。ペーシングカーブ・重みをスキルに焼かない。参考が変われば再測定
4. **推測になりがちな属性は事実化する**。実演/指示語は該当フレームをagyにYES/NO定型質問で
   見せて確定（qc_intruder方式）。「実演の可能性が高い」を根拠に採否を決めない
5. **「置かない」「捨てる」は正規の選択肢**。顔見せ・実演区間では置かないことが正の利得
6. **温存（reserve）**: 各意味タグの本命スロット（言及強度最大の位置）に最良資源を予約して
   から残りを埋める。前半で良い素材を使い切らない
7. 窓は asset_windows の**人が確定した行のみ**（confirmed_by NOT NULL）。AI提案は根拠にしない
8. 決めた判断は必ず**理由付きで正本に残す**（broll.json の why / no_insert_decisions /
   grammar.jsonl）。上書き禁止・git管理

## ★参照駆動モード（参考動画の1秒分析シートがある案件は必ずこちら・2026-07-30確定）

参考分析シート（TIMELINE-SHEET）と style_profile がある案件では、下の5層の [2]〜[4] を
`references/REF-DRIVEN-SELECTION.md`（正典）の **S0〜S8** で置き換える。要点:
- **3軸評価**: 軸1=1対1の良いカット（スロット局所）/ 軸2=参考に寄せる（系列相対・肝TOP3=100%）/
  軸3=ショートとして高品質（絶対・ゲート0件）。3軸は評価者を分離し、
  **軸2班には参考を見せ、軸3班には見せない（盲検）**。同じAIセッションに3軸を同時に聞かない
- 数値: 軸1=スロット採点（最低スロット点併記）/ 軸2=Fidelity Index+z値+盲検A/B識別率 /
  軸3=ユニバーサルゲート0件+ジャンル帯+盲検評点。数値PASSでも人の通し視聴は省略しない
- 衝突時: 肝（軸2）とゲート（軸3）がハード、軸1はその制約内最大化。
  ハード同士の衝突はconflict台帳→人裁定→grammar.jsonlへ文法化
- 供給不足（候補<3のスロット）は footage-asset-db W6 掘り直しキューへ即登録

## ★厳密にやる場合（厳密なカット選定 — 区間マップ準拠＋相対比較トーナメント）

素材側で `footage-asset-db/references/STRICT-USABILITY-SPANS.md` の final_spans.json が
ある案件（=「使えないカットが混ざる」指摘が出た案件の次周）は、
**`references/STRICT-SELECTION.md`** の T1〜T6 で選定する。
要点: 窓の全フレームが使用可能区間内のみ候補化／意味属性のハードフィルタ（開閉状態×テロップ矛盾禁止）／
テイク内逸脱は減点であって除外ではない／最終順位は絶対評価でなくCodex相対比較トーナメント／
組上げフォールバックでも窓重複は絶対禁止／完成MP4から全カット検品し指摘は系統ごとに現物目視で切り分け。
（2026-08-02 Feriest案件で確立・検証済み）

## ワークフロー（5層）

```
[1] 供給の正本化   beat_ledger.py で発話をビート台帳に → Claudeが機能/情緒/方針を著述
                   → 実演/指示語疑いは agy でフレーム事実化 → 台帳確定
                   ★台本なし案件はこの層を skill script-from-footage（[1.5]台本化）が担い、
                   著述済みビート台帳＋script.jsonを受け取る（二重定義しない・2026-07-30）
[2] 需要の正本化   参考1秒シートあり=**style_profile.json が正本**（TIMELINE-SHEET [R5]・
                   参照駆動モードへ）／なし=pacing_measure.py measure <参考動画> → pacing_curve.json
[3] 割当           select_solver.py: スロット×窓の全候補スコア → 温存/交互/近接/尺帯の
                   制約付きビームサーチ → broll.json（＋置かない判断）→ qc_inserts 必須通過
[3.5] ★採点ループ  Codex gpt-5.5 敵対採点（ルーブリック100点）→ 指摘を
                   実行可能/事実誤認(反証)/素材制約 に3分類 → 著述修正して再ソルバ →
                   **95点以上になるまで反復**（上限5R・自己採点禁止）。
                   95未満のままシートを発行しない。正典: references/SCORING-LOOP.md
[4] 複数案×合議    variant パラメータを振ってN案 → 各案 rough proxy → agy(知覚)＋
                   Codex gpt-5.5(敵対: 1対1/指示語/実演/重複)＋Claude(情緒の弧) → 勝者に
                   次点の良所をグラフト → 承認シートへ（[3.5]と併用可・拮抗時に使う）
[5] 文法の還流     承認シート要修正・G19指摘・ユーザー指摘原文を「状況→判断」で
                   grammar.jsonl に追記 → 重み/禁止規則へ反映（案件をまたぐのは文法だけ）
```

## scripts/

- `beat_ledger.py <profile> [--out qc/beat_ledger.json]` — words→ビート台帳の骨格生成。
  自動欄: 時刻/本文/位置%/ギャップ/指示語hit/実演疑い/mentionタグ/冗長グループ（3-gram類似）。
  著述欄（Claudeが埋める）: function（フック/価格/信頼/正直訴求/CTA/つなぎ）/
  emotion（山/谷/上り）/broll_policy（allow/forbid/preserve）＋reason
- `pacing_measure.py measure <video> [--ref] [--bins 10]` — カット密度カーブ・ショット長分布・
  挿入被覆率を実測（参考側=シーン検出の複数閾値スイープ、設計側=cutlist/brollから全数列挙）。
  `check <profile>` — 設計カーブを pacing_curve.json の帯（±tol）と照合、FAILで差し戻し
- `select_solver.py <profile> [--params k=v ...] [--out work/broll.json]` — 割当本体。
  利得=意味一致+文脈（交互/情緒/温存）+尺帯適合−ペナルティ（重複/近接/単調）。
  制約=資源1回・再登場ギャップ・タグ上限・BANNED・forbidビート。末尾でqc_inserts自動実行
- `variant_confer.py <profile> --grid <json>` — N案生成→各案 rough proxy 合成→
  agy/Codex への審査プロンプト一式を出力（合議と裁定はClaudeが行い、記録する）
- `grammar_log.py add "<状況>" "<判断>" --source <sheet|g19|user> [--quote "<原文>"]` —
  判断文法の追記（`references/grammar.jsonl`。削除禁止・supersedeのみ）
- 参照駆動モード追加分（★初回転で実データと共に構築・未検証の検出器を先に量産しない）:
  `slot_score_build.py`（参考1秒シート→スロット譜）/ `axis_scorecard.py`（3軸一括計算・
  スコアカード出力・pacing z値化を吸収）/ select_solver.py拡張（スロット譜入力・
  クラスタ多様性・リズム帯制約）/ variant_confer.py に盲検A/B・初見視聴・秒別横並びの班別プロンプト

## 案件プロファイルに足す欄（project.json）

```json
"selection": {
  "weights": {"semantic": 45, "framing_alt": 15, "freshness": 15, "duration": 10, "quality": 5},
  "pacing_curve": "qc/pacing_curve.json",
  "beat_ledger": "qc/beat_ledger.json",
  "insert_len_band": {"head": [1.5, 2.0], "mid": [1.8, 2.6], "tail": [1.8, 2.4]},
  "reserve_tags": ["seat_rear"],
  "_beat著述の追加キー": "max_dur=尺上限（短く寄せる） / window_pin={src,from}=窓ピン留め（視聴判断の反映）",
  "solver": {"beam": 200, "near_gap": 8.0, "max_use": 3, "max_tag": 3},
  "ref_driven": {"mode": "リズム移植|完全転写", "ref_sheet": "<参考1秒シートdir>",
    "style_profile": "<style_profile.json>", "fidelity_contract": "qc/fidelity_contract.md",
    "bands_axis3": "ジャンル帯(過去合格+参考群から較正)"}
}
```
初期重みは CUT-QC-RULES の実績値（内容一致45/寄り引き15/新鮮さ15/尺10/画質5/NG−100）。

## 型ごとの差（供給の形式は同じ）

- **型A**（収録×台本なし）: 発話資源=収録words。剪定=冗長グループから1つ残す判断
- **型D**(収録×台本あり): script_align のテイク群がそのまま発話資源。テイク選定も同じ割当
- **型B**（生成×台本あり）: 生成候補が映像資源に入る（生成→窓確定→同じソルバ）

## 検証の掟

- ソルバ出力は必ず qc_inserts（--windows-db 付き）を通過してから正本化
- pacing check は設計値から全数列挙（画像解析の閾値依存に頼らない）
- 検出器・スコアの新設時は**陽性データで検証**（実データ0件は「問題なし」と
  「壊れている」を区別できない）
- 実績（2026-07-29 初回転・18_ACTY_R2）: beat_ledger 22ビート（指示語8・実演疑い2、
  『見てください』『こういった』を正しく捕捉）／著述17ビート（allow9・forbid8）／
  solver 10挿入+置かない8（温存予約 dashcam/seat_rear が機械で効き、手動設計とほぼ同型を
  全体最適で再現。窓の粒度不足も発見→6232を3分割に精密化）／qc_inserts 違反0／
  可視スリバー3ガード（境界スナップ・窓内延長・締めの顔0.40秒確保）／
  pacing design=全数列挙47境界・被覆24%（measureモードは複数閾値スイープで機構検証済み）／
  [3.5]採点ループ初回転: 82→91→**96点**（3R・修正7件+反証3件+エンジン表記根治1件で
  「承認シートに進めてよい」到達。max_dur/window_pinはこのループから生まれた）
