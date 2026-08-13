# 編集操作 全数マトリクス（非アクティブなプロジェクトで何ができるか）

Premiere **26.3.2** / プロジェクト3本を同時に開いた状態で全数実測（2026-08-08）。
SKILL.md §3-4 の要約版に対する完全版。

## 0. 測り方（ここを間違えると結果が全部嘘になる）

**各操作の直前に必ずフォーカスを別プロジェクトへ戻してから測る。**

最初の測定はこれを忘れ、冒頭の `createBin` がフォーカスを奪ったせいで
**以降の判定が全部「アクティブ状態での結果」**になっていた。

フォーカスの移し方: **別プロジェクトに空ビンを作って消す**
（`createBin` は奪うことが分かっているので確実）。

```javascript
function focusAway() {
    try { var b = other.rootItem.createBin("_f"); if (b) b.deleteBin(); } catch (e) {}
    return act();
}
```

測定器は `templates/probe_focus.jsx`。Premiere のバージョンが上がったとき、
あるいは新しい操作を使う前に、**推測せずこれで測る**。

## A. フォーカスを奪わずに通る

ユーザーが別プロジェクトを触っていても邪魔しない。並行運用の主戦場。

| 分類 | 操作 | 実測結果 |
|---|---|---|
| 読み取り | `proj.sequences` / `numTracks` / `clips` 列挙 / `disabled` | 通る |
| 読み取り | `getMediaPath()` での項目探索 | 通る |
| 配置 | `track.overwriteClip(item, time)` | clips 2→3 |
| 配置 | `track.insertClip(item, time)` | clips 3→4 |
| 尺 | `clip.start = Time` | 30.000→30.250 |
| 尺 | `clip.end = Time` | 35.000→34.750 |
| 属性 | `clip.disabled = true/false` | 読み書きとも可 |
| 属性 | `clip.name = "..."` | 書き換わる |
| 削除 | `clip.remove(false, false)` | clips 4→3 |
| マーカー | `markers.createMarker(t)` / `name=` / `comments=` / `deleteMarker` | 通る |
| シーケンス | `setInPoint` / `setOutPoint` | 1.00-3.00 |
| シーケンス | `seq.name =` | 通る |
| シーケンス | `getSettings()` | 1280x720 |
| シーケンス | `exportAsFinalCutProXML(path)` | true |
| シーケンス | `proj.createNewSequence(name, "")`（**空**） | **★ダイアログが開いて止まる**（下記・2026-08-13 訂正） |
| シーケンス | `proj.createNewSequence(name, "vops")`（**空でない文字列**） | 通る・**奪わない**・ダイアログ無し |
| トラック | `track.setMute(1/0)` / `isMuted()` | 通る |
| 素材 | `item.setScaleToFrameSize()` | 通る |
| 素材 | `item.setInPoint` / `setOutPoint` / `getInPoint` / `getOutPoint` | 1.00-3.00 ／ **★2引数必須**（下記） |
| 配置 | **`overwriteClip` は素材の in/out を尊重する**（リンク音声も同区間で付く） | 実証済み（下記） |
| 素材 | `item.getMarkers()` | numMarkers=0 |
| 素材 | `item.getProjectMetadata()` | len=9518 |
| **キーフレーム** | `clip.components` 列挙 | 2個: 不透明度,モーション |
| **キーフレーム** | `component.properties` 列挙 | 位置,スケール,スケール(幅),縦横比を固定,回転,アンカーポイント,アンチフリッカー,切り抜き(左/上/右/下端) |
| **キーフレーム** | `getValue()` / `setValue(v, true)` | 100 → 80 |
| **キーフレーム** | `setTimeVarying(true/false)` / `isTimeVarying()` | 通る |
| **キーフレーム** | `addKey(t)` / `setValueAtKey(t, v, true)` | keys=2 / first=inPoint と一致 |
| **キーフレーム** | `getKeys()` / `getValueAtKey(k)` | v0=50 v1=100 |
| ネスト | `seq.projectItem` を別シーケンスに `overwriteClip` | clips 1→2。**プロジェクトを跨いでも置けた** |
| 選択 | `clip.setSelected(true, true)` / `seq.getSelection()` | n=1 |
| ビン | `bin.moveBin(dst)` | 移動する |
| ビン | `bin.deleteBin()` | children 18→17 |
| オーディオ | `audioTracks` 読み / `setMute` / `overwriteClip` | NA=4 / 0→1 |
| 保存 | `proj.save()` | true |
| 書き出し | `app.encoder.encodeSequence(seq, ...)` | jobID を返す |

