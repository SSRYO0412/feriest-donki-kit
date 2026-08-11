# HANDOFF — 別マシンでこの案件を始めるまでの全手順

> このファイルだけを上から順にやれば、Feriest（ドン・キホーテ／PPIH）8月掲載分の
> 編集・修正・検品を開始できる状態になります。所要 30〜60分（うちフォント有効化とダウンロードが大半）。
> **macOS 専用**（`defaults write` / `ditto` を前提にしています）。

★**この案件で最大の失敗は「案件側の引き継ぎ書を読まずに着手したこと」**でした。
フォントが既に決まっていたのに「無い」と誤断定して別書体に置き換え、全部やり直しになっています。
**「無い」「未着手」と判断する前に、案件側が既に決めていないか必ず確認してください。**

---

## 0. 必要なもの（先に揃える）

★はじめに **[LICENSE.md](LICENSE.md)（利用条件）** を確認してください。本キットはトライアル実演・評価
限定の提供で、他案件への流用・第三者提供・再配布はできません。

| | |
|---|---|
| **このリポジトリへのアクセス権** | ★**private です。** Collaborator 権限かトークンが要ります |
| **原本フッテージ** | 5商材 **188本・34.5GB**（MP4 153＋MOV 35）。★リポジトリには入っていません（GitHub の 100MB/ファイル制限のため）|
| **Premiere Pro 2026** ＋ **Adobe Media Encoder** | CEP拡張の対応は `[14.0, 99.9]` |
| **Adobe Fonts** の3書体 | 手順3で有効化します |
| **ffmpeg / ffprobe** | 検品スクリプトが使います |
| **python3 3.9+** | ★**pip install は不要**。numpy も Pillow も使いません |

**After Effects は不要です。** テロップは完成済み MOGRT テンプレ(v22)を投入するだけです。

### 原本フッテージのフォルダ構成

キットは次の構成を前提にしています。**`FERIEST_ROOT` は `00_source_drive` の親**を指します。

```
<FERIEST_ROOT>/
  00_source_drive/
    20260807_新素材_8月掲載分/
      海老ドーン贅沢ぷりぷり海老マヨピザ/          ← 0801
      ド情熱逆さで使える消臭スプレー&速乾防水スプレー/  ← 0802
      おうちでライブマイク/                      ← 0803
      Reebokファン付きベスト/                    ← 0804
      Mii +フレグランスオイル、ロックミルク/        ← 0805
  02_work/premiere/         ← 作業prproj と 書き出し（無ければ手順5で作る）
  03_render/premiere_202608/ ← 書き出し（同上）
```

商材フォルダ名は在庫表（media_manifest.json）の `product` と**一字一句一致**する必要があります
（半角スペースや読点まで。例 `Mii +フレグランスオイル、ロックミルク`）。
違う場合は手順5の検査が `NG` を出すので、名前を合わせるか
`.feriest-paths` で `FERIEST_ROOT` を調整してください。
★**`00_source_drive/` は読み取り専用**。ここから直接編集しません。

### ★SSD である必要はありません

`FERIEST_ROOT` は**ただのパス**です。既定値が `/Volumes/Extreme SSD/FERIEST` なだけで、
コード上「SSD」を要求している箇所はありません。内蔵ディスクでも外付けでもマウント済みの
ネットワークボリュームでも動きます。満たすべきは**上のフォルダ構成だけ**です。

```bash
export FERIEST_ROOT=~/FERIEST     # 内蔵でも可（.feriest-paths に書いても同じ）
```

内蔵（APFS）に置く場合の差:

| | |
|---|---|
| **並列は par15** の制約 | ★**ExFAT 固有**（par20 でマウントが落ちた）。内蔵では不要 |
| ExFAT の NFD 問題 | 発生条件が変わる。コード側は `unicodedata.normalize` で両対応済み |
| `._*` の AppleDouble 除外 | 外部由来のコピーには残るので**引き続き必要** |
| zip は `ditto -x -k` | `unzip` だと日本語名が化ける。**引き続き必要** |
| **空き容量 34.5GB** | ★HANDBOOK に「ブートディスクが満杯になりやすい・実際に ENOSPC でスクリプトの書き込みが失敗した」という記録あり。余裕を見ること |

