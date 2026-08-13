# Premiere ExtendScript API 罠一覧（実機で踏んだものだけ）

推測は書かない。**実機で確認した挙動のみ**を載せる。
新しく踏んだらここに追記する（バージョンと日付を添える）。

## A. 存在しないメソッド（呼ぶと `ReferenceError`）

| 呼んだもの | 結果 | 正解 |
|---|---|---|
| `clip.isDisabled()` | `is not a function` | `clip.disabled`（プロパティ） |
| QE `trackItem.isEnabled()` | `is not a function` | DOM の `clip.disabled` |
| QE `trackItem.setEnabled(false)` | `is not a function` | **`clip.disabled = true`（プロパティへの代入で書ける）**。2026-08-08 実測で読み書き両方できることを確認 |
| `component.remove()` | 存在しない | QE の `TrackItem.removeEffects()` |

確認: Premiere Pro 26 / 2026-08-07。

`track.isMuted()` は**動く**が、これは**トラック単位のミュート**でクリップの無効化とは別物。
トラックが `muted=false` でも、その上のクリップが `disabled=true` ということは普通に起きる。
**片方を見て他方を判断してはいけない。**

## B. 戻り値が期待と違う

| API | 実際の挙動 |
|---|---|
| `mcp__premiere-pro__execute_extendscript` | **常に `"undefined"`**。戻り値を返さない |
| `evalScript` の戻り値 | 長いと切れる。全量はファイルへ書き出す |
| `ソーステキスト.getValue()`（ネイティブGraphic） | 本文ではなく1文字の不透明値（`ɘ` / charCode 600） |
| ネイティブGraphic の `projectItem` | `null`。`getMGTComponent()` も `null` |
| `getKeys()` / `getValueAtTime()` | **自分が書いた座標系で返す**ので座標系の誤りを検出できない |

## C. 挙動が直感と違う

| API | 罠 |
|---|---|
| `app.project` | **手前のプロジェクト**を返す。作業中に入れ替わる。3点照合で中断させる |
| `insertClip` | 挿入編集で**後続を押し出す**。時刻指定で置くなら `overwriteClip` |
| `overwriteClip` | **1フレーム長く置くことがある**。`clip.end` で詰める（**格子に乗せれば起きない**・C-11） |
| `item.setInPoint` / `setOutPoint` | **2引数**（`mediaType` 必須）。省くと `Not Enough Parameters`。mediaType は 0/1/2/4 が同値を共有し **3 は無効**（C-11） |
| `clip.inPoint` / `outPoint` の読み戻し | **★トリムの検算に使えない。`clip.end` で伸ばしても伸びない。** 尺は `end − start`（C-11） |
| `clip.start = 負の Time` | **スクリプトごと落ちる**（`ExtendScript execution failed`）。例外ですらない。伸ばす前にハンドル量でクランプ |
| **out点 > 素材尺** | **★エラーもクランプもしない。超過分を【完全な黒＋無音】で埋める**。配置の機械検算もPASSする（C-11-4） |
| `clip.remove(ripple, alignToVideo)` | `ripple=true` は**後続をずらす**。`remove(false, false)` を使う |
| QE `getVideoTrackAt(n).numItems` | **Empty（空き）も数える**。`type==="Clip"` で絞る |
| `addKey(t)` / `setValueAtKey(t,v)` | `t` は**クリップの inPoint 基準**。静止画の inPoint は約3600秒 |
| `videoTracks[n]` | 範囲外は `ExtendScript execution failed via CEP evalScript()`。`numTracks` を先読み |
| クリップ名 | 版が変わっても同名。`getMediaPath()` で照合する |
| 名前の文字列比較 | Premiere は **NFD** で返す。`charCodeAt` 配列で比較 |
| **`createNewSequence`** | **★引数に関係なくダイアログが開いて止まる**（人が OK を押すまで返らない）。`clone()` か `createNewSequenceFromClips` を使う（C-12） |
| タイムアウト | **失敗ではない**。処理が成功していることがある。読み戻してから再実行 |
| 開始秒での照合 | 許容は1フレーム以上（60fpsで0.0167s）。0.01sで44本中14本が外れた |

## C-1. ★トップレベルの `return` は構文エラー（2026-08-08 実測）

CEP はスクリプトを**そのまま `evalScript` に渡す**。関数に包んでくれない。
だから素の `.jsx` に `return` を書くと**構文エラー**になる。

実測（`pr.sh` で直接投げた結果）:

| スクリプト | 結果 |
|---|---|
| `"plain-ok";` | `result: "plain-ok"` |
| `if (1) return "ret-ok";` | **`ExtendScript execution failed via CEP evalScript()`** |
| `(function(){ if (1) return "wrapped-ok"; })();` | `result: "wrapped-ok"` |

**返ってくるエラーは「host-side scripting failure or CEP compatibility issue」だけで、
構文エラーだと分からない。** ここに何時間も溶かす。

対処: `pr.sh` と `prq.py` は**既定で本体を `(function(){ ... })();` に包む**。
包むと**末尾の裸の式は返らない**ので、`.jsx` の末尾は必ず `return <式>;` で書く。
包みたくない使い捨てスクリプトは `PR_WRAP=0`。

## C-2. CEPブリッジ本体の罠（パネルの実装を読んで確認・2026-08-08）

