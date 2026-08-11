# MOGRT — スクリプトから「テキストを作る」唯一の道

ネイティブグラフィック（Premiereのテキストツールで作るもの）は
**スクリプトから新規作成できず、本文もフォントもサイズも色も読めない**（`EDITING-MATRIX.md` §F）。
**テキストをプログラムで生成・制御したいなら MOGRT しかない。**

以下はすべて Premiere **26.3.2** の実機実測（2026-08-08）。

## 1. 挿入は公式サポート

```javascript
var clip = sequence.importMGT(path, ticks, videoTrackOffset, audioTrackOffset);
// 戻り値は TrackItem。実測で 40.00-48.00 に挿入できた
```

- `sequence.importMGT` / `sequence.importMGTFromLibrary` はどちらも実在（`typeof`=function）
- UXP なら `SequenceEditor.insertMogrtFromPath()` / `insertMogrtFromLibrary()`（25.6以降）
- 挿入したクリップの `inPoint` も **3600秒付近**。キーフレームは `OFF = clip.inPoint.seconds` 基準
- ★★★**素材長は 150F（5.000秒）固定**（2026-08-09 実測）。`clip.end` で 150F を超えて
  伸ばすと**150F 以降は何も描画されない**。読み戻しではクリップが伸びて見えるため検出できず、
  **書き出した画素で初めて分かる**。長い区間は複数枚を隙間なく敷き詰める
  （実例: 337F ＝ 0-150 / 150-300 / 300-337 の3枚）

## 2. ★AE製でないと使えない

**`getMGTComponent()` が `null` を返すものは Premiere製で、挿入した瞬間に
ネイティブグラフィック化する**（＝本文もフォントも触れなくなる）。

| テンプレート | `getMGTComponent()` |
|---|---|
| `[AE] Sports Package/*` | **あり**（9〜25パラメータ公開） |
| `Basic Title.mogrt` | **null** |
| `Angled Lower Third` / `Bold Lower Third Left` / `Modern Live Overlay` | **null** |

**Adobe同梱のものは大半が Premiere製。** 名前や見た目では判別できない。
**使う前に必ず `getMGTComponent()` が null でないことを確認する。**

★**自分で作れる。** AE は AppleScript で直接叩けるので（ブリッジ不要）、
必要な MOGRT はスクリプトで生成するのが早い。作り方は **`AE-MOGRT-BUILD.md`**。
「1つのテンプレートから書体・サイズ・色・グロー・フチを変える」設計もそちらに書いた。

## 3. テキストは JSON で入っている

公開パラメータのうち、`getValue()` が `{` で始まる文字列を返すものがテキスト。

```json
{"capPropFontEdit":true,"capPropFontFauxStyleEdit":true,"capPropFontSizeEdit":true,
 "capPropTextRunCount":1,
 "fontEditValue":["SourceHanSansJP-Bold"],
 "fontFSAllCapsValue":[false],"fontFSBoldValue":[false],
 "fontFSItalicValue":[false],"fontFSSmallCapsValue":[false],
 "fontSizeEditValue":[40],"fontTextRunLength":[4],
 "textEditValue":"Live"}
```

**★JSONの解析に `eval(` を使うとブリッジに弾かれる**（`validateScript` の禁止語）。
正規表現で読み書きする。

```javascript
function gS(j,k){ var m=j.match(new RegExp('"'+k+'"\\s*:\\s*"((?:[^"\\\\]|\\\\.)*)"')); return m?m[1]:null; }
function sA(j,k,v){ return j.replace(new RegExp('("'+k+'"\\s*:\\s*)\\[[^\\]]*\\]'),'$1['+v+']'); }
```

## 4. 何が変えられるか（実測）

| 項目 | 結果 |
|---|---|
| **本文** | `Live` → `テスト本文ABC`（`fontTextRunLength` も更新すること） |
| **フォント** | `SourceHanSansJP-Bold` → `HiraginoSans-W6` |
| **サイズ** | `40` → `123` |
| **改行** | **`\n` が効く**。`\r` はリテラル文字列として入るだけ |
| **色** | **独立パラメータ**として公開されている（メインカラー/ハイライトカラー/タイトルカラー等）。JSON内ではない |
| 位置・スケール・不透明度・キーフレーム | 普通のクリップと同じ（フォーカスも奪わない） |
| エフェクト追加 | 可（ただし**クリップ全体**にかかる・アクティブ化が必要） |

### ★フォント/サイズは AE側で有効化されていないと変えられない

AEの Source Text「Edit Properties」で以下を個別にONにする必要がある:
**Enable Custom Font Selection** / **Enable Font Size Adjustment** / **Enable Faux Styles**