---

## 1. クローン

```bash
git clone https://github.com/SSRYO0412/feriest-donki-kit.git
cd feriest-donki-kit
```

約100MB です。`git clone` が認証エラーになる場合は手順0のアクセス権の問題です。

---

## 2. 原本の場所を教える

```bash
cp .feriest-paths.example .feriest-paths
$EDITOR .feriest-paths          # FERIEST_ROOT を自分の原本の場所に書き換える
python3 scripts/resolve_paths.py   # 何がどこに解決されたかを確認
```

キットの JSON と 案件 jsx は、マシン依存の絶対パスを**トークン**で持っています。

| トークン | 中身 | 解決元 |
|---|---|---|
| `@@FERIEST_ROOT@@` | 原本フッテージの根 | env `FERIEST_ROOT` → `.feriest-paths` → 既定値 |
| `@@KIT_ROOT@@` | このキットの根 | `pr.sh` の位置から自動導出 |
| `@@BRIDGE_DIR@@` | ブリッジの受け渡し場所 | env `PR_BRIDGE_DIR`（既定 `/tmp/premiere-mcp-bridge`）|
| `@@AME_PRESET@@` | 書き出しプリセット | env `AME_PRESET` → `/Applications` から**自動検出** |

`pr.sh` が jsx を投げる直前に実パスへ置換します。未解決なら**投入せずに落ちます**。

★MOGRT・Twemoji・参考prproj は**キット同梱物を参照**します（原本側には要りません）。
jsx が `FERIEST_ROOT` を要求するのは **原本素材と書き出し先だけ**です。

---

## 3. フォント3種を有効化（★ここを飛ばすと全部やり直しになる）

Adobe Fonts で次を**有効化**します。

| 書体 | 使う場所 |
|---|---|
| `mplus-1p-heavy` | 通常テロップ 68.948 / 商品名2行組 |
| `HeiseiMinStd-W9` | 感嘆・言い切り 109・129 |
| `Makinas-4-Square`（マキナス 4 Square）| ロックアップ（左下の常時表示）35 |

★**未インストールの書体は Premiere が警告なしに別書体へ差し替えます。**
気づかないまま別物が出来上がるので、手順5の検査を必ず通してください。

---

## 4. Premiere CEP Bridge を導入

Premiere をスクリプトから操作する拡張です。**キットに同梱済み**なので入手は不要です。

```bash
# ① 未署名拡張を許可（バージョンで CSXS の番号が変わるのでまとめて）
defaults write com.adobe.CSXS.12 PlayerDebugMode 1
defaults write com.adobe.CSXS.11 PlayerDebugMode 1
defaults write com.adobe.CSXS.10 PlayerDebugMode 1

# ② 拡張を配置（★cp -r ではなく ditto。日本語ファイル名の正規化のため）
mkdir -p ~/Library/Application\ Support/Adobe/CEP/extensions
ditto skill/donki-feriest/assets/MCPBridgeCEP \
      ~/Library/Application\ Support/Adobe/CEP/extensions/MCPBridgeCEP
```

③ **Premiere Pro を完全終了 → 起動**
④ `ウィンドウ > 拡張機能 > MCP Bridge (CEP)` を開く
⑤ Temp Directory を確認（既定 `/tmp/premiere-mcp-bridge`）→ **Save Configuration** → **Start Bridge**

★**Start Bridge は毎セッション手動です。** 押し忘れると `pr.sh` が無応答のままタイムアウトします。
★**外部からブリッジを再開する手段はありません。** 止まったら人が押すしかないので、
長い処理の前には生存確認を入れてください。