| 箇所 | 実際の挙動 |
|---|---|
| コマンドの取り出し | `fs.readdirSync()` の**最初の1件だけ**処理して `return`。**同時実行は不可** |
| その順序 | readdirSync 順で**時系列順ではない**。12件置いて実測したら `n01 n10 n06 n07 n11 n04 n12 n08 n09 n05 n02 n03` |
| ポーリング | 250ms 間隔。`isProcessing` が偽で `isConnected` が真のときだけ走査 |
| `validateScript` | `require(` `process.` `eval(` `new Function(` `__dirname` `__filename` `child_process` を含むと**問答無用で拒否**。**コメント内でもアウト**。返るのは `Script validation failed` だけ |
| スクリプト長 | 500,000 文字まで |
| タイムアウト | 既定 45秒。`timeoutMs` は**それより大きいときだけ**採用される（短くはできない） |
| 応答ファイル | `command-<id>.json` → `command-` を `response-` に置換した名前。同ディレクトリ |
| 設定の在り処 | `~/.premiere-mcp-bridge/config.json` と `<tempdir>/config.json` の2箇所 |

→ 投入順を守るには **ブリッジに置く command を常に1件だけ**にして、順番は呼ぶ側で持つ
（`scripts/prq.py`）。

## C-3. 書き出しは即時とキューで別API（2026-08-08）

| API | 挙動 |
|---|---|
| `sequence.exportAsMediaDirect(out, epr, workAreaType)` | **その場でレンダー**。同期なのでブリッジ全体が塞がる |
| `app.encoder.encodeSequence(seq, out, epr, workArea, removeUponCompletion)` | **AMEキューに積んで即返る**。jobID を返す（`0` なら投入失敗） |
| `app.encoder.launchEncoder()` / `startBatch()` | AME起動 / バッチ開始。成功時 `0` |
| `app.encoder.setEmbeddedXMPEnabled(0/1)` / `setSidecarXMPEnabled(0/1)` | XMP出力の制御 |

`workArea`: `0`=全体 / `1`=イン〜アウト / `2`=ワークエリア。
`app.encoder` は Premiere 14.3.1〜15 の **Mac で壊れていた**が 22+ で修正済み。

**AMEは別ソース同士を同時にエンコードしない**（同一ソースの複数出力だけ並列）。
キューは自動的に直列になる。

完了通知は ExtendScript に来ない。**AMEのログが正本**:
`~/Documents/Adobe/Adobe Media Encoder/<ver>/AMEEncodingLog.txt`（**UTF-16LE**・`cat` すると化ける）。
`- 出力ファイル : <path>` と `ファイルが正常にエンコードされました` で判定（`scripts/ame_watch.py`）。

## C-4. 複数プロジェクトの扱い（2026-08-08）

| 事実 | 出典/実測 |
|---|---|
| `app.project` は**アクティブなプロジェクト**を返すだけ。パネルのクリックで変わる | Adobe helpx |
| `app.projects` が開いている全プロジェクトのコレクション（`numProjects`） | docsforadobe ProjectCollection |
| `Project` のメソッドは**非アクティブなプロジェクトにも直接呼べる** | Adobe PProPanel サンプル |
| **`documentID` は UUID だがユニークではない。`.prproj` をコピーすると複製される** | ★2026-08-08 実測。本番と `cp` したコピーが同一IDだった |
| **同じ `documentID` のプロジェクトを2つ開くとシーケンスが合流する** | ★実測。本番 5本→10本（全部ユニークな別ID）。コピーを閉じても戻らない |
| `name` は同名 `.prproj` で衝突 | docsforadobe Project |
| **アクティブなシーケンスはアプリ全体で1本**。`activeSequence` を近道にしない | Adobe staff 回答 |
| **`app.executeCommand` は 26.3.2 に存在しない**（`typeof`=`undefined`） | 2026-08-08 実測。「アクティブに効くから使うな」以前に**無い**。Web上の解説は古い |
| **アンドゥでスクリプトの変更は戻せない** | `qe.project.undo()` は呼べるが、直前に足したクリップは対象・アクティブどちらも戻らなかった。**戻せない前提で作業する** |
| 1インスタンスで複数の普通の `.prproj` が**両方とも書き込み可能** | 2026-08-08 実機で3本同時に編集・保存できた |
| **非アクティブなプロジェクトの編集は実際に通る** | 実機で確認（下表） |
| `app.newProject(path)` は既存を閉じずに追加で開く。**新しい方がアクティブになる** | 実機 |
| `app.projects[i]` の**並び順は開いた順ではない** | 実機: `[0]=最後に作った方, [2]=最初から開いていた方` |

**★フォーカスを奪う操作／奪わない操作**（2026-08-08 実機・各操作の直前にフォーカスを戻して全数実測）:

| 奪わない | 奪う |
|---|---|
| 読み取り全般（`sequences`/`clips`/`disabled`/`getMediaPath`） | **`importFiles(...)`** |
| `overwriteClip` / `insertClip` | **`rootItem.createBin(...)`** |
| `clip.start=` / `clip.end=` / `clip.disabled=` / `clip.name=` / `remove()` | **`createSubClip(...)`** |
| `markers.*` / `setInPoint` / `setOutPoint` / `seq.name=` | **`createNewSequenceFromClips(...)`** |
| `getSettings` / `exportAsFinalCutProXML` / `createNewSequence`（空） | |
| `track.setMute` / `item.setScaleToFrameSize` | |
| キーフレーム一式（`getValue`/`setValue`/`setTimeVarying`/`addKey`/`setValueAtKey`/`getValueAtKey`） | |
| `proj.save()` / `app.encoder.encodeSequence(...)` | |

