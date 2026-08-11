# SETUP — 環境構築と動作確認

macOS 専用（`defaults write` / `ditto` を前提にしている）。所要 15〜30分。

> ★**別マシンで一から始めるなら `HANDOFF.md` を上から順にやってください。**
> このファイルは各手順の詳細版（罠・ExtendScriptの作法・MOGRT・キーフレーム）です。

---

## 0. 先に確認（ここで詰まる人が多い）

```bash
ffmpeg -version | head -1        # 必須
python3 --version                # 3.9+ / 標準ライブラリのみ使用
```

**pip install は不要です。** numpy も Pillow も使いません。

### 0-1. 原本素材の場所を教える（★別マシンで最初にやること）

原本フッテージ（5商材 **188本・34.5GB**）は**このリポジトリに入っていません**。手元の原本と結びます。

```bash
cp .feriest-paths.example .feriest-paths
$EDITOR .feriest-paths          # FERIEST_ROOT を自分の場所に書き換える
```

`FERIEST_ROOT` は、その下に `00_source_drive/` と `02_work/premiere/` がある階層を指します。
環境変数で渡しても同じです（`export FERIEST_ROOT=/path/to/FERIEST`。環境変数が優先）。

```bash
python3 scripts/resolve_paths.py   # 何がどこに解決されたかを一覧
python3 scripts/check_links.py     # ★素材が実際に引けるかを検査（5案件・0801は使用10本まで）
```

`check_links.py` が **OK にならないまま Premiere を開かないでください。**
リンク切れはオフラインクリップとして**無言で**並びます。

★**prproj は相対パスも持っています**（`<RelativePath>` 36件）。
`FERIEST_ROOT/00_source_drive` と `FERIEST_ROOT/02_work/premiere` の位置関係さえ保てば、
Premiere が自動でメディアを再リンクします。

### 0-2. パスはトークンで持っている

キットの JSON と 案件 jsx（`work/jsx_20260809/`）は、マシン依存の絶対パスを直に持ちません。

| トークン | 中身 | 解決元 |
|---|---|---|
| `@@FERIEST_ROOT@@` | 素材SSDの根 | env `FERIEST_ROOT` → `.feriest-paths` → 既定値 |
| `@@KIT_ROOT@@` | このキットの根 | `pr.sh` の位置から自動導出 |
| `@@BRIDGE_DIR@@` | ブリッジの受け渡し場所 | env `PR_BRIDGE_DIR`（既定 `/tmp/premiere-mcp-bridge`）|
| `@@AME_PRESET@@` | 書き出しプリセット | env `AME_PRESET` → `/Applications` から**自動検出** |

`pr.sh` が**投入直前に**実パスへ置換します。未解決のトークンが残っていたら**投入せずに落とします**。

★ExtendScript 側で環境変数を読む案は使えません。Premiere は GUI 起動なのでシェルの
`export` が届かず、かつブリッジの `validateScript` が `process.` をコメント内でも弾きます。

---

## 1. フォント（★これを飛ばすと全部やり直しになる）

Adobe Fonts で次の3書体を**有効化**する。

| 書体 | 使う場所 |
|---|---|
| `mplus-1p-heavy` | 通常テロップ 68.948 / 商品名2行組 |
| `HeiseiMinStd-W9` | 感嘆・言い切り 109・129 |
| `Makinas-4-Square` | ロックアップ（左下の常時表示）35 |

★**未インストールの書体は Premiere が警告なしに別書体へ差し替えます。** 気づかないまま
別物が出来上がるので、着手前に Premiere の文字パネルで実際に3種が出ることを確認してください。

---

## 2. Premiere CEP Bridge

Premiere を**スクリプトから操作するための拡張**。framework には入っていないので、このキットに同梱してあります。

### 2-1. 未署名拡張を許可する

```bash
defaults write com.adobe.CSXS.12 PlayerDebugMode 1
defaults write com.adobe.CSXS.11 PlayerDebugMode 1
defaults write com.adobe.CSXS.10 PlayerDebugMode 1
```

（Premiere のバージョンで CSXS の番号が変わるため、まとめて入れておくのが確実です）

### 2-2. 拡張を置く