### 疎通確認

```bash
cat > /tmp/ping.jsx <<'JSX'
var f = new File("/tmp/premiere-mcp-bridge/ping.txt");
f.open("w"); f.write("projects=" + app.projects.numProjects); f.close();
return "ok";
JSX
bash skill/donki-feriest/scripts/pr.sh /tmp/ping.jsx
cat /tmp/premiere-mcp-bridge/ping.txt
```

★`pr.sh` の正本は **`skill/donki-feriest/scripts/pr.sh`** です。
`skills/premiere-bridge-ops/scripts/pr.sh`（framework 由来・編集禁止レイヤ）は
トークン解決を持たないので、案件 jsx を投げると `@@FERIEST_ROOT@@` が生のまま Premiere に届きます。

---

## 5. 着手前チェック（★ここが OK になるまで Premiere で作業を始めない）

```bash
python3 scripts/check_links.py                 # 素材・前提ソフト・書き出し先をまとめて検査
python3 scripts/check_links.py --fix-dirs      # 足りない書き出し先ディレクトリを作る
python3 scripts/check_links.py --verify-media  # ★原本を全数照合（新規に用意した場合は必須）
```

見るもの:

- **素材** — 5案件の商材フォルダと、0801 が設計上使う10本の実在
- **前提** — ffmpeg / ffprobe / Premiere / AMEプリセット / CEP拡張 / PlayerDebugMode / **フォント3種**
- **書き出し先** — `02_work/premiere/verify_20260809` と `03_render/premiere_202608`

フォント確認に system_profiler を使うので **10秒ほどかかります**（急ぐときは `--no-fonts`）。

★**リンク切れは Premiere 側で無言に起きます**（オフラインクリップとして黙って並ぶ）。
ここで落としておかないと、組み上げた後に気づくことになります。

### ★原本を今から用意する／ダウンロードした場合は `--verify-media`

同梱の在庫表 **`data/asset_db/media_manifest.json`**（188クリップの名前と実尺）と突合して、
落とし切れているかを機械照合できます。**188本で約3秒**です。

```
== 原本の全数照合（在庫表と突合）==
  OK  0801  海老ドーン贅沢ぷりぷり海老マヨピザ          24/24本 照合
  OK  0802  ド情熱逆さで使える消臭スプレー&速乾防水スプレー   36/36本 照合
   …
```

検出できるもの（欠陥を仕込んで実証済み）:

| 出力 | 意味 |
|---|---|
| `欠け` | DBにあるのに手元に無い＝**ダウンロードの取りこぼし** |
| `DBに無い` | 余分なファイル（別案件の混入・リネームの失敗）|
| `尺ズレ` | 名前は合うが中身が違う＝**取り違え**（DB 21.52秒 / 実測 7.01秒 のように出る）|
| `読めない` | ffprobe が尺を取れない＝**破損・途中で切れている** |

★**Google Drive からの取得は要注意**です。ルート直下に同名フォルダが2つずつ9組あり、
`rclone lsjson -R` は取りこぼします（**268本と出るが実際は315本**）。
`--drive-root-folder-id` をフォルダIDごとに与えて再帰してください（HANDBOOK 1節）。
**落とし切れていないのに落とし切れたように見える**のが一番危ない失敗です。

---

## 6. 0801（構築済み）を開く場合だけ

★**リポジトリ内の位置のまま prproj を開かないでください。**
prproj は相対パス（`<RelativePath>` 36件）でメディアを持っていますが、その基準は
**prproj 自身の位置**です。`work/premiere/` のまま開くと `../../` がキット直下を指し、
**全クリップがオフラインになります。**

```bash
cp work/premiere/FERIEST_0801_ebi_v1.prproj "$FERIEST_ROOT/02_work/premiere/"
```

この位置に置けば `../../00_source_drive/…` が正しく解決され、Premiere が自動で再リンクします。