**★測り方の注意**: 先に奪う操作が1つあると、以降の判定が全部「アクティブ状態での結果」になる。
最初の測定はこれで誤った。**各操作の直前に必ずフォーカスを別プロジェクトへ戻す**こと
（移し方: 別プロジェクトに空ビンを作って消す＝`createBin` は奪うので確実）。

**★QE はアクティブなプロジェクトしか見えない**（2026-08-08 実測）:

- 対象=**プロジェクトA** / アクティブ=**プロジェクトB** のとき `qe.project.name` は **B**（アクティブ側）を返す
- `qe.project.getSequenceAt(i)` も**アクティブ側のシーケンスしか列挙しない**
- `qe.project.getActiveSequence()` は**アクティブプロジェクトと食い違うことがある**
  （実測で `qe.project` は B を指すのに `getActiveSequence()` は **A のシーケンス**を返した）。
  **QE の2つを突き合わせずに使うと別プロジェクトを編集する。**
- したがって **エフェクト追加・`removeEffects`・トランジションは非アクティブでは不可**

回避策: **`proj.openSequence(sequenceID)`**（`true` を返す）で
**プロジェクトとシーケンスの両方をアクティブにできる**。その後 QE が追従する。
実測: `openSequence` → `qe.project` も `getActiveSequence()` も **A側**に切り替わり →
`addVideoEffect(モザイク)` が通り `components 2→3` になった。

アクティブ化後は QE が一通り通る（実測）: `getVideoTransitionByName("クロスディゾルブ")` →
`clip.addTransition(tr, true)` 追加可 / `sequence.addTracks(1,n,0,0,0,0)` で V 4→5 /
`track.razor("00;00;02;00")` で V0 clips 1→2 / `clip.addVideoEffect(ef)` で components 2→3。
`clip.removeEffects(...)` は**呼べるが components が変わらなかった**（引数の意味は未確定）。

`qe.project` に**在る**メソッド（`typeof` で確認）:
`undo, redo, getVideoTransitionByName, getAudioTransitionByName, getVideoEffectByName,
getAudioEffectByName, getSequenceAt, getActiveSequence, newSequence, importFiles, save, close`
**無い**: `deleteSequence`, `openSequence`

`qe.project` のメンバ（プロパティのみ・`for in` は**メソッドを列挙しない**ので注意）:
`currentRendererName, importFailures, isAudioConforming, isAudioPeakGenerating, isIndexing,
name, numActiveProgressItems, numAudioPeakGeneratedFiles, numBins, numConformedFiles,
numIndexedFiles, numItems, numSequenceItems, numSequences, path`

**★`getKeys()` は time-varying でないとき `undefined` を返す**（2026-08-08 実測）。
`p.getKeys().length` と書くと `TypeError: undefined is not an object` で落ちる。
`setTimeVarying(false)` の直後に件数を数えようとして踏んだ。**必ず存在チェックしてから使う。**

## C-4-2. プロジェクト間で中身を移す（2026-08-08 実測・結果が割れた）

`app.executeCommand` が無いのでUIのコピー&ペーストは叩けない。代わりに:

1. `proj.importFiles(["/path/other.prproj"], true, proj.rootItem, false)`
   **挙動が一定しない**:
   - 小さな自作プロジェクト → `proj.sequences` が **8→10**。シーケンスとして使えた
   - 実案件のプロジェクト → **素材は入るが `proj.sequences` は増えない**。
     `rootItem` に `isSequence()===true` の項目としては居るが、
     元の `sequenceID` で `openSequence()` しても**全部 `false`**（IDは引き継がれない）
   → **素材を持ってくる手段としては確実。シーケンスを編集可能に持ってくる手段としては信用しない。**
   取り込む前に `other.save()`（未保存分は入らない）。フォーカスは奪う
2. 相手の `sequence.projectItem` を自分のタイムラインに `overwriteClip`
   → 置けた（実測 clips 2→3）。**プロジェクト跨ぎの依存が残る**。
   相手を閉じた後も成立するかは未検証

## C-4-3. ★`.prproj` のコピーを開いてはいけない（2026-08-08・実害）

「本番に触らないようテスト用コピーを作る」つもりで `cp` → `app.openDocument()` した結果:

- コピーは **`documentID` まで複製されている**（本番と同一）
- 開いた瞬間、Premiere が両者を同一視し、**本番プロジェクトのシーケンスが 5本→10本に合流**
  （元の5本は健在で、コピー側の5本が別IDで増殖）
- **コピーを閉じても戻らない**
- 保存していれば原本が壊れていた（`save()` を呼んでいなかったので原本は無傷）
- **アンドゥも効かない**ので、気づいてからでは戻せない

**回避**: テスト用に複製したいなら「コピーを開く」のではなく、
別プロジェクトを新規作成して素材を `importFiles` する。
作業前に `list_projects.jsx` で `documentID` の重複を必ず確認する。

## C-5. 外付けSSD(exFAT)の AppleDouble（2026-08-08 実測）