```bash
mkdir -p ~/Library/Application\ Support/Adobe/CEP/extensions
ditto skill/donki-feriest/assets/MCPBridgeCEP \
      ~/Library/Application\ Support/Adobe/CEP/extensions/MCPBridgeCEP
```

★`cp -r` ではなく `ditto` を使ってください（日本語ファイル名の正規化のため）。

### 2-3. Premiere を再起動して開始する

1. Premiere Pro を**完全に終了 → 起動**
2. `ウィンドウ > 拡張機能 > MCP Bridge (CEP)` を開く
3. Temp Directory を確認（既定 `/tmp/premiere-mcp-bridge`）
4. **Save Configuration** → **Start Bridge**

★**Start Bridge は毎セッション手動です。** 押し忘れると `pr.sh` が無応答のままタイムアウトします。
★**外部からブリッジを再開する手段はありません。** 止まったら人が押すしかないので、
長い処理の前には生存確認を入れてください。

### 2-4. 疎通確認

```bash
cat > /tmp/ping.jsx <<'JSX'
var f = new File("/tmp/premiere-mcp-bridge/ping.txt");
f.open("w"); f.write("projects=" + app.projects.numProjects); f.close();
return "ok";
JSX
skill/donki-feriest/scripts/pr.sh /tmp/ping.jsx
cat /tmp/premiere-mcp-bridge/ping.txt
```

`projects=N` が出れば疎通しています。

---

## 3. ★ExtendScript の作法（先に読む。全部実際に踏んだ）

| | |
|---|---|
| **ES3 です** | `forEach` / `map` / アロー関数 / `JSON` が**無い**。素のループで書く |
| **末尾は `return <式>;`** | `pr.sh` はこの戻り値を拾う |
| **長い結果はファイルへ** | `evalScript` の戻り値は長いと切れる。`<bridge dir>/*.txt` に書いて Bash で読む |
| **`app.project` を信じない** | ★手前のプロジェクトを返す。**documentID で必ず照合する** |
| **項目探索は `getMediaPath()`** | 名前で探すと同名の別素材を掴む |
| **★参考prprojを開いたまま実行しない** | documentID `6822d0d1-…a01` を掴んだら**即中断する**ガードを毎回入れる |

```javascript
// ★毎回冒頭に置くガード
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";   // 対象
var REF="6822d0d1-041a-46a0-a5ff-735087200a01";   // 参考（絶対に書き込まない）
var proj=null;
for(var i=0;i<app.projects.numProjects;i++)
  if(app.projects[i].documentID===DOC) proj=app.projects[i];
if(!proj || proj.documentID===REF){ return "★中断: 対象不正"; }
```

### よく使う定数

```javascript
var TPS = 254016000000;      // ticks / 秒
var TPF = 8467200000;        // 30fps の1フレーム
```

### 縦型シーケンスの生成

```javascript
var st = seq.getSettings();
st.videoFrameWidth = 1080; st.videoFrameHeight = 1920;
var t = new Time(); t.ticks = "8467200000"; st.videoFrameRate = t;
st.videoPixelAspectRatio = "1:1";
st.editingMode = "795454d9-d3c2-429d-9474-923ab13b7018";
st.videoFieldType = 0;
seq.setSettings(st);
```

---

## 4. MOGRT（テロップ）

正本は `skill/donki-feriest/assets/telop_3slot_v22.mogrt`（★v20 は使わない）。
**AE は不要です。** 完成済みテンプレを投入してパラメータを書き換えるだけ。

```javascript
// ★本文の書き換えは4つを同時に。fontTextRunLength を文字数に合わせないと Premiere が落ちる
p.setValue(v.replace(/"textEditValue":"[^"]*"/,      '"textEditValue":"'+txt+'"')
            .replace(/"fontTextRunLength":\[[^\]]*\]/,'"fontTextRunLength":['+txt.length+']')
            .replace(/"fontEditValue":\["[^"]*"\]/,   '"fontEditValue":["'+font+'"]')
            .replace(/"fontSizeEditValue":\[[^\]]*\]/,'"fontSizeEditValue":['+size+']'), true);
```