| | |
|---|---|
| シーケンス | `0801_ebi` / **1080×1920 / 30fps / 337F = 11.233秒** |
| documentID | `3ea1839d-a639-48ba-acae-e0d506adfd39` |
| 却下版 | `work/premiere/FERIEST_0801_ebi_v1__premierev2_6cut_20260809_1743.prproj`（★開かない）|

★**`.prproj` のコピーを開かない**（documentIDが複製されシーケンスが合流します・恒久ルール15）。

---

## 7. 動作確認（Premiere 無しでここまで通ります）

```bash
python3 .fork/gen_projects.py --check
python3 scripts/reference_match.py \
  --build design/build_0801.json --mp4 data/baseline/0801_baseline_v9.mov \
  --out qc/reference_match_0801.json
python3 scripts/calibration_harness.py mechanical \
  --build design/build_0801.json --mp4 data/baseline/0801_baseline_v9.mov \
  --out qc/calibration
```

期待される結果（2026-08-11 時点の実測）:

| | |
|---|---|
| `gen_projects.py --check` | `OK` |
| `reference_match.py` | **13 PASS / 1 FAIL**（G90-14 は未解決の実指摘。伏せずに残してあります）|
| `calibration_harness.py mechanical` | **検出率 4/4 PASS** |

★2が **PASS だけ**になったら、直ったのではなく**判定が空振りしている**可能性を疑ってください。
実際に G92 が「ΔRGB が構造的にしきい値を下回れない」実装バグを1件検出しています。

### ★`mechanical` の 4/4 は G92 の合格ではありません

較正ハーネスの既知欠陥は **9件**あり、`mechanical` が自動で測れるのは **4件だけ**です。

| | 欠陥 | どこで測るか |
|---|---|---|
| 測れる系5件 | D1 白飛び / D2 テロップ色が埋もれる / D4 最短ショット割れ | `mechanical` |
| | **D3 DBラベルと実画の食い違い**（実画を見ないと分からない）| **packet**（目視レンズ）|
| | **D5 検算スクリプト自身の誤り**（動画ではなくコードの欠陥）| **packet**（コードレビューのレンズ）|
| 判断系4件 | D9 数値だけ合わせた過剰分割 | `mechanical` |
| | D6 同種動作の連打 / D7 離れた画が被る / D8 訴求として弱い画 | **packet** |

合格条件は **測れる系5件=100%・判断系4件=75%以上**。つまり **packet → score まで回して初めて G92 の判定が出ます。**

```bash
# 1) パケットを生成（5欠陥 × 3ラウンド = 15本。既に qc/calibration/packets/ に同梱済み）
python3 scripts/calibration_harness.py packet \
  --build design/build_0801.json --out qc/calibration

# 2) ★各パケットを「隔離した」サブエージェントに1本ずつ渡す
#    作業ログや制作側の理由を渡さない。成果物＋参考＋ルールのみ。
#    「否定せよ／迷ったら却下」を明示する（PROJECT-RULES §1 の independent_review 要件）
#    回答を qc/calibration/answers/<D3_r1>.json のように保存する

# 3) 採点（2/3多数決。割れたら却下側に倒す）
python3 scripts/calibration_harness.py score --out qc/calibration
```

`qc/calibration/answers/` は `.gitignore` 済みです（回答は各マシンで作るもの）。

★**未検出は必ず名指しで報告してください。伏せない**というのが `known_defects.json` の
`_pass_rule.reporting` です。また、これは**同一モデルによるレビューであり、モデル多様性は
回復していません**（隔離とレンズ分割で埋まるのは共有文脈バイアスの方）。この事実は
検出率が基準を満たしても消えません。

---

## 8. ここまで来たら読むもの（順番を飛ばさない）