exFAT/SMB のボリュームでは macOS が `._<name>` という AppleDouble ファイルを作る。
これが `*.json` のグロブに一致してジョブとして拾われ、バイナリなので
`UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb0` で落ちた。
**ディレクトリ走査ではドットで始まる名前を必ず除外する**（`prq.py` の `job_files()`）。
| Premiere に `aerender` 相当の公式CLIは**無い**。`open -n` の複数インスタンスは非サポート | Adobe |


## C-6. MOGRT（2026-08-08 実測）

| 事実 | 詳細 |
|---|---|
| `sequence.importMGT(path, ticks, vOffset, aOffset)` | 実在。TrackItem を返す |
| `sequence.importMGTFromLibrary` / `createCaptionTrack` | どちらも実在（`typeof`=function） |
| **`getMGTComponent()` が null なら Premiere製** | 挿入した瞬間に**ネイティブグラフィック化**する。Adobe同梱は大半がこれ |
| テキストは JSON 文字列 | `getValue()` が `{` で始まる。`eval(` は使えない（禁止語）ので正規表現で読み書き |
| **`capPropFontEdit` はキーがあっても値が false のことが多い** | 同梱78個中、キー有74・**true は14**（サイズは11）。値で判断する |
| **★per-run配列は7つ全部の長さを揃える** | 1つでも不揃いだと `setValue` は成功し読み戻しも通るのに**UIで開いた瞬間に落ちる**（実際に落とした） |
| 部分強調で文字が消える | **ランは無罪。行の総幅がテキストボックスを超えた分だけ行頭から欠ける**（1文字だけ欠ける事例あり） |
| **per-run に色は無い** | 同梱78個を横断で確認。色はテンプレの独立パラメータで**テキスト全体**にかかる |
| 改行 | **`\n` が効く**。`\r` はリテラル文字列として入る |

→ 単語単位の色・グローは **AEのレンジセレクター**を公開するしかない（`references/MOGRT.md`）。

## C-7. エフェクトは136種ある（2026-08-08 実測）

`qe.project.getVideoEffectList()` で**全列挙できる**。決め打ちで探さない。

- グロー系: **VR グロー / アルファグロー / エコーグロー / エッジグロー / ワンダーグロー**
- ブラー系: VR ブラー / カメラブラー / ブラー (ガウス)(レガシ) / ブラー(滑らか) /
  エッジのぼかし / ピクセルモーションブラー / 指向性ブラー(レガシー) / ガウスぼかし

**エフェクトはクリップ全体にかかる。** 「この単語だけ光らせる」はできない。

## C-8. `pr.sh` / `prq.py` の事前検査（自分で踏んだので入れた）

- ブリッジの `validateScript` に弾かれる語は**投げる前に検出する**。
  `pr.sh` は素通りだったため `eval(` を書いて時間を溶かした（2026-08-08）。両方に検査を入れた
- パス照合は **NFC/NFD 両形**を渡す。「結合濁点を落として比較」は
  **NFC 側が変わらないので効かない**（正しいパスを中断させる誤検出を出した）


## C-9. UIにあってスクリプトに無いもの（2026-08-08 実測・すべて `typeof`=`undefined`）

| 分類 | 試した名前 | 結果 |
|---|---|---|
| マスク | `masks` `getMasks` `addMask` `createMask` `maskPath` | 全部 undefined（TrackItem・Component どちらにも無い） |
| エフェクトの順序 | `moveComponent` `reorder` `setIndex` `moveTo` | 全部 undefined。**追加した順に積まれるだけ** |
| プリセット | `getVideoEffectPresetList` `getPresetList` `getVideoEffectPresetByName` `importPreset` `applyPreset` `addPreset` `savePreset` | 全部 undefined |
| 調整レイヤー | `createNewAdjustmentLayer` `newAdjustmentLayer` `createAdjustmentLayer` `importAdjustmentLayer` | 全部 undefined |

QE に**在る**生成系: `newTransparentVideo` `newBlackVideo` `newColorMatte`
（`newAdjustmentLayer` は無い）。透明ビデオで調整レイヤーを代替できる可能性はあるが**未検証**。

**UIのパネル構成**: Premiere 25.0 以降、旧「エッセンシャルグラフィックス」の機能は
**「プロパティ」パネルへ移動**した。エフェクトコントロール（`Shift+5`）は健在で、
**エフェクトの全設定・順序・マスク・キーフレームはそちら**。

## C-10. エフェクトの複製はプロジェクトを跨げる（2026-08-08 実測）

参考プロジェクトのクリップからエフェクト名・全パラメータ・キーフレームを読み、
別プロジェクトのクリップ（MOGRTでも可）へ流し込める。**「属性をペースト」のスクリプト版。**

- キーフレーム時刻は **`clip.inPoint.seconds` を引いて相対化**して記録し、
  貼るときに `OFF + t` で戻す。これで尺の違うクリップにも移植できる
- 実測: エフェクト2個・パラメータ37件のうち **34件が完全一致**
- **色だけ不一致**。`18374966858408292000` のようなパック整数で返り、
  同じ値を `setValue` しても `4294967295`(`0xFFFFFFFF`＝既定の白) のままになる（未解明）
- `getKeys()` は time-varying でないとき `undefined` を返すので、読む前に `isTimeVarying()` を見る

## C-11. ★トリム投入（in点/out点で敷く）で踏んだもの（2026-08-13 実測）