**固有エフェクト（モーション・不透明度）のキーフレームが全部ここに入る**のが要点。
テロップのアニメーション・位置・スケールの作業は**非アクティブのまま完結する**。

## B. 通るがフォーカスを奪う

セットアップ段でまとめて済ませる。

| 操作 | 実測結果 |
|---|---|
| `proj.importFiles([...])` | true。対象がアクティブになる |
| `rootItem.createBin(name)` | 作られる |
| `item.createSubClip(...)` | 作られる |
| `proj.createNewSequenceFromClips(name, [item], bin)` | 作られる |
| `seq.createSubsequence(false)` | `<元の名前>_Sub_01` が作られる |
| `seq.clone()` | 作られる（`名前 のコピー`。戻り値の `.name` は undefined） |
| `proj.deleteSequence(seq)` | sequences 9→8 |

**「新しく作る」系が奪う**と覚えると外さない（ビン・サブクリップ・サブシーケンス・複製）。
例外: **`createNewSequence`（空のシーケンス）は奪わない**。
ビンも**作るのは奪うが、動かす・消すは奪わない**。

## C. 対象をアクティブにしないとできない（QE依存）

### QE はアクティブなプロジェクトしか見えない

対象=**プロジェクトA** / アクティブ=**プロジェクトB** のときの実測:

- `qe.project.name` → **B**（アクティブ側。対象ではない）
- `qe.project.getSequenceAt(i)` → **アクティブ側のシーケンスしか列挙しない**
- `qe.project.getActiveSequence()` → **`qe.project` と食い違うことがある**
  （実測で `qe.project` は B を指すのに `getActiveSequence()` は **A のシーケンス**を返した）

**★QE の2つを突き合わせずに使うと別プロジェクトを編集する。**
必ず `qe.project.name` と `getActiveSequence().name` の両方を対象と照合してから触る。

### 回避策: `proj.openSequence(sequenceID)`

`true` を返し、**プロジェクトとシーケンスの両方をアクティブにする**。その後 QE が追従する。

```
openSequence=true → active/qe.project/getActiveSequence がすべて **対象A** に揃う
```

### アクティブ化後は QE が一通り通る

| QE操作 | 実測結果 |
|---|---|
| `qe.project.getVideoEffectByName("モザイク")` → `clip.addVideoEffect(ef)` | components 2→3（不透明度,モーション,モザイク） |
| `qe.project.getVideoTransitionByName("クロスディゾルブ")` | 見つかる |
| `clip.addTransition(tr, true)` | 追加できた |
| `sequence.addTracks(1, n, 0,0,0,0)` | Vトラック 4→5 |
| `track.razor("00;00;02;00")` | V0 clips 1→2（分割できた） |
| `clip.removeEffects(...)` | 呼べるが components 3→3 で**変化しなかった**（引数の意味は未確定） |
| `sequence.makeCurrent` | メソッドは存在する（`typeof` = function） |

### `qe.project` のメンバ

**在るメソッド**（`typeof` で確認）:
`undo, redo, getVideoTransitionByName, getAudioTransitionByName, getVideoEffectByName,
getAudioEffectByName, getSequenceAt, getActiveSequence, newSequence, importFiles, save, close`

**無い**: `deleteSequence`, `openSequence`

**プロパティ**（`for in` で列挙・**メソッドは列挙されない**ので存在確認は `typeof` で）:
`currentRendererName, importFailures, isAudioConforming, isAudioPeakGenerating, isIndexing,
name, numActiveProgressItems, numAudioPeakGeneratedFiles, numBins, numConformedFiles,
numIndexedFiles, numItems, numSequenceItems, numSequences, path`

### QE の既知の罠

`getVideoTrackAt(n).numItems` は **Empty（空き）も数える**。
`type === "Clip"` だけ集めてから添字を使う（実例: numItems=8 だが実クリップ4本）。

## D. できないこと

### `app.executeCommand` は存在しない

26.3.2 で `typeof app.executeCommand` が **`undefined`**。
Web上には「メニューコマンドを叩ける」という解説があるが**このバージョンには無い**。
したがって UI のコピー&ペースト・各種メニュー操作は script から叩けない。

### アンドゥでスクリプトの変更は戻せない