JSONの `capPropFontEdit` / `capPropFontSizeEdit` がその状態を表す。
**`false` を `true` に書き換えても機能は生えない**（公開されていないものは後から作れない）。

**★キーの有無で判断しないこと。** Adobe同梱78個を調べた実測:

```
capPropFontEdit のキーがある : 74個
値が true                    : 14個   ← フォント編集が実際に可能なのはこれだけ
サイズ編集が true            : 11個
```

## 5. 部分強調（複数ラン）

**per-run の配列は7つ**。同じ長さに揃えれば、1つのテキスト内で
書体・サイズ・太字を出し分けられる。

```
fontEditValue / fontFSAllCapsValue / fontFSBoldValue / fontFSItalicValue /
fontFSSmallCapsValue / fontSizeEditValue / fontTextRunLength
```

```javascript
// 「これは強調です」= これは(3) + 強調です(4)
capPropTextRunCount   = 2
fontTextRunLength     = [3, 4]
fontEditValue         = ["HiraginoSans-W6", "HiraginoSans-W7"]
fontSizeEditValue     = [40, 90]
fontFSAllCapsValue    = [false, false]   // ★これらも必ず2要素に
fontFSBoldValue       = [false, false]
fontFSItalicValue     = [false, false]
fontFSSmallCapsValue  = [false, false]
```

### ★★★ 配列長を揃えないと Premiere が落ちる

`fontFSBoldValue` だけ2要素にして他3つを1要素のまま残したら、
**setValue は `true` を返し読み戻しも通ったのに、UIでそのクリップを開いた瞬間に
Premiere がクラッシュした**（2026-08-08 実際に落とした）。

**これは検証原則そのもの**（`SKILL.md` §4）:
**①戻り値 ②読み戻し が両方通っても、実際には壊れていることがある。**

### ★欠けるのは「行の総幅」が原因（ラン機能は無罪）

強調で1つ目のランが消える現象を追ったところ、**ラン機能ではなく
テンプレのテキストボックス幅の溢れ**だった。溢れた分だけ**行頭から欠ける**。

| 構成（文字数@サイズ） | 概算幅 | 結果 |
|---|---|---|
| 2@40 + 2@90 | 260 | ✅ 出る |
| 6@40 + 1@90 | 330 | ✅ 出る |
| 3@40 + 4@60 | 360 | ✅ 出る |
| 3@40 + 4@75 | 420 | ⚠️ **1文字だけ欠ける** |
| 3@20 + 4@90 | 420 | ❌ 消える |
| 3@40 + 4@90 | 480 | ❌ 消える |
| 7@90（**書式差なし**） | 630 | ❌ 消える |

**書式差の有無と無関係**（差なしの630でも欠けた）。**幅だけで決まる。**
1文字だけ欠ける事例があることが、ラン機能が正常である決定的な証拠。

→ **自前のAEテンプレでテキストボックスを画面幅いっぱいに取れば起きない。**

### ★ラン単位の色はできない

Adobe同梱78個の `.mogrt` を横断で調べたが、**per-run配列に色フィールドは存在しない**。
テンプレのカラーパラメータは**テキスト全体**にかかる。

**エフェクトも同じ**。クリップ全体にかかるので「単語だけ光らせる」はできない。

## 6. 単語単位で色・グローをやるなら AEのレンジセレクター

ラン方式では色が出せず、エフェクトはクリップ全体にしかかからない。
**単語だけ色を変える／単語だけ光らせる**には、AE側の
**テキストアニメーター + Range Selector** を使い、範囲をスライダーで公開する。

Essential Graphics に公開する設計:

```
本文テキスト / 書体 / サイズ         （capPropFontEdit・FontSizeEdit を true に）
塗り色 / フチ色 / フチ幅 / シャドウ色
★強調開始文字番号（スライダー）
★強調文字数（スライダー）
★強調色（カラー）
★強調サイズ倍率（スライダー）
★強調グロー強度（スライダー）
出現アニメ種別（ドロップダウン）
```

**利点**:
1. 未文書のJSONに触らない＝**クラッシュしない**
2. **色とグローが単語単位でできる**（他に方法が無い）
3. スクリプト側は数値・色パラメータを set するだけ

**出現アニメはドロップダウンで型を切り替える。** アニメの種類ごとにテンプレを
分けると枚数が爆発する。「なし」を必ず入れること（参考が静止なら動きを足さない）。

**テキストボックスは画面幅いっぱいに取る**（§5の欠けの原因）。

## 6-1. ★★★ フォントは Premiere から自由に差し替えられる（2026-08-09 解明）

`capPropFontEdit` が `false` だとフォントを触れない、という話（§4）には**続きがある**。
**このフラグは `.mogrt` の中の `definition.json` を書き換えるだけで立つ。**