運用ルールは SKILL.md 絶対厳守14条 / §3-1、実測の全量は `EDITING-MATRIX.md` §G。
ここは「踏むと分からなくなる」ものだけ。

**1. `setInPoint` は2引数。エラー文がそれを教えてくれない**

`Error: Not Enough Parameters` としか出ないので「`Time` の作り方が違うのか」と疑って
`Time` / 数値 / ticks文字列の3通りを試して全部同じエラーを踏んだ。
足りないのは**型ではなく引数の数**（`mediaType`）。`item.setInPoint(T(sec), 4)` が正。

**2. ★`outPoint` の読み戻しは「伸ばしても伸びない」**

`clip.end` でクリップを伸ばした後の読み戻し（実測）:

```
V0[2] tl=8.0000-14.0000  (＝6秒)
      src=5.0000-9.0000  (＝4秒)   ← 食い違っている。outPoint は元の値のまま
```

書き出した画素では **src 5.0→11.0 が出ている**（ハンドルから2秒ぶん伸びている）。
つまり `outPoint` は嘘をつく。§3-3 のキーフレーム事故と同じで、
**同じAPIで書いて同じAPIで読む検算は、この種の誤りを原理的に検出できない。**

- 尺の検算は **`end − start`**
- 「本当にその素材のその瞬間が出ているか」は**書き出した実ファイルの画素**
- 実写素材は焼き込みTCが無いので **SSIM + 対照実験**（フリーズ説・隣接フレーム説と比べる）。
  ±5F を1F刻みでスキャンして**0Fずれに単峰のピーク**が立てばフレーム厳密

**3. `clip.start` に負の `Time` を代入するとスクリプトごと落ちる**

素材の頭より前へ伸ばそうとしたときに踏んだ。`try/catch` で捕まらず、
**そのスクリプト全体が `ExtendScript execution failed via CEP evalScript()` になる**
（＝その前に書いた変更は適用済みで、後半だけ実行されない）。
**伸ばす前に残ハンドル量を計算してクランプする。**

**4. ★★★ 素材尺を超える out 点は「黒＋無音」で黙って埋められる（最も危険）**

60.0秒ちょうどの素材に `in=55.0 / out=65.0`（5秒ぶん存在しない）を打って敷いた結果:

| 見えたもの | 実測 |
|---|---|
| `setOutPoint` | **エラーにならない**。読み戻しも `65.000` を返す |
| 出来たクリップ | **10秒（300F）**。クランプされない |
| 配置の機械検算（clips数・`end−start`） | **PASSしてしまう** |
| 書き出した実ファイル | **5.000秒ちょうどから末尾まで完全な黒**（`blackdetect` で 4.967秒） |
| その区間の音声 | **-47.8 dB（無音）**。前半は -24.1 dB |

**フリーズですらなく、黒である。** そして Premiere も ExtendScript も何も言わない。
「配置は全項目PASSしたのに完成品の後半が真っ黒」という事故が、これで簡単に起きる。

**対策**: トリム範囲は**生成の時点で ffprobe の実尺と突き合わせて落とす**
（`core/pipeline/scripts/place_premiere.py` の `guard_range()` が実装。
`src_out > 実尺` / `src_in < 0` / `src_out <= src_in` で中断する）。
手書きの jsx を投げるときも、**素材尺を確かめてから** in/out を打つこと。

**5. `overwriteClip` の「1F過剰」は格子に乗せれば起きなかった**

合成素材3カット＋実写4K素材3カットの計6カットで、フレーム格子に丸めた秒を渡したところ
**全カットが設計フレーム数に厳密一致**した。過剰配置はサブフレームの秒を渡したときの症状。

## C-12. ★シーケンス作成はダイアログで止まる（2026-08-13 実測・★2回訂正した）

**`proj.createNewSequence(name, ...)` は「新規シーケンス」ダイアログを開いて、
人が OK を押すまで返らない。第2引数を何にしても出る。**

### この項目は2回間違えた（同じ原因で）

| 記述 | 実際 |
|---|---|
| 1回目「通る・奪わない」 | ✕ 測定器 `probe_focus.jsx` が `""` を使っていて、人が押していた |
| 2回目「空でない文字列なら出ない」 | ✕ **こちらも人が押していた**（9360ms 掛かっていたのが証拠） |

**「スクリプトが戻ったか」ではダイアログの有無を判定できない。** 人が横にいると通る。

### 唯一確実な測り方

**誰も画面を触らない状態で、短いタイムアウトを掛けて止まるか見る。**
到達ログを1行ずつファイルへ書きながら呼ぶと、止まった位置が分かる。

```javascript
function mark(s){ var f=new File(LOG); f.encoding="UTF-8"; f.open("a"); f.writeln(s); f.close(); }
mark("1) 直前");  proj.createNewSequence(name, "vops");  mark("2) 戻った");
```

実測: ログが `1) 直前` で止まり15秒でタイムアウト。画面には「新規シーケンス」ダイアログが出ていた。

### ★ダイアログを出さずに作る2つの手段（無人で完走を確認）

| 手段 | 所要 | 条件 | フォーカス |
|---|---|---|---|
| **`sequence.clone()`** | **30〜250ms** | 複製元が1本要る | 奪わない |
| **`createNewSequenceFromClips(name,[item],bin)`** | **87ms** | 素材が1つ要る | 奪う |

