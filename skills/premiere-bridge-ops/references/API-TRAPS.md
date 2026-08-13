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
| `overwriteClip` | **1フレーム長く置くことがある**。`clip.end` で詰める |
| `clip.remove(ripple, alignToVideo)` | `ripple=true` は**後続をずらす**。`remove(false, false)` を使う |
| QE `getVideoTrackAt(n).numItems` | **Empty（空き）も数える**。`type==="Clip"` で絞る |
| `addKey(t)` / `setValueAtKey(t,v)` | `t` は**クリップの inPoint 基準**。静止画の inPoint は約3600秒 |
| `videoTracks[n]` | 範囲外は `ExtendScript execution failed via CEP evalScript()`。`numTracks` を先読み |
| クリップ名 | 版が変わっても同名。`getMediaPath()` で照合する |
| 名前の文字列比較 | Premiere は **NFD** で返す。`charCodeAt` 配列で比較 |
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
| **★`createNewSequence(name, "")` は止まる** | **第2引数が空文字列だと「新規シーケンス」ダイアログが開き、人が OK を押すまで返らない**。空でない文字列（`"vops"` 等）を渡す。中身は見ていない（存在しないパスでも通る） |
| **`createNewSequence` は既定プリセット** | **プリセットのパスを渡しても内容は反映されない**。何を渡しても 1920x1080 / 23.976fps。縦型にするには作ってから `setSettings` で上書きする |
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
