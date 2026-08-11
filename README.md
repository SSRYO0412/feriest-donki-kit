# feriest-donki-kit

ドン・キホーテ（株式会社PPIH）「Feriest」8月掲載分ショート動画を、**このリポジトリと SSD だけで**
組み上げ・修正・検品するためのキット。`video-ops-framework` からフォークしたもので、
**upstream（master）には一切変更を加えていない。**

## このキットで何ができるか

| | |
|---|---|
| **① ゼロから組み上げる** | 0802〜0805 の4本。字コンテ・候補リスト・参考の実測値から設計 → Premiere で実装 → 検品 |
| **② 既存を修正する** | 0801（海老ドーン・構築済み）に修正指示を当てて直す |
| **③ 検品通過を名乗る** | ★**Codex が無い環境で**。40ゲート・独立レビュー36回・参考突合・較正ハーネス |

## 30秒で確かめる

```bash
# 手元の原本と結べているか＋前提ソフトが揃っているか（別マシンでは最初にここ）
# ★環境構築の全手順は HANDOFF.md にある
cp .feriest-paths.example .feriest-paths   # FERIEST_ROOT を自分の場所に書き換える
python3 scripts/check_links.py
python3 scripts/check_links.py --verify-media   # 原本を新規に用意したなら全数照合（188本・約3秒）

# 参考と瓜二つか（完成MP4の画素を実測して参考の実測値と突合）
python3 scripts/reference_match.py \
  --build design/build_0801.json \
  --mp4  data/baseline/0801_baseline_v9.mov \
  --out  qc/reference_match_0801.json

# レビュー機構が既知欠陥を何件捕まえられるか（実測）
python3 scripts/calibration_harness.py mechanical \
  --build design/build_0801.json \
  --mp4  data/baseline/0801_baseline_v9.mov \
  --out  qc/calibration
```

依存は **Python 標準ライブラリ と ffmpeg/ffprobe のみ**。numpy も Pillow も pip も要らない。

## 読む順番（飛ばさない）

0. ★**`HANDOFF.md`** — **別マシンで始めるならまずここ。** 環境構築から着手前チェックまでの全手順
1. **`.fork/PROJECT-RULES.md`** — 恒久ルール15条・★合格条件の上書き宣言・作業の型
2. **`HANDBOOK.md`** — 案件の全体像・★効いた修正の履歴・やってはいけない10箇条
3. **`SETUP.md`** — Premiere CEP Bridge・フォント・動作確認（HANDOFF.md の詳細版）
4. **`skill/donki-feriest/references/`** — 仕様の正本7本
5. **`.fork/lenses/lenses.json`** — 独立レビュー12レンズ

★**この案件で最大の失敗は「案件側の引き継ぎ書を読まずに着手したこと」**でした。
フォントが既に決まっていたのに「無い」と誤断定して別書体に置き換え、全部やり直しになりました。

## 中身

```
HANDOFF.md               ★別マシンで始めるまでの全手順（アクセス権〜着手前チェック）
HANDBOOK.md              案件の全知見（Notionが見られない環境用の正本）
SETUP.md                 環境構築と動作確認（HANDOFF.md の詳細版）

.fork/                   ★追記レイヤ（このフォーク固有。ここだけ書き換えてよい）
  PROJECT-RULES.md       恒久ルール・合格条件の上書き宣言
  project.base.json      案件共通プロファイル（roles から codex を外してある）
  gen_projects.py        projects/*.json の生成器（手で書かない）
  REFERENCE-TARGETS.json ★「瓜二つ」を判定する参考の実測値
  gates.json             40ゲート（gen_gates.py で生成）
  known_defects.json     ★較正ハーネス用・実際に起きた欠陥9件
  lenses/lenses.json     独立レビュー12レンズ

projects/                0801〜0805 の動画別プロファイル（生成物）
scripts/
  reference_match.py     ★G90 参考突合。完成MP4の画素で測る
  calibration_harness.py ★G92 較正ハーネス。検出率を実測する
  resolve_paths.py       トークン（@@FERIEST_ROOT@@ 等）を実パスへ解決する
  check_links.py         ★手元の原本が引けるか検査（Premiereを開く前に通す）

work/                    0801 を実際に組んだ現物
  jsx_20260809/          案件 jsx 98本（絶対パスはトークン化済み）
    _rejected/           ★v20 参照の却下版5本。実行すると即中断する
  premiere/              作業 prproj（採用版＋却下版）

.feriest-paths.example   パス設定の雛形（写して .feriest-paths を作る）
core/ skills/            framework由来（★編集禁止レイヤ）
skill/donki-feriest/     案件スキル（references 7本 + MOGRT + Twemoji + CEP Bridge）
data/
  conte/conte.json       ★字コンテ45スロット（赤入れ後の確定内容・文言変更禁止）
  asset_db/media_manifest.json  在庫表（188クリップの名前と実尺・検収用）
  reference/             参考「0.7人前うどん」prproj + MP4 + ロゴ
  baseline/              0801の現行レンダー（修正の実演の出発点）
design/build_0801.json   0801の構成（G90の入力）
data/revision_aids/      ★修正即応表（軸別代替候補・188本×1秒プロファイル・事前計算済み）
qc/                      検品の出力
```

## ★Codex が無いことをどう扱っているか

`short-video-qc` の合格条件3・4は実施者を Codex と名指ししています。この環境には無いので、
**実施者ではなく満たすべき性質**に一般化し、その分ゲートを増やしました（`.fork/PROJECT-RULES.md §1`）。

- 12レンズ × 3ラウンド = **独立レビュー36回**（隔離／反証／レンズ分割／2/3多数決）
- **G90 参考突合** — 「瓜二つか」を感想でなく数値で判定。★測定なのでモデル多様性の問題を受けない
- **G92 較正ハーネス** — 既知欠陥を注入し直して**検出率を実測**する

★**正直に書いておくこと: モデル多様性は回復していません。**
隔離とレンズ分割で消えるのは「共有文脈バイアス」（自分の理由を知っているから甘くなる）であって、
同一モデルの盲点ではありません。**この2つは別物なので、分けて説明してください。**
残余がどれくらいかは G92 の実測値で報告します。

## 現在の状態（実測値・2026-08-11）

| | |
|---|---|
| G90 参考突合（0801） | **13 PASS / 1 FAIL**（下記） |
| G92 較正ハーネス mechanical | **4/4 検出（PASS）** |
| G92 packet | 15パケット生成済（5欠陥 × 3ラウンド）・回答待ち |
| 在庫 | 188クリップ / 候補リスト562件（0801-0805） |
| 字コンテ | 45スロット（5商材） |

### ★未解決の指摘 1件（伏せずに残してある）

**G90-14 ズーム文法** — `c01` が `100→110` で参考の帯 `112〜117` を下回っている。
理由も独立承認も記録が無いため FAIL のまま。
（`c04` の `115→135` は「もっとピザに寄って。」の指示によるもので、理由と承認を添えて WAIVED）

★**FAIL を PASS に見せない。** 免責するなら `reason` と `independent_approval` の両方を残す。
片方だけでは FAIL のままになるようにしてあります。