**どちらも直後に `setSettings` で仕様を変えられる**（横型の複製元から縦型へ変更できることを実測）。
複製は中身のクリップが残るので、`clip.remove(false,false)` で空にしてから使う。
手順の全文は `EDITING-MATRIX.md` §H。

★**プリセットの内容は反映されない。** `createNewSequence` に何を渡しても 1920x1080/23.976 で作られる。
仕様は必ず `setSettings` で決める。

## D. 数値の実測メモ

- 静止画クリップの `inPoint` = **3599.969秒**（3600秒問題は実在）
- 位置は**正規化座標**。中心 `[0.5, 0.5]`、±Npx は `0.5 + N/1080`（縦は `/1920`）
- `in`/`out` が「トリム」ではなく**開始タイムコード表記**のことがある。
  `out − in` が素材全長と一致するならトリムではない
  （実例: `in=1.9686` だが `out−in = 20.020s = 600F = 素材全長` → **f0 = クリップ頭**。
  画素マッチで裏取り済み・相関0.9997）
- 29.97系の変換: `TL = h*3600 + m*60 + s + f/(30000/1001)`

## E. 使えるエフェクト（日本語UIで確認）

プロセスアンプ / VR グロー / 方向ブラー / VR デジタルグリッチ / トランスフォーム

## F. 書き出し

- 「Mobile Device 1080p HD」プリセットは**1920×1080の横向きに強制する**
- 縦型は **「Match Source - High bitrate」**
  （`.../MediaIO/systempresets/4E49434B_48323634/`）

## G. プロジェクトファイル

**同じ `.prproj` を2重に開いたまま片方を保存すると、もう片方の古い内容で上書きされる**
（実際に17の作業が消えた）。

## H. After Effects（MOGRTを作る側・2026-08-08 実測）

AE は **CEPブリッジ不要**で AppleScript の `DoScript`/`DoScriptFile` から直接叩ける
（`scripts/ae.sh`）。ただし罠は Premiere と別系統。全体は `AE-MOGRT-BUILD.md`。

| 罠 | 中身 |
|---|---|
| **`catch(e)` で `"..." + e` が落ちる** | ExtendScript は Error オブジェクトを連結できない。`String(e)` |
| **エラー＝以降の全スクリプトが死ぬ** | モーダルで停止する。`app.beginSuppressDialogs()` で抑止 |
| **`get version` は当てにならない** | ダイアログが開いていても応答する。生存確認はファイルを書かせる |
| **`File.writeln` の改行が `\r`** | 既定が Mac古典。`f.lineFeed = "Unix"` |
| **`DoScript` の戻り値は 0/1 だけ** | 結果はファイル経由 |
| **`setPropertyParameters` はプロパティを作り直す** | 参照が死に、**エフェクト名も消える**。ドロップダウン専用 |
| **`addToMotionGraphicsTemplate` も参照を無効化** | 毎回 名前/index で取り直す |
| **式で組んだ TextDocument は MOGRT で描画されない** | 書体は値として焼き込む |
| **未インストールのフォントは黙って代替される** | `app.fonts.allFonts` で実在を確認 |
| **レイヤースタイルは有効化できない** | 11種あるが `canSetEnabled=false` |
| **`exportAsMotionGraphicsTemplate` の第2引数はディレクトリ** | ファイルパスではない |

## I. 「絵に出ない」と判断する前に（2026-08-09・実害あり）

**Premiere のタイムラインは下に素材が無ければ背景が黒。**
白文字＋黒フチの MOGRT をそのまま置くと、**フチは正しく出ていても背景と同化して見えない。**
これを「スクリプトが効いていない」と誤判定し、原因究明に半日使った。

- **確認用に置くときは、背景と絶対にぶつからない色にする**か、**下に素材を敷く**
- **数値は設定できるが色は設定できない**（`MOGRT.md` §6-2）ので、
  確認用の色は**テンプレート側の既定値として焼いておく**
- AE 側の `sourceRectAtTime` で線が出ていることを確認済みなのに Premiere で見えない、
  という状況では**まず配色**を疑う。レンダラーの非互換を疑うのはその後

## J. 配置と書き出しで踏んだもの（2026-08-09）

| 罠 | 中身 |
|---|---|
| **`importMGT` の ticks は「文字列」** | 数値で渡すと時刻が効かず、**全部0秒に入る**。`String(Math.round(sec*TPS))` |
| **`importFiles` は非同期** | 呼んだ直後に `rootItem.children` を探しても**見つからない**。実行を分ける |
| **`createNewSequence` は既定プリセット** | 1920x1080 / 23.976fps で作られる。**縦型は L. の方法で作れる（2026-08-09 解決）** |
| **出力の拡張子はプリセットが上書きする** | `.mp4` を渡しても H.264 システムプリセットでは **`.mov`** で出る。完了待ちで誤判定した |
| **モーションの「位置」が2箇所ある** | 「グラフィックパラメーター」側にも「位置」がある。**コンポーネント名で絞る** |
| **モーションの位置は正規化** | 0〜1。`(フレーム幅/2 + ずらす量) / フレーム幅` |
| `seq.setPlayerPosition("0")` | 頭出し。引数は**文字列のticks** |
| **MOGRTのコンプは等倍で中央に置かれる** | 縮尺されない。コンプ1080幅・フレーム1920幅なら**コンプpx = フレームpx**（水平オフセット+420） |
| **ドロップダウンは Premiere が0始まり** | AEで既定2にしたものを Premiere の API で読むと `1`。**設定時は AEの値−1** |
| **書き出しは速い** | 20秒のシーケンスが**2秒**（ハードウェアエンコード）。待ち時間の見積もりに使う |