```bash
python3 scripts/mogrt_enable_font_edit.py 入力.mogrt 出力.mogrt
```

`.mogrt` は zip。中の `definition.json` で `capPropType == 0`（ソーステキスト）の項目の
`capPropFontEdit` / `capPropFontSizeEdit` / `capPropFontFauxStyleEdit` を `true` にして
詰め直すだけ。**AE にこれを有効化する API は無い**（`CompItem` / `Property` を
総当たりしても存在しない）ので、この後処理が唯一の道。

**実機で確認済み（書き出したファイルの画素で判定）**:

| 比較 | SSIM | PSNR |
|---|---|---|
| 同じクリップで**書体だけ**差し替えた2本 | **0.9816** | **21.6 dB** |
| （対照）まったく別内容の2本 | 0.9837 | — |

完全一致なら `SSIM=1.000000` / `PSNR=inf`。そうなっていないので、
**フォントの差し替えはレンダー結果に反映されている。**

### これが意味すること

**書体ごとにレイヤーを焼き込む必要が無い。** 1レイヤーで、
**インストールされている書体なら何でも**指定できる。ドロップダウンも要らない。

```javascript
var v = textProp.getValue();                                  // JSON文字列
var patched = v.replace(/("fontEditValue":\[)"[^"]*"(\])/, '$1"' + PS名 + '"$2');
textProp.setValue(patched, true);
```

★入れるのは **PostScript名**（AEの `app.fonts.allFonts` で採れる）。
★**未インストールのフォントは黙って代替される。設定後に読み返して一致を確かめる。**
★**per-run 配列は7本あり、長さを揃えないと Premiere が落ちる**（§5）。
本文を変えるときは `fontTextRunLength` も併せて直すこと。

## 6-2. ★色は「読む表現」と「書く表現」が違う（2026-08-09 実測）

MOGRT のカラーパラメータは、**`getValue()` は 64bit、`setValue()` は 32bit** で、
**同じ値が往復しない**。長らく「色だけ再現できない」としていた症状の正体はこれ。

**読むと 64bit の `[A:16][R:16][G:16][B:16]`**（各チャンネルは `値<<8`）:

| 色 | `getValue()` |
|---|---|
| 白 | `0x0100FF00FF00FF00` = `72337973781266176` |
| 赤 | `0x0100FF0000000000` = `72337969503010816` |
| 黒 | `0x0100000000000000` = `72057594037927936` |

**書くと 32bit に丸められる**（渡した数値がそのまま格納され、64bit を渡すと `0xFFFFFFFF` に潰れる）:

| 渡した値 | 結果 |
|---|---|
| `0xFFFF0000`（32bit ARGB） | `4294901760` そのまま格納 |
| 64bit の赤 | **`4294967295`（＝白）に潰れる** |
| `[1,0,0,1]` / `[255,0,0,255]` | **`Error: Illegal Parameter type`** |

### なぜ潰れるのか（2026-08-09 追試で判明）

**`setValue` は `2^32-1` で頭打ちになる。** 64bit のうち**下位32bit（＝G と B）にしか手が届かない。**
実際、`0xFFFF0000` と `0xFF0000FF` は**レンダー結果が完全一致**した（SSIM `1.000000`）。
どちらも 64bit で読むと `G≈255 / B≈0` の**緑**になるためで、辻褄が合う。
`0xFF00FF00` は `G≈255 / B≈255` の**水色**になり、これも一致した。

★つまり**緑と青は作れるが、赤とアルファは作れない**。色指定としては使い物にならない。

### ★★★ 解: 色は「0〜100 の数値スライダー3本」で持たせる

**数値は確実に設定できる**ので、色をカラー型で持つのをやめる。

```javascript
// AE側: R/G/B を 0〜100 のスライダーで持ち、式で色を作る
var RGBFN = 'function rgb(r,g,b){ return [r/100, g/100, b/100, 1]; }\n';
fill.expression = RGBFN + 'var T=thisComp.layer("本文");'
   + 'rgb(T.effect("文字色R")(1),T.effect("文字色G")(1),T.effect("文字色B")(1));';
```

★**スケールは 0〜255 ではなく 0〜100 にすること。**
**EGPのスライダーは Premiere 側で 0〜100 に丸められる**（`255` を渡すと `100`、`-1` は `0` になる。実測）。
「範囲を編集」で広げられるが**UI操作でスクリプトからは設定できない**ので、
**最初から 0〜100 に収まる設計にする**のが唯一確実。小数は使えるので精度は落ちない。

**実測（書き出したファイルの平均RGB・背景 74,74,82）**:

| 指定 | 平均RGB | |
|---|---|---|
| 白 `[100,100,100]` | (83,84,93) | 全チャンネル上昇 ✅ |
| 赤 `[100,0,0]` | (84,68,76) | R上昇・G/B低下 ✅ |
| 青 `[0,0,100]` | (67,68,94) | B上昇・R/G低下 ✅ |
| 金 `[100,84,0]` | (84,82,75) | R最大・G中・B低下 ✅ |

この方式のテンプレが `assets/telop_3slot_v22.mogrt`（雛形は
`templates/ae_build_telop_mogrt_v4.jsx`）。**人がUIで色を選びたいならピッカー版のv20を使う。**

**数値パラメータ（太さ・サイズ等）は問題なく設定できる**（8→20 を実測で確認）。
ただし**すべて 0〜100 に収まるよう設計する**こと。

## 6-3. ★1行を複数クリップに分けて並べる（2026-08-09 実証）

**文字単位でできないこと（グローなど）は、行を分けて別クリップにすれば解決する。**
グローはレイヤーに掛かるエフェクトなので「一部の文字だけ光らせる」はテンプレ内では作れないが、
「これは」「グローです」を**別々のMOGRTクリップとして横に並べれば**、後者だけ光らせられる。
書体・サイズ・出現タイミングもクリップごとに完全に独立する。

### 位置合わせ — AE を「文字幅の計算機」として使う

Premiere 側から文字幅を取る手段は無い。**AE に測らせるのが唯一の道**
（`templates/ae_measure_text.jsx`）。テンプレのコンプで実際に文字列を流し込み、
`sourceRectAtTime` で実寸を採る。

★**単純に幅を足してはいけない。** 実測（見出しゴシック120px）:

| | 幅 |
|---|---|
| 「これは」 | 330.37 |
| 「グローです」 | 543.01 |
| 単純合計 | 873.38 |
| **「これはグローです」（連結）** | **879.83** |

**連結の方が 6.45px 広い。** 単純合計で置くと字間が詰まりすぎる。
**両端合わせ**（左パーツを連結時の左端に、右パーツを右端に合わせる）にすれば、
内側の隙間が自動的に自然な字間になる。

### 座標変換

★**MOGRT のコンプはフレーム中央に「等倍」で置かれる（縮尺されない）。**
コンプ1080幅・フレーム1920幅なら **コンプpx = フレームpx**、水平オフセットは `+420`。
Premiere のモーション位置は**正規化**なので `(フレーム幅/2 + ずらす量) / フレーム幅` を渡す。

```javascript
// モーションは MOGRT クリップにも効く
for (var q=0;q<clip.components.numItems;q++){ var cp=clip.components[q];
  for (var r=0;r<cp.properties.numItems;r++){ var pr=cp.properties[r];
    if (pr.displayName==="位置" && cp.displayName==="モーション") pr.setValue([x,0.5],true); } }
```

### 実証

分割2クリップと、1クリップに全文を入れたものを書き出して比較した。

| 比較 | SSIM |
|---|---|
| **分割2クリップ vs 1クリップ** | **0.999722** |
| （対照）**わざと20pxずらした**版 vs 1クリップ | 0.987369 |

20pxの誤差ははっきり検出できる感度がある。その中で 0.9997 なので、
**分割配置は1クリップの行をほぼ完全に再現している。**

### ★本文を差し替えるときは配列長も直す

本文パラメータの実体（実測でこの形）:

```json
{"capPropFontEdit":true,"capPropFontFauxStyleEdit":true,"capPropFontSizeEdit":true,
 "capPropTextRunCount":1,"fontEditValue":["..."],"fontFSAllCapsValue":[false],
 "fontFSBoldValue":[false],"fontFSItalicValue":[false],"fontFSSmallCapsValue":[false],
 "fontSizeEditValue":[90],"fontTextRunLength":[7],"textEditValue":"サンプルの文字"}
```

**`textEditValue` を変えたら `fontTextRunLength` も文字数に合わせる。**
揃えないと `setValue` は成功し読み戻しも通るのに、**UIで開いた瞬間に Premiere が落ちる**（§5）。

## 7. まだ測っていないこと

※ AE側で作る際の知見（露出できる型・フォント焼き込み・アニメーター線幅）は
`AE-MOGRT-BUILD.md` に分離した。

- レンジセレクター方式の実挙動（公開の仕方・スクリプトからの設定）
- 約物の詰め送りが AEのテキストエンジンで追い込めるか
  （PNG方式では `「」（）、。` を約0.55emに詰めている。全角送りだと行が最大12%長い）
- 縦組みでの長音符・括弧の回転（PNG方式では `ROT_CHARS` で90度回転させている）
- 複数ランと Range Selector を併用したときの挙動