| 順 | ファイル | 中身 |
|---|---|---|
| 1 | **`.fork/PROJECT-RULES.md`** | 恒久ルール15条・合格条件の上書き宣言・作業の型・やってはいけない |
| 2 | **`HANDBOOK.md`** | 案件の全知見（参考の実測値・効いた修正の履歴・環境の罠）|
| 3 | `skill/donki-feriest/references/` | 仕様の正本7本（下表）|
| 4 | `.fork/REFERENCE-TARGETS.json` | 「瓜二つ」を判定する基準値（機械可読）|
| 5 | `.fork/lenses/lenses.json` | 独立レビュー12レンズ |

| references | 中身 |
|---|---|
| `REFERENCE-SPEC.md` | 参考「0.7人前うどん」の全実測値 |
| `TELOP-SPEC.md` | テロップの3階層の文法 |
| `PREMIERE-RECIPE.md` | Premiere の組み方（コード付き）|
| `TRAPS.md` | 踏んだ罠（API 18件・測定器の盲点7件・素材6件・選定5件・運用6件）|
| `ASSETS.md` | ★**素材の引き方**（在庫表・候補リスト・実測での裏取り）|
| `PROJECT-RULES.md` / `MINIMAL-SET.md` | 案件ルール・最小セット |

---

## 9. 素材の探し方（★ラベルを信用しない・実測主義）

★このキットには**窓単位の素材解析データは同梱されていません**。入っているのは
①在庫表 `data/asset_db/media_manifest.json`（検収用）と
②**選抜済みの候補リスト** `data/design/s34_FINAL3.json`（5商材×6スロット・候補562件）です。
引き方と実素材での裏取り手順は `ASSETS.md` に実例があります。

```bash
python3 - <<'EOF'
import json
d = json.load(open("data/design/s34_FINAL3.json"))
for s in d["products"]["海老ドーン贅沢ぷりぷり海老マヨピザ"]["slots"]:
    print(s["slot"], "|", s["telop"], "| 候補", len(s["candidates"]))
EOF
```

★**修正指示への対応は `skill/donki-feriest/references/REVISION-PLAYBOOK.md` から入る**こと。
指示の類型（白飛び/カメラワーク/被写体中心/人物/寄り引き/意味/テンポ）ごとに、
事前計算済みの表 `data/revision_aids/`（軸別代替候補・1秒粒度クリッププロファイル）を引く手順が固定してあります。

★守ること（`ASSETS.md` と `PROJECT-RULES.md` から）:

- **選定の主キーは「何をしているか」**（動作・機能）。写っている物の列挙で照合しない（偽陽性を量産する）
- **候補のラベルは実画と食い違うことがある**。採用前に必ず実画を目視で裏を取る
- **候補リストの数値は目安。最終判断は実素材を ffprobe/ffmpeg で測る**
- **向き** — 原本は全て 3840×2160 で返るが、229本は rotation メタで実体は縦。
  真に横なのは5本だけ（a0947 / a0950 / a0951 / a0803 / **a0933**）
- **連番が商品をまたぐ**。★**フォルダ名の商品帰属を信用しない**

---

## 10. 作業の型（`PROJECT-RULES.md` 5節）

```
[0] 修正台帳／字コンテから、やることを引く
[1] ★実測してから動く（推測で直さない）
[2] カットを選ぶなら 3〜5候補をスコアリング
     内容一致45 / 寄り引き15 / 新鮮さ15 / 尺10 / 画質5 / NG−100
     「置かない・変えない」も候補に入れる。全候補を実画で目視
[3] ★独立レビュー 12レンズ × 3ラウンド = 36回（隔離・反証・多数決）＋ 盲検ランキング(G91)
[4] Premiere で実装 → 全ショットの機械検算
[5] ★完成画素で検証（読み戻しだけで「できた」と言わない）＋ 参考突合(G90) ＋ 較正ハーネス(G92)
[6] 記録（修正台帳の行 ＋ 修正記録DB に1行）
```

### ★絶対に守る（恒久ルールの抜粋。全文は `PROJECT-RULES.md` 2節）