★H.264 のシステムプリセット:
`/Applications/Adobe Media Encoder 2026/Adobe Media Encoder 2026.app/Contents/MediaIO/systempresets/3F3F3F3F_4D6F6F56/H264 Match Source - High bitrate.epr`

## K. シェルスクリプト側で踏んだもの

- **変数の直後に全角文字を置かない。** `"$ALL）"` は変数名 `ALL）` として解釈されて
  `unbound variable` で落ちる。**`${ALL}`** と波括弧で囲む
- **`ffmpeg` に `-v error` を付けると ssim/psnr の出力ごと消える。**
  `-hide_banner` にして `grep -i SSIM | tail -1` で拾う
- **`node --check` は `.jsx` を拡張子で弾く**（Node 25）。`.js` にコピーしてから検査する
- **★`ffmpeg` を `while read` ループの中で回すと stdin を食われる**（2026-08-13 実測）。
  ヒアドキュメントの残りを ffmpeg が読み込んでしまい、**2行目以降のフィールドが欠けたまま処理される**
  （`tl=3.90` が `tl=.90` になり、生成物のファイル名が壊れた。エラーは一切出ない）。
  **`ffmpeg -nostdin`** を付ける（`core/compilation/scripts/build_compilation.py` は既に対応済み）

## L. 縦型シーケンスはスクリプトで作れる（2026-08-09 実測・J. の「未調査」を解消）

`createNewSequence` の後に **`getSettings` → 値を書き換え → `setSettings`** で通る。
参考プロジェクト（1080×1920 / 30fps）と**全項目が一致**することを読み戻しで確認した。

```javascript
var st = seq.getSettings();
st.videoFrameWidth  = 1080;
st.videoFrameHeight = 1920;
var t = new Time(); t.ticks = "8467200000"; st.videoFrameRate = t;   // 30fps ちょうど
st.videoPixelAspectRatio = "1:1";
st.editingMode = "795454d9-d3c2-429d-9474-923ab13b7018";             // カスタム
st.videoFieldType = 0;
seq.setSettings(st);
```

★`videoFrameRate` は **`Time` オブジェクト**。数値やfpsの値ではなく **1フレームあたりのticks**。
`TICKS_PER_SECOND = 254016000000` なので 30fps は `254016000000/30 = 8467200000`。

## M. 尺・格子・素材長で踏んだもの（2026-08-09・すべて実害）

### ★カットは必ずフレーム格子に乗せる

設計値の秒（例 0.92 / 1.95 / 2.52…）をそのまま `overwriteClip` に渡すと、
**カット間にサブフレームの隙間**ができる。フレーム数で敷き直す。

```javascript
V1.overwriteClip(item, T(f0 * TPF));
V1.clips[k].end = T(f1 * TPF);        // TPF = 8467200000（30fps）
```

検算は「前のクリップの `end` フレーム == 次のクリップの `start` フレーム」を全数。

### ★★MOGRT の素材長は 150F（5.000秒）。超えて伸ばすと描画されない

`clip.end` で 337F まで伸ばしても、**150F 以降は絵が出ない**。
しかも **読み戻しでは絶対に気づけない** — クリップは 0-337F に見える。
書き出した画素を測って初めて分かった。

→ **同じ MOGRT を複数枚、隙間なく敷き詰める**（0-150 / 150-300 / 300-337）。

### ★全トラックの終端を並べて比較する（1フレームの穴）

V1 の最終カットだけ 336F で終わり、他トラックは 337F という**1フレームの穴**が出た。
目視では絶対に分からない。**毎回この検算を入れる。**

```javascript
for (var v=0; v<seq.videoTracks.numTracks; v++){
  var tr = seq.videoTracks[v]; if (!tr.clips.numItems) continue;
  var e = Math.round(Number(tr.clips[tr.clips.numItems-1].end.ticks)/TPF);
  if (e !== TOTAL) log("★V"+(v+1)+" 終端="+e+"F");
}
```

### ★`縦横比を固定` の既定は false

`スケール(高さ)` だけにキーフレームを打つと、**縦に伸びるだけ**でズームにならない。
参考は true。**倍率が設計どおりにならないときは、まずここを疑う。**

### `app.newProject()` は返らないことがある

ダイアログで止まり、ブリッジがコマンドを消費しなくなる。
**タイムアウト＝失敗ではない**（プロジェクトもシーケンスも出来ていた）。
二度実行せず、まず「既に開いているか」を読む。

## N. 名前と単位で踏んだもの（2026-08-09・実害あり）

### ★★`縦横比を固定` を true にすると、プロパティ名が変わる

| 縦横比を固定 | プロパティ名 |
|---|---|
| `false` | `スケール (高さ)` ＋ `スケール (幅)` |
| **`true`** | **`スケール`**（`スケール (幅)` は**空文字の名前**になる） |

`スケール (高さ)` だけを探す検算は、**固定=true のクリップを「キーフレームが無い」と誤判定する。**
実際に6カット中3カットを「ズーム未適用」と誤って報告した。**両方の名前を受け付ける**こと。