`qe.project.undo()` は呼べる（メソッドは在る）が、実測で
**直前にスクリプトで足したクリップは対象・アクティブどちらも戻らなかった**。

```
before: 対象(A)=1 アクティブ(B)=0
変更後: 対象(A)=2 アクティブ(B)=1
undo後: 対象(A)=2 アクティブ(B)=1   → どちらも戻っていない
```

**元に戻せない前提で作業する。** 上書きせず新規版を作る運用が、ここでも効いてくる。

### ネイティブGraphic（テロップ）の本文

- `projectItem` が **null**、`getMGTComponent()` も **null**
- `ソーステキスト.getValue()` は本文ではなく**1文字の不透明値**
  （実測 charCode 580 / 過去記録 600。**値は個体差があり「1文字しか返らない」ことが本質**）
- **ライブのExtendScript/MCPから本文・本文フォントを直接読み書きすることはできない**
- **新規作成も不可**。QEの生成メソッドは `newSequence/newBin/newBlackVideo/newColorMatte/`
  `newTransparentVideo/newBarsAndTone/newSmartBin/newUniversalCountingLeader` のみで、
  **`newTitle`/`newGraphic`/`newText`/`newCaption` は存在しない**（実測）。
  UXP 26.3 にも `addGraphic`/`createTextLayer`/`createCaption` は無い（公式型定義で確認）
- **テキストを作るなら MOGRT 一択**（`references/MOGRT.md`）。
  `sequence.importMGT` と `sequence.createCaptionTrack`(SRT経由) が実在する
- ただし Premiere を閉じた状態で、コピーした `.prproj` 内の Graphic バイナリを
  差し替える方法は Premiere 26 実機で成功している（フォント差し替えのみ・本文は未検証）

## E. プロジェクト間で中身を移す

`app.executeCommand` が無いので UI のコピー&ペーストは叩けない。
代替を測ったが、**結果が案件によって割れた**。以下は実測をそのまま書く。

### ★★★ 先に読む: `.prproj` のコピーを開いてはいけない

`.prproj` をコピーすると **`documentID` まで複製される**。
その状態でコピーを `app.openDocument()` すると、**Premiere が両者を同一視して
シーケンスが合流する**。実測（2026-08-08）:

```
本番プロジェクト  5本 → 10本（元の5本＋コピー側5本、全部ユニークな別ID）
コピーを閉じても 10本のまま戻らない
```

保存していれば原本が壊れていた（原本は無保存だったため無傷）。
**同じ documentID のプロジェクトを2つ開かない。** 作業前に `list_projects.jsx` で重複を検出する。

### 1. `.prproj` を `importFiles` で取り込む — 挙動が一定しない

```javascript
other.save();                                                   // ★先に相手を保存する
proj.importFiles(["/path/other.prproj"], true, proj.rootItem, false);
```

| 実測 | 結果 |
|---|---|
| 小さな自作プロジェクト（2シーケンス）を取り込み | `proj.sequences` が **8→10**。シーケンスとして使えた |
| 実案件のプロジェクト（5シーケンス・素材多数）を取り込み | **素材（PNG/JPG/MP3）は入るが `proj.sequences` は増えない**。`numSequences` は 11 のまま |

後者では、シーケンスは `rootItem` に **`isSequence() === true` の projectItem として存在する**のに
`proj.sequences` に載らなかった。元プロジェクトの `sequenceID` で `openSequence()` しても
**全部 `false`**（＝IDは引き継がれない）。つまり**中身を編集する経路が無い**。

→ **`.prproj` 取り込みは「素材を持ってくる手段」としては確実だが、
「シーケンスを編集可能な状態で持ってくる手段」としては信用できない。**
必要なら `list_projects.jsx` で `numSequences` が増えたかを毎回確かめること。
（差が何に由来するかは未特定。プロジェクトの規模・元が開いているか・保存状態のいずれか）

### 2. ネストで参照する

相手の `sequence.projectItem` を自分のタイムラインに `overwriteClip`。
実測で clips **2→3**。フォーカスは奪わない。

ただし**プロジェクト跨ぎの依存が残る**。相手を閉じた後も成立するかは**未検証**。

## F. ネイティブグラフィック（Premiereのテキストクリップ）

実案件のプロジェクトで実測（読み取りのみ・2026-08-08）。

### 構造 — 「本文だけ触れない箱」

