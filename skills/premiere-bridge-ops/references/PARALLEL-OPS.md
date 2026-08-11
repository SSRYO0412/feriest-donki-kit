# 並列運用の設計根拠（なぜこの形なのか）

SKILL.md §2 の手順の裏付け。**なぜ直列キューが要るのか／なぜAMEに投げるのか**を、
CEPパネルの実装を読んだ結果と実機の実測で示す。手順だけ要るなら SKILL.md で足りる。

## 1. ブリッジは構造的に直列（実装を読んで確認）

`~/Library/Application Support/Adobe/CEP/extensions/MCPBridgeCEP/bridge-cep.js` の実装:

```javascript
// startCommandPolling
setInterval(function () {
    if (!self.isProcessing && self.isConnected) {
        var tempPath = self.getTempDirectory();
        if (tempPath) self.watchDirectory(tempPath);
    }
}, 250);

// watchDirectory
var files = fs.readdirSync(watchedPath);
for (var i = 0; i < files.length; i++) {
    var file = files[i];
    if (file.indexOf('command-') === 0 && ...) {
        this.processCommandFile(path.join(watchedPath, file));
        return;                      // ★1件処理したら抜ける
    }
}
```

- 250ms ごとに、`isProcessing` が偽で `isConnected` が真のときだけ走査
- **最初に見つけた1件だけ**処理して `return`
- → **同時に2本の ExtendScript を走らせることは原理的にできない**

これは設定ではなく実装なので、回避できない。並行化は層を分けるしかない。

## 2. `readdirSync` の順は時系列順ではない（実測）

12件を `n01`〜`n12` の順で置いて `os.listdir()`（＝`readdirSync` 相当）が返す順を見た:

```
投入順: n01 n02 n03 n04 n05 n06 n07 n08 n09 n10 n11 n12
返る順: n01 n10 n06 n07 n11 n04 n12 n08 n09 n05 n02 n03
```

**まとめて置くと実行順が壊れる。** 投入順を守るには
**ブリッジに置く command を常に1件だけ**にして、順番は呼ぶ側で持つしかない。
それが `scripts/prq.py`。

### 検証のやり方（再現できるようにしておく）

本物と同じ挙動（250msポーリング・`isProcessing`・`listdir` 先頭1件）の**偽ブリッジ**を書いて
`prq.py` を実走させ、5件が投入順どおり `00001`→`00005` で直列に流れることを確認した。
Premiere が無くてもキューの検証ができる。

## 3. `validateScript` の禁止語

パネルは以下を含むスクリプトを**問答無用で拒否**する。**コメント内でもアウト**。

```
require(   process.   eval(   new Function(   __dirname   __filename   child_process
```

返るのは `Script validation failed` だけで原因が分からない。
`prq.py enqueue` が投入時に検出して中断する。
スクリプト長は 500,000 文字まで。

## 4. タイムアウトの扱い

- 既定 45秒。`timeoutMs` は**それより大きいときだけ**採用される（短くはできない）
- **タイムアウトは失敗ではない**。Premiere側で処理が続いている可能性がある
- 次を投げると**二重実行**になるので、`prq.py run` は exit 2 で停止しジョブを `running/` に残す
- 再開前に必ず状態を読み戻す

## 5. 書き出しを AME に投げる理由

| API | 挙動 |
|---|---|
| `sequence.exportAsMediaDirect(out, epr, workAreaType)` | **その場でレンダー**。同期なのでブリッジ全体が塞がる |
| `app.encoder.encodeSequence(seq, out, epr, workArea, removeUponCompletion)` | **AMEキューに積んで即返る**。jobID を返す（`0` なら投入失敗） |

1時間の書き出しを `exportAsMediaDirect` でやると、その間**他の動画の編集ジョブが1件も流れない**。

**実測**: `encodeSequence` は **0.45秒**で jobID を返し、
AMEがエンコードしている最中に別プロジェクトの編集ジョブが **0.46秒**で通った。

その他の `app.encoder`:
`launchEncoder()`（未起動なら起動・成功時 `0`）/ `startBatch()` /
`setEmbeddedXMPEnabled(0|1)` / `setSidecarXMPEnabled(0|1)`。
`workArea`: `0`=全体 / `1`=イン〜アウト / `2`=ワークエリア。
`app.encoder` は Premiere 14.3.1〜15 の Mac で壊れていたが 22+ で修正済み。

## 6. AMEは別ソース同士を同時にエンコードしない

同一ソースの複数出力（H.264 + ProRes 同時）は並列化できるが、
Sequence A と Sequence B は**同時に回らず順次処理**される。
→ **キューは自動的に直列になる**ので、こちらで直列化する必要はない。
これが「書き出しは直列」の実体。

## 7. 完了検知（ExtendScript に通知は来ない）

`encodeSequence` の jobID は「キューに積めた」証拠であって「書き出せた」証拠ではない。
AME は結果を必ずログに書くので、そこを正本にする。

- 場所: `~/Documents/Adobe/Adobe Media Encoder/<ver>/AMEEncodingLog.txt`
- **UTF-16LE**（BOM `ff fe`）。`cat` すると化ける。必ずデコードして読む
- 書式（日本語UI）:

```
MM/DD/YYYY hh:mm:ss PM : キューが開始されました
 - ソースファイル : <path>
 - 出力ファイル : <path>
 - 使用されているプリセット : <name>
 - ビデオ : 1080x1920 (1.0), 29.97 fps, ...
 - オーディオ : AAC, 320 Kbps, 48 kHz, ステレオ
 - エンコード時間 : 00:12:24
MM/DD/YYYY hh:mm:ss PM : ファイルが正常にエンコードされました
MM/DD/YYYY hh:mm:ss PM : キューが停止されました
```

`scripts/ame_watch.py` がこれを解析する（実ログ50エントリで検証済み）。

★ログの「正常にエンコードされました」は **AMEが落ちなかった**という意味しかない。
中身は SKILL.md §4 のとおり**書き出した実ファイルの画素**で測る。

## 8. 1台のMacで並列レンダーはしない

- Premiere に `aerender` 相当の**公式CLIは無い**（After Effects にはある）。
  `.app` を直叩きしてもGUIが起動するだけで、シーケンス指定・プリセット・
  完了ステータスの契約が無い
- `open -n -a "Adobe Premiere Pro 2026"` は macOS の汎用機能で **Adobe非サポート**。
  環境設定・メディアキャッシュDB・Dynamic Link・GPU/VideoToolbox セッションを共有して競合する。
  Adobe自身が「プロジェクトごとに別インスタンスを起動するな」と回答している
- 1台で2本回すと CPU/メモリ帯域/GPU/ハードウェアエンコーダを食い合い、
  **直列より遅くなることがある**（特に long-GOP H.264/HEVC のデコード）
- 本当に並列レンダーが要るならマシンを分け、各ノードに独立したユーザー環境・
  キャッシュ・スクラッチ・出力パスを持たせてジョブキューで分配する

## 9. キューの実装メモ（`scripts/prq.py`）

- ジョブは `pending/` → `running/` → `done/`|`failed/` と移動する
- 順序は**こちらが振った連番**（`00001-<label>.json`）。`readdirSync` 順に依存しない
- `--doc-id` を渡すと先頭に `prqResolveProject()` / `prqFindSequence()` が注入される
- 本体は `(function(){ ... })();` に包まれる（トップレベル `return` が構文エラーのため）
- **exFAT/SMB の `._` AppleDouble を除外する**。外付けSSD上にキューを置くと
  macOS が `._<name>` を作り、`*.json` に一致してバイナリを読み込み
  `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb0` で落ちた（実際に踏んだ）