```javascript
if (n === "スケール" || n === "スケール (高さ)") { ... }
```

★さらに悪いのは、**その分岐の中でカウントしていた「不備件数」も0のままになる**こと。
**検算のカウンタは、分岐の外で「見つからなかった」を数える。**

### ★MOGRT の `縦位置` は中心ではなく「テキストの下端」

`縦位置(%) × コンプ高さ` が**文字の下端**に一致する。中心だと思って組むとズレる。

実測（1080×1920・完成画素で確認）:

| 設定値 | 予測 y | 実測の下端 | 差 |
|---|---|---|---|
| 81.71% | 1568.8 | 1571 | 2px |
| 83.76% | 1608.2 | 1608 | 0px |

### ★クリップを差し替えると隣のクリップに2フレームの穴が空く

`remove()` → `overwriteClip()` で置くとき、素材に余裕（+2F）を付けて置いてから
`clip.end` で詰めると、**余裕分が隣のクリップの頭を上書きしたまま残る**。

- 症状: 次のクリップの `start` が2F後ろにずれる
- 対処: 差し替えのあと**必ず全クリップの `start`/`end` を連続性で検算**し、
  ずれていたら `clip.start` を戻す
- ★`clip.start` を戻すと**頭が伸びた分だけキーフレームが inPoint 基準からずれる**
  （実測: `-2F:100 / 52F:115` になっていた）。**打ち直す**こと。
  キーの全消しは `setTimeVarying(false)` → `setValue(既定)` → `setTimeVarying(true)`

## O. 完成画素での測り方（2026-08-09 実測）

**動く被写体のクリップでは、倍率を「先頭フレーム vs 末尾フレーム」の相関では測れない。**
内容そのものが変わるので、スケールだけのモデルが当たらない（実測の相関 0.12〜0.73）。

| 測れる | 測れない |
|---|---|
| 静止した被写体（相関 0.92〜0.99 で設計値と一致） | 手や商品が動くカット |

→ 動くカットは**「測れていない」と書く**。読み戻しが通ったことを根拠に「効いている」と書かない。

**色は背景と一緒に測る。** テロップの色を素材から採ると、**背景の支配色と同じになって埋もれる**。
背景平均色との色差（ΔRGB）を出して、参考の実測帯と比べる。

| | テロップ色 | 背景 | ΔRGB |
|---|---|---|---|
| 参考A | `#EAB1A3` | `#989083` | 93.3 |
| 参考B | `#EFE919` | `#C1B795` | 141.8 |
| **踏んだ失敗** | `#D4B27D` | `#C6A26B` | **27.2**（読めない） |

## P. MOGRT の「強調」と絵文字（2026-08-10 実測）

### ★★強調は「出現アニメ」が無いと発火しない

`強調の出方` を「後から跳ねる」にしても、**`出現の型` が「なし」だと一切動かない**。
全28フレームで bbox が1pxも変わらず、原因が分からないまま時間を溶かす。

`強調の遅れ` は**出現アニメが終わってからの秒数**。だから出現が無いと起点が立たない。

| `強調の出方` | 効き方 |
|---|---|
| `0`（なし） | **静的に効く**。指定した範囲が最初から大きく・別の色になる |
| `1`以上（跳ねる／色が乗る／両方） | **アニメのみ**。静的には効かず、出現アニメの後に一度だけ動く |

**静的な強調が欲しいなら `0`、動かしたいなら `1`以上＋出現アニメを必ず入れる。**

### 強調の振幅が小さいと1フレームで終わる

`強調1の大きさ` 25 では、30fps で**基準から4px以上ずれるのが1フレームだけ**だった（112→131px）。
人の目には一瞬すぎる。**40〜60まで上げると10〜27フレームにわたって動く**。

診断のしかた: 赤・特大・全文字・出現アニメ有り、の「絶対に見えるはずの条件」を1本書き出し、
**全フレームの bbox と色画素を測る**。原因候補が複数あっても一度で決着する。

### ★`importMGT` で置き直すとモーションの「位置」が既定に戻る

テロップを敷き直すと、それまで付けていた**横位置のオフセットが消えて中央に戻る**。
本文だけ動いて、別トラックに置いた画像（絵文字など）は元の位置に残るので**重なる**。
→ 敷き直したら**位置・スケールを必ず設定し直す**。

### 絵文字は画像で置く（フォントでは出ない）

ファイル名は Unicode コードポイント（`1f447.png` = 👇）。72×72 の PNG。

- **描画高さ ＝ フォントサイズ** になるようスケールを決める（`スケール = フォントサイズ ÷ 72 × 100`）
- **画像の中心を本文の中心に合わせる**（モーションの `位置` は画像の中心。アンカーは 0.5,0.5）
- 本文の末尾に**全角スペースを1つ**入れて、その上に重ねる

★**強調で本文の幅が変わると、隣に置いた画像と衝突する**。
強調の大きさを変えたら、**本文の最大右端を全フレームで測ってから**画像を置き直す。

### 色マスクは背景に汚染される

絵文字やテロップの色は、背景（食材・木目など）に同系色があると**マスクで分離できない**。
実際に「フレーム全体が検出された」ことが何度もある。
**裁定は拡大して目視**。機械で測るなら、背景に無い色（フチ色など）を手がかりにする。