`projectItem` は `null`、`getMGTComponent()` も `null`（＝AE製MOGRTではない）。
しかし中身は**普通のコンポーネント4つ**に分かれている:

| COMP | matchName | パラメータ |
|---|---|---|
| 不透明度 | `AE.ADBE Opacity` | 不透明度 / 描画モード |
| モーション | `AE.ADBE Motion` | 位置 / スケール / スケール(幅) / 縦横比を固定 / 回転 / アンカーポイント / アンチフリッカー / 切り抜き(左上右下) |
| ベクトルモーション | `AE.ADBE Graphic Group` | 位置 / スケール / スケール(幅) / 縦横比を固定 / 回転 / アンカーポイント |
| **テキスト** | **`AE.ADBE Text`** | **ソーステキスト** / トランスフォーム / 位置 / スケール / 水平比率 / 回転 / 不透明度 / アンカーポイント / start / end / 左上右下 / 親の幅・高さ・回転 |

値も読めた（位置 `0.5,0.5` / スケール `100` / 不透明度 `100` /
テキスト側の位置 `0.4966,0.8239` / スケール `112.22`）。

### ソーステキストだけが読めない・書けない

```
ソーステキスト の getValue() → typeof=string / length=1 / charCode=580
先頭が '{' か（MOGRTのようなJSONか）= false
```

**1文字の不透明値**が返るだけ。値は個体差がある（過去の記録では charCode 600 / `ɘ`、
今回は 580 / `Ʉ`）。**「1文字しか返らない」ことが本質で、具体的な文字に意味は無い。**

**これは仕様**。Adobe の Bruce Bullis が **Premiere 26.x のバグ報告に対して2026年4月**にこう回答している:

> "That's correct behavior. The ExtendScript API is designed to work with .mogrts, created within After Effects."

UXP 26.x にも `TextLayer` / `setText()` は**存在しない**（公式型定義 `@adobe/premierepro` で確認）。
将来的に開く見込みは薄い。

### AE製MOGRT なら本文を変えられる（別物）

`getMGTComponent()` が `null` でないものは AE 製 MOGRT で、こちらは書き換えられる。
ただし現行の `getValue()` は**プレーン文字列ではなく JSON** を返す:

```json
{"textEditValue":"Old","fontTextRunLength":[3],"fontEditValue":["Font"],"fontSizeEditValue":[100]}
```

- **`textEditValue` だけ書き換えると壊れる。`fontTextRunLength` も新しい文字数に合わせる**
- 文字列で丸ごと上書きするとフォント等のスタイル情報が消えて空白になる
- Premiere 13〜14 ではプレーン文字列で通ったので、**古い記事のコードはそのままでは動かない**
- UXP では 26.3 から `project.lockedAccess()` の中で action を作り
  `executeTransaction()` で確定する必要がある（25.x 向けサンプルは動かない）

### inPoint はグラフィックでも 3600秒付近

実測: `3628.333` / `3578.933` / `3599.867` / `3596.400`。
**静止画と同じ慣例がネイティブグラフィックにも当てはまる。**
キーフレームは必ず `OFF = clip.inPoint.seconds` 基準で打つこと（§3-3 の事故が再発する）。

### ★API で取れないものも `.prproj` を直接読めば取れる（2026-08-08 実案件で確定）

`scripts/prproj_telop_dump.py` を使う。**Premiere を閉じてから**実行する（読み取り専用）。

| 項目 | ライブAPI | `.prproj` 解析 |
|---|---|---|
| 本文 | ✗ | **○ 確実**（実案件で 303/320 取得） |
| フォント名 | ✗ | **○ 確実**（302/320。`HiraginoSans-W6` 等25種類） |
| フォントサイズ | ✗ | **○ 確実**（float32） |
| 塗り・フチ・シャドウの色 | ✗ | **△ 実験的**（下記） |
| 位置・スケール・不透明度 | ○ | ○ |

**構造**: `.prproj` は gzip 圧縮XML。テキストは `<StartKeyframeValue>` の base64
（FlatBuffers・マジック `44 33 22 11`）。文字列は `u32の長さ + UTF-8平文` で素直に取れる。

**★フォントサイズは整数ではない。** UIが四捨五入して `69` と表示していても内部は **`68.948`**。
整数で grep すると見つからない（実際にこれで一度見失った）。

**検証**（ユーザー提供の正解値と突合）:
本文「正体は…」= UI表示 サイズ69 / 塗りFFFFFF / フチ313131 / シャドウ090000
→ 本文・`HiraginoSans-W6`・`68.948` が一致。同一様式の他5枚でも完全に再現。