| 罠 | 中身 |
|---|---|
| **色は 0〜100** | 0〜255 ではない。`#EFE919` → `[93.7, 91.4, 9.8]` |
| **`縦位置` は下端** | 中心ではない。`縦位置(%) × 1920 = 文字の下端y` |
| **素材長 150F** | 超えて置けない。★337F を敷くには 0-150 / 150-300 / 300-337 の3枚に割る |
| **★`出現の型=なし` だと強調が発火しない** | 最初から強調された状態で出る。原因特定に一番時間を使った罠 |
| **`強調の遅れ`** | 出現アニメが終わってから数える |
| **`importMGT` で位置が既定に戻る** | 投入後に `位置` を再適用する |

---

## 5. キーフレーム（★読み戻しでは検出できない罠）

```javascript
var OFF = clip.inPoint.seconds;      // ★静止画クリップの inPoint は慣例で 3600.000 秒
pr.addKey(OFF + t);
pr.setValueAtKey(OFF + t, v, true);
// 検算
Math.abs(pr.getKeys()[0].seconds - clip.inPoint.seconds) < 0.01
```

★`0.0` に打つと可視範囲の3600秒手前に置かれ、レンダラーは最後のキーの値を保持し続けます。
**「配置は正しいのにアニメーションだけ効かない」ときは時間軸の基準を疑うのが最短です。**

★`getKeys()` も `getValueAtTime()` も**自分が書いた座標系で返す**ので、
**同じAPIで書いて同じAPIで読む検算は、座標系の誤りを原理的に検出できません。**
必ず書き出した実ファイルの画素で確かめてください（それが `scripts/reference_match.py` です）。

★`縦横比を固定 = true` にすると**プロパティ名が `スケール (高さ)` → `スケール` に変わります。**
検算は両方の名前を受けること。カウンタは分岐の外で数えること（中で数えると 0 のまま嘘の PASS になります）。

```javascript
if (n === "スケール" || n === "スケール (高さ)") { /* ... */ }
```

---

## 6. 動作確認（Premiere 無しでここまで通ります）

```bash
# 0) パス解決と素材リンク（★別マシンでは最初にここ）
python3 scripts/resolve_paths.py
python3 scripts/check_links.py
python3 scripts/check_links.py --verify-media   # ★原本を新規に用意した場合

# 1) 案件プロファイルが生成元と一致するか
python3 .fork/gen_projects.py --check

# 2) 参考突合（完成MP4の画素を実測）
python3 scripts/reference_match.py \
  --build design/build_0801.json \
  --mp4  data/baseline/0801_baseline_v9.mov \
  --out  qc/reference_match_0801.json

# 3) 較正ハーネス（既知欠陥の検出率を実測）
python3 scripts/calibration_harness.py mechanical \
  --build design/build_0801.json \
  --mp4  data/baseline/0801_baseline_v9.mov \
  --out  qc/calibration
```

期待される結果（2026-08-11 時点の実測）:

- `resolve_paths.py` → 4トークンすべてに実在するパスが出る
- `check_links.py` → 5案件すべて `OK`／0801 は「使用素材 10/10 本すべて実在」
- `gen_projects.py --check` → `OK`
- `reference_match.py` → **13 PASS / 1 FAIL**（G90-14 は未解決の実指摘。伏せずに残してある）
- `calibration_harness.py mechanical` → **4/4 PASS**

★2 が **PASS だけ**になったら、それは直ったのではなく**判定が空振りしている**可能性を疑ってください。
実際に G92 が「ΔRGB が構造的にしきい値を下回れない」実装バグを1件検出しています。

---

## 7. 環境の罠（すべて実際に踏んだ）

- **ExFAT の NFD** — 日本語ファイル名の正規化差でパスが一致しない。`unicodedata.normalize` か glob で拾う
- **zip 展開は `ditto -x -k`** — `unzip` だと日本語名が文字化けする
- **`._*` の AppleDouble** — 解析時は `-not -name "._*"` で除外
- **並列は par15 まで** — 超えると ExFAT マウントが落ちる
- **ブートディスクが満杯になりやすい** — 一時ファイルは SSD 側へ。実際に ENOSPC でスクリプトの書き込みが失敗した
- **★`~/.claude` 配下で作業しない** — 消える。必ず SSD 側
- **★`00_source_drive/` は読み取り専用**