- **コンテの文言は一字も変えない**（赤入れ後が確定内容）
- **追撮はしない**。不足はテロップ/ナレで補う
- **今回の素材は全て顔出しOK**。顔が出ていてもNG分類しない・顔クロップ不要
- **py・prproj・jsx は上書き禁止**。必ず新版・**却下版も消さない**
- **完成MP4を直接編集しない**。修正は必ず生成側から
- **参考 `0.7人前うどん.prproj` は読むだけ。絶対に編集しない**
- **`core/` `skills/` は編集禁止レイヤ**。案件固有の判断は `.fork/` と `skill/donki-feriest/` に書く
- **並列は par15**（par20 だと ExFAT マウントが落ちる・実際に発生）
- **字コンテの無い2商材**（トロリスタ・ホイールグローブ）は**コンテ到着まで着手しない**

### 毎回やる機械検算（全部0件が正常）

```
V1の隙間/重なり ・ 同一素材同一区間の重複 ・ 全トラックの終端ずれ
MOGRTの fontTextRunLength 不一致 ・ ズームキーの inPoint 頭ズレ
設計カット点で画が変わらない ・ 設計外の画変わり
白飛び2%超のショット ・ 黒フレーム ・ 0.40秒未満のショット
```

---

## 10-B. 0802〜0805 をゼロから組む（★制作の入口）

**設計の材料はキットに揃っています。** 0801 だけが構築済みで、残り4本がこの流れになります。

### ① 何をやるかを引く

| ファイル | 中身 |
|---|---|
| `data/conte/conte.json` | ★**クライアント赤入れ後の字コンテ**。0801=9 / 0802=8 / 0803=10 / 0804=9 / 0805=9 スロット。各スロットに `pic`（画の指示）/ `narr` / `telop` / `need`（must+want）|
| `data/design/s34_FINAL3.json` | ★**候補まで出してある**。5商材 × 6スロット、候補 **562件**（`t0/t1/dur/shot/comp/quality/blur/persons/matched` 付き）|
| `projects/08xx.json` | 目標値（ショット数の帯・尺・窓数）|
| `.fork/REFERENCE-TARGETS.json` | 「瓜二つ」の判定基準 |

★**`conte.json` の文言は一字も変えません**（恒久ルール2）。

### ② 採否を決める（★ここが人の仕事）

`s34_FINAL3.json` は自分でこう宣言しています。

> `"note": "★候補列挙とスコアまで。採否は人の原寸目視(S3.5/S8)で決める"`

候補IDの `#` 以降は不透明トークンです。実時刻は各行の `t0/t1` が正で、`__NO_INSERT__` は **「置かない」という選択肢**で、
★これも候補に入れるのが恒久ルールです。

```bash
# スロットの候補を見る
python3 - <<'PY'
import json
d = json.load(open("data/design/s34_FINAL3.json"))
p = d["products"]["おうちでライブマイク"]
for s in p["slots"]:
    print(s["slot"], s["function"], s["emotion"], "|", s["telop"], "|",
          "%.2f秒" % s["dur_est"], "候補", len(s["candidates"]))
PY
```

スコアの重みは `内容一致45 / 寄り引き15 / 新鮮さ15 / 尺10 / 画質5 / NG−100`。
★**全候補を実画で目視**します（`person_count` や `inventory` は当てになりません）。

### ③ `design/build_08xx.json` を作る

`design/build_0801.json` が唯一の完成例です。**同じ形で書きます。**

| キー | 中身 |
|---|---|
| `video_id` / `product` / `fps` / `frames` / `width` / `height` | 基本 |
| `shots[]` | `name` / `start_f` / `end_f` / `src` / `tin` / `zoom` / `punch` |
| `telops[]` | 本文・様式（3階層のどれか）・区間 |
| `_provenance` | ★**どの数値がどこから来たか**。0801 は「ショット表=設計記録の jsx」「色=完成MP4の画素実測」と書いてあります |