**色が「実験的」な理由**（自動確定できない）:

- フチ `313131` は `00 31 31 31`、シャドウ `090000` は `00 09 00 00` として見つかる
- しかし塗り `FFFFFF` は `ff ff ff` の直前が `00` でなく `3c/4e/44/48/5e` と揺れる
- float の `1.0`(`00 00 80 3f`) と `0.5`(`00 00 00 3f`) が色に化ける
- 暗い色（`09 00 00`）は小さな整数フィールドと区別できない
- `ff ff ff` はパディングとしても頻出し、白を過検出する

→ **1枚だけ Premiere で実値を見て突き合わせれば、同一様式の残り全部を機械で確定できる。**
実際にその手順でこの案件を確定させた。

### 実務上の意味

参考動画の `.prproj` が手に入る案件なら、`TELOP-CRAFT.md` の
「全区間を原寸で1枚ずつ見て書体を割り当てる」「色は名前で決めず芯を実測する」という
手作業のうち、**本文・書体・サイズは機械で確定できる**。色だけは従来どおり画素実測が要る。

### まだ測っていないこと

- 位置・スケール・不透明度・キーフレームへの**書き込み**は未検証。
  構造上は普通のコンポーネントなので通るはずだが、**測っていないので「はず」でしかない**。
  測るときは**本番プロジェクトでやらない**（アンドゥが効かない＝戻せない）
- フチ幅・行間・字間は未確定。`37.1` のような別の float が毎回同じ位置に出るが、
  正解値を知らないので断定できない（UIに「10 px・外側」の表示があったので
  フチ幅10pxの可能性はある）

## H. シーケンス作成は第2引数でダイアログの有無が決まる（2026-08-13 実測・★過去の記述を訂正）

**`proj.createNewSequence(name, "")` は「新規シーケンス」ダイアログを開いてそこで止まる。**
この文書は以前「通る・奪わない」と書いていたが、**人が OK を押していたから通っていた**だけだった
（実際にユーザーが毎回押していた。スクリプトが人の操作に依存していた）。

止まっている証拠は**到達ログ**で採れる。1ステップごとにファイルへ追記する probe を流すと、
`createNewSequence` の直前で途切れ、`ExtendScript execution timed out after 60000ms` になる。

| 第2引数 | 結果 |
|---|---|
| `""`（空文字列） | **★ダイアログが開いて停止**（人が押すまで返らない） |
| 実在するプリセットのパス | 戻る・ダイアログ無し |
| **存在しない**プリセットのパス | 戻る・ダイアログ無し |
| `"x"` / `" "`（空白1文字） | **戻る・ダイアログ無し** |

**第2引数は「ダイアログを出すか出さないか」のスイッチでしかなく、中身は見ていない。**
実在チェックすらしていない。

### ★プリセットの内容は反映されない

縦型の `Social Media Portrait 9x16 30 fps` を渡しても、HD プリセットを渡しても、
存在しないパスを渡しても、**すべて 1920x1080 / 23.976fps（ticks=10594584000）**で出来た。
**狙った仕様にするには `setSettings` で上書きするしかない。**

```javascript
proj.createNewSequence(name, "vops");        // ★空文字列にしない（中身は何でもよい）
var st = seq.getSettings();
st.videoFrameWidth = 1080; st.videoFrameHeight = 1920;
var tk = new Time(); tk.ticks = "8467200000"; st.videoFrameRate = tk;   // 30fps
st.videoPixelAspectRatio = "1:1";
st.editingMode = "795454d9-d3c2-429d-9474-923ab13b7018";
st.videoFieldType = 0;
seq.setSettings(st);                          // ここで初めて狙いの仕様になる
// 実測: 1080x1920 / ticks=8467200000 / V=3 A=4
```

**教訓**: 「通った」の記録は、**人が横で押していないか**を疑う。無人で回す前提の運用では、
ダイアログで止まる操作は「動く」ではなく「止まる」。到達ログを仕込めば機械で判別できる。

## G. 素材のイン点/アウト点（トリム投入）— 2026-08-13 全数実測

**運用ルールは SKILL.md 絶対厳守14条 / §3-1、横断原則は `_video-core/PRINCIPLES.md` §16。**
ここには「測った事実」だけを置く。

### `setInPoint` / `setOutPoint` は2引数