★`_provenance` を省かないでください。**後から「なぜこの値か」を辿れないものは検証できません。**

### ④ Premiere で実装 → 完成画素で測る

`skill/donki-feriest/references/PREMIERE-RECIPE.md` の手順で組み、`work/jsx_20260809/` を
実装例として読みます（0801 は `w02_rebuild` → `w05_repair` → `z08_c04c05` の順で追うと分かりやすい）。
書き出したら**必ず完成ファイルの画素で**測ります。

```bash
python3 scripts/reference_match.py \
  --build design/build_0802.json --mp4 <書き出したMP4> --out qc/reference_match_0802.json
```

★**読み戻しだけで「できた」と言わない**（`getKeys()` は自分が書いた座標系で返すので、
座標系の誤りを原理的に検出できません）。

### ⑤ 独立レビュー36回 → 記録

`.fork/lenses/lenses.json` の12レンズ × 3ラウンド。隔離した文脈で、反証を明示して回します。
終わったら**その場で**台帳に書きます（手順14）。

---

## 11. 過去の作業を読む・再利用する

`work/jsx_20260809/` に、0801 を実際に組んだ ExtendScript **98本**が世代ごとに残っています。

| 接頭 | 本数 | 中身 |
|---|---|---|
| `r` | 10 | 参考うどん prproj の読み取り・分析 |
| `v` | 38 | 初回組み上げ（make_project → import → place_cuts → telop → export の反復）|
| `t` `u` | 19 | MOGRT v22 の probe・素材差し替え・Lumetri修正・ズーム全適用 |
| `w` | 10 | 再構築（rebuild → fx → verify → repair → export）|
| `x` `y` | 13 | テロップ配置・強調の詰め |
| `z` | 8 | 最終修正（c04/c05 差し替え・c01 fit・final export）|

★**`work/jsx_20260809/_rejected/` の5本は実行禁止**です（MOGRT v20 を参照する却下版）。
投げても先頭で中断しますが、v22 系列（`t/u/w/x`）に同じ役割のものがあります。

`design/build_0801.json` の `_provenance` が、設計値の出どころとしてこの jsx を名指ししています
（ショット表 = `w02_rebuild` / `z08_c04c05`、テロップ書式 = `w05_repair` / `u05_telop3` ほか）。

---

## 11-B. Notion 台帳（★記録は義務。省略できません）

修正指示と採用状態は **Notion が正**です。ID はキットに入っているので、接続さえできれば動きます。

### 接続

キットのスクリプトは **`NOTION_TOKEN`（環境変数）→ `--token-file` → `~/.claude.json`** の順で
トークンを探します（`core/revision/scripts/notion_rest.py`）。

```bash
export NOTION_TOKEN=secret_xxxxxxxx
```

★**発注側のトークンをそのまま受け取らないでください。** そのインテグレーションが見える範囲を
すべて操作できてしまいます。**必要なページにゲスト招待してもらい、自分のトークン／コネクタで繋ぐ**のが
正しい形です。スコープが共有ページに限定され、後から個別に失効できます。

### 3つの台帳（★混同しない）

| | 場所 | 何のためか |
|---|---|---|
| **(A) 11DB体制** | `3b78866ade56814a8813cbe7484555fa` | 8月掲載分の映像管理。0801〜0805。トロリスタ・ホイールグローブは**未発番** |
| **(B) 修正台帳** | 「作業記録・修正管理（全案件共通）」配下 | ★**発注側が修正指示を書く場所**。1動画=1ページ |
| **(C) 修正記録DB** | `data_source_id: 41e8866a-de56-829f-850d-0726dd063cdc` | ★**py/jsx を作る・直すたびに1行** |

- **(B) は「修正指示DB」ではありません。** カット台帳をもとに作る**記入用シート**で、
  発注側が書くのは **`修正指示` と `採否` の2列だけ**。残りは作業側が埋めます。
- ★**台帳ページにはテンプレ由来の空のリンクドビューがもう1つあります**（別案件のデータ入り）。
  そちらではなく**カット名が入っている方**を見てください。
- **(C) の必須列**: 記録名 / 対象ファイル_pyパス（フルパス）/ バージョン / 変更内容 /
  変更理由（★**発注側の指摘は原文引用**）/ 採用状態 / 却下理由 / 検証方法（★**実測値を数字で**）/ 関連ファイルパス

### 書くタイミング

| いつ | どこに |
|---|---|
| py・jsx を作った／直した**その都度** | (C) 修正記録DB に1行 |
| **採用 MP4 / 採用 py / 採用 v が変わった瞬間** | (A) 動画台帳を更新。★**過去の採用値と却下理由を消さずに追記** |
| 修正指示に対応し終わったら | (B) を納品済みに |

★**採用が変わったのに台帳が未更新のまま「完了」と報告してはいけません。**
★**上書きしない・却下版も消さない**（恒久ルール9・10）。

### Notion に繋がらない期間

`data/ledger/` が代替の受け皿です（`.fork/project.base.json` の `notion.ledger_offline`）。

| | |
|---|---|
| `data/ledger/revision_records.jsonl` | (C) の代わり。1行1レコードで**追記のみ** |
| `data/ledger/adoption.json` | (A) の代わり。採用版と `history[]` |

★**台帳の更新義務そのものは消えません。** 繋がったら Notion へ転記し、
`data/ledger/` の行は**消さずに残します**。

---

## 12. 詰まったら

| 症状 | 見るところ |
|---|---|
| `pr.sh` が無反応でタイムアウト | Start Bridge を押し忘れ（手順4⑤）。★タイムアウト＝失敗ではないので、作り直す前に読み戻す |
| `Script validation failed` | ブリッジが `require(` `process.` `eval(` `new Function(` を**コメント内でも**弾く |
| 「配置は正しいのにアニメーションだけ効かない」 | キーフレームの時間軸。★静止画クリップの inPoint は慣例で **3600.000秒**。`SETUP.md` 5節 |
| クリップが全部オフライン | 手順6（prproj の置き場所）か手順5（リンク検査）|
| 書体が違うものになっている | 手順3。★Premiere は未インストール書体を**警告なしに差し替える** |
| 日本語パスが一致しない | ExFAT の NFD 問題。`unicodedata.normalize` か glob で拾う |
| zip の日本語名が化ける | `unzip` ではなく `ditto -x -k` |

より詳しい罠は `skill/donki-feriest/references/TRAPS.md`（API 18件ほか）と
`skills/premiere-bridge-ops/references/API-TRAPS.md` にあります。

---

## 13. この案件のスコープ

| video_id | 商材 | 状態 |
|---|---|---|
| **0801** | 海老ドーン 贅沢ぷりぷり海老マヨピザ | **構築済み**（修正の実演用）|
| **0802** | ド情熱 逆さで使える消臭スプレー＆速乾防水スプレー | ゼロから組み上げ |
| **0803** | おうちでライブマイク | ゼロから組み上げ |
| **0804** | Reebok ファン付きベスト | ゼロから組み上げ |
| **0805** | Mii + フレグランスオイル、ロックミルク | ゼロから組み上げ |

★**素材が無い4件は確定済み**（探せば見つかる、と誤認しないこと。全数検索で不在を確定しています）:
0803「3色展開」は**実物が黒とシルバーの2色のみ**・0804「モバイルバッテリーで起動」「1万円以下」・
0805「香水みたいにいい香り」。**ライブマイクの3色は画と文言が食い違う**のでクライアント確認が要ります。

クライアントの赤入れ（原文）は `HANDBOOK.md` 3節にあります。
★全案件横断で「**もう少し遊び心や視聴者がクスッとできる要素**」、
構成は「**1カットごとに異なる訴求を詰め込まず、動画全体で一番伝えたい訴求をカット同士でつなげる**」。