```javascript
item.setInPoint(T(20.0));      // ✕ Error: Not Enough Parameters
item.setInPoint(20.0);         // ✕ 同上（数値でもダメ。引数の“数”の問題）
item.setInPoint(String(ticks));// ✕ 同上
item.setInPoint(T(20.0), 4);   // ○ 通る（戻り値は null）
```

**第2引数 `mediaType` は省略できない。** 省略時のエラーは `Not Enough Parameters` で、
「Time の作り方が悪い」と読み違えやすい（実際に3通り試して全部同じエラーを踏んだ）。

### mediaType は 0/1/2/4 が同じ値を共有する（3 は無効）

`mediaType` ごとに別々の値（in=40+mt / out=50+mt）を書いてから全部読み戻した結果:

| 読み | `getInPoint(0)` | `(1)` | `(2)` | `(3)` | `(4)` | 引数なし |
|---|---|---|---|---|---|---|
| 値 | 44.0 | 44.0 | 44.0 | **0.0** | 44.0 | 44.0 |

**A/V一体の素材では in/out は1組しか無い。** どの mediaType に書いても同じ場所に入り、
最後に書いた値が残る。**3 だけは無効**で 0 を返す。実務では **4 に統一**すればよい。

★ただし**書いた直後の読み戻しが1手ぶん遅れて見えることがある**（連続で別の mediaType へ
書きながら読むと前の値が返った）。**読み戻しで検算しない**という結論は変わらない。

### `overwriteClip` は素材の in/out を尊重する

3カット（合成素材）＋3カット（実写4K）で実証。**設計どおりのフレーム数で乗り、
リンク音声も同区間で自動的に付く**（A1へ別途置く必要がない）。

| | 設計 src | 設計 tl | 実測 tl | 実測F |
|---|---|---|---|---|
| c01 | 20.0–25.0 | 0.0 | 0.0000–5.0000 | 150F |
| c02 | 40.0–43.0 | 5.0 | 5.0000–8.0000 | 90F |
| c03 | 5.0–9.0 | 8.0 | 8.0000–12.0000 | 120F |

★**フレーム格子に乗せれば1フレーム過剰配置は起きなかった**（6カットとも厳密一致）。
`place_clip.jsx` が書いている「overwriteClip は1F長く置くことがある」は、
**格子に乗っていない秒を渡したときの症状**と考えてよい。

### 置いた後に `clip.end` で伸ばすとハンドルから実フレームが出る

`src 5.0–9.0` を `tl 8–12` に置き、`clip.end = 14.0` にして書き出し、**画素で判定**した:

| tl | 期待（ハンドル説） | 実測（焼き込みTC） |
|---|---|---|
| 12.50s | src 9.50 | `00:00:09:15` ＝ 9.5s ✓ |
| 13.90s | src 10.90 | `00:00:10:27` ＝ 10.9s ✓ |

実写素材でも SSIM で同じ結論（ハンドル説 0.951 / フリーズ説 0.465 / 別素材 0.287、
±5F スキャンで **0Fずれに単峰のピーク**）。**フリーズではなく本当に新しい映像が出る。**

### ★素材尺を超えた分は「黒＋無音」になる（クランプもエラーも無い）

60.0秒の素材に `in=55.0 / out=65.0` を打った結果:

| | 実測 |
|---|---|
| `setOutPoint(65.0, 4)` | 成功。`getOutPoint()` も `65.000` を返す |
| 出来たクリップ | tl 0.0000–10.0000（**300F**）。クランプされない |
| 配置の機械検算 | **PASS**（clips数も `end−start` も設計どおり） |
| 書き出した実ファイル | `blackdetect` が **black_start:5.0 / duration:4.967** ＝素材が尽きた瞬間から末尾まで真っ黒 |
| 同区間の音声 | **-47.8 dB**（前半は -24.1 dB） |

**ハンドルの「上限」は素材の実尺**であり、それを超えた要求は**静かに黒で埋められる**。
生成の時点で ffprobe と突き合わせて落とすこと（`place_premiere.py` の `guard_range()`）。

## F. 未検証のまま残っているもの

- `removeEffects` の引数の意味（呼べるが components が変わらなかった）
- ネスト参照が、参照先プロジェクトを閉じた後も成立するか
- マルチカメラ、Productions、Team Projects まわり
- 新しい操作を使う前は `templates/probe_focus.jsx` で**測ってから**使う
