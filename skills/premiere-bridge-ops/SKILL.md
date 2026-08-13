---
name: premiere-bridge-ops
description: Premiere Pro をスクリプトから安定して自動操作するスキル。3本柱で構成する。①接続 = CEP Bridge の手順（毎セッション手動の Start Bridge）・.jsx をファイル渡しで叩く・結果はファイル経由で受け取る・トップレベル return は構文エラー。②並列 = 複数本の動画を同時に進める運用（app.projects と documentID で対象を固定してフロント依存を切る／直列ジョブキュー prq.py で投入順を保証／書き出しは app.encoder.encodeSequence で AME キューへ非ブロッキング投入し ame_watch.py で完了実測）。③編集 = どの操作が非アクティブのまま通るかの全数実測マトリクス・overwriteClip・clip.disabled・キーフレームの inPoint 基準・QE がアクティブ依存であること・executeCommand が存在しないこと・ネイティブGraphic は新規作成も本文/フォント/サイズ/色の変更もできないこと（.prproj を直接読めば取れる）・テキストを作るなら MOGRT 一択でその全知見（AE製のみ有効・capProp の値確認・部分強調の複数ランは配列長を揃えないと落ちる・欠けは幅が原因）。④AE側でMOGRTを作る = After Effects は AppleScript(DoScriptFile)で直接叩けるのでブリッジ不要（ae.sh/aecheck.sh）・エッセンシャルグラフィックスに露出できる型と「範囲を編集」・1つの雛形から書体を変えるにはドロップダウン＋レイヤー出し分け（式で組んだTextDocumentは描画されない）・フチはソーステキストに無いのでテキストアニメーターの線幅を露出する・フォントは app.fonts.allFonts で実在確認（未インストールは黙って代替される）・レイヤースタイルはスクリプトから有効化できない。⑤テロップ制作の通し運用 = 準備→テンプレ生成→Premiereへの配置→検証→書き出し→記録の手順書（TELOP-WORKFLOW.md）と、書き出さずにsourceRectAtTimeで測る／ffmpegのSSIM・PSNRで実ファイルを判定する／対照実験を必ず置く／測定器の盲点を疑う／診断物を1本作って1回の目視で決着させる／ユーザーに絵を見てもらうときの渡し方（VERIFY-METHOD.md）と、クリップ全体に掛かるものはPremiere側・文字の中に踏み込むものはAE側という境界線と原理的に無理なもの一覧（DESIGN-BOUNDARY.md）。importMGTのticksは文字列・importFilesは非同期・出力の拡張子はプリセットに上書きされる・モーションの位置は正規化・テキストアニメーターの数値は加算で色は置き換え。Premiere のタイムライン操作・クリップ差し替え・エフェクト/キーフレーム・書き出し前の状態確認・複数プロジェクトの並行編集・書き出しキューの運用・ExtendScript がタイムアウトする問題の切り分け・MOGRTテンプレートの新規作成で必ず使う。
---

# Premiere Pro スクリプト操作スキル（premiere-bridge-ops）

> 出自: 2026-07〜08 に Premiere を自動操作して踏んだ事故と、2026-08-08 に
> Premiere 26.3.2 で全数実測した結果の積み上げ。
> **①スクリプトの戻り値 ②アプリからの読み戻し だけで「適用済み」と報告してはならない。**
> **③書き出した実ファイルの画素/波形で測るまで完了と言わない。**（§4）

---

# ★★★ 絶対厳守（14条）

**この14条はすべて実機で事故った結果として書かれている。守らないと同じ事故が再発する。**

1. **戻り値と読み戻しだけで「できた」と報告しない。**
   **書き出した実ファイルの画素で測るまで完了と言わない。**
   同じAPIで書いて同じAPIで読む検算は、**座標系・単位の誤りを原理的に検出できない。**
2. **絵の最終判断はユーザーがする。** こちらは機械検算まで通し、
   **どこを見るか・その結果でどう分岐するかを添えて渡して止まる。**
3. **「効いていない」と思ったら、まず背景色と測定器を疑う。**
   （黒背景に黒フチ／外形は両端の文字でしか動かない——どちらも実際に半日溶かした）
   アプリ側の非互換を疑うのは**その後**。
4. **対象は `documentID` で固定し、名前と3点照合してから触る。**
   **重複していたら中断する。**（`.prproj` のコピーで複製される。実案件を汚染した）
5. **`.prproj` のコピーを開かない。** 同じIDのプロジェクトを2つ開くと**シーケンスが合流する**。
6. **`.mogrt` を書き出したら必ず `scripts/mogrt_enable_font_edit.py` を通す。**
   通さないと Premiere から書体もサイズも変えられない。
7. **本文を変えたら `fontTextRunLength` を文字数に合わせる。**
   揃えないと `setValue` は成功し読み戻しも通るのに、**UIで開いた瞬間に落ちる。**
8. **キーフレームの時刻は `clip.inPoint.seconds` 基準**（静止画・ネイティブGraphicは約3600秒）。
9. **テキストアニメーターの数値は「加算」される。** スロット側は**追加分だけ**返す。**色は置き換え。**
10. **ドロップダウンは `AEの値 − 1`**（Premiereは0始まり）。
    **EGPのスライダーは Premiere 側で 0〜100 に丸められる**（255→100・-1→0）。
    **色はカラー型では設定できない**ので、**0〜100 の数値スライダー3本**で持たせる。
11. **上書きしない。** テンプレも py も MOGRT も**v番号を上げ、却下版を理由つきで残す。**
12. **露出項目は後から増やせない。** 増やすと配置済みクリップの差し替えになる。
    設計時に「なし」を入れて余裕を持たせる。
13. **MOGRT の素材長は 150F（5秒）。`clip.end` で超えて伸ばすと 150F 以降は描画されない。**
    しかも**読み戻しでは検出できない**（クリップは伸びて見える。書き出した画素で初めて分かる）。
    長い区間は**複数枚を隙間なく敷き詰める**（例: 337F = 0-150 / 150-300 / 300-337）。
14. **★素材は切らずにトリムで入れる。** 元素材を秒数で切り出したファイルを作って置いてはならない。
    **元素材を取り込み、`setInPoint`/`setOutPoint` を打ってから `overwriteClip` する**（§3-1）。
    切り出すと**後から伸ばす自由が原理的に消え**、修正のたび ffmpeg へ戻ることになる。
    トリムの検算に `outPoint` の読み戻しを使わない（**伸ばしても伸びない**）。尺は `end − start`。
    **★in/out が素材尺を超えていないか投入前に ffprobe で確かめる。**
    超えるとエラーもクランプもなく**超過分に完全な黒＋無音が焼き込まれ、機械検算もPASSする**。
    横断原則は `_video-core/PRINCIPLES.md` §16。

---

## 0-0. 前提（これが無いと動かない）

| 要るもの | 用途 | 無いとどうなるか |
|---|---|---|
| **Premiere Pro**（26系で実測） | 編集・配置 | — |
| **MCP Bridge (CEP) パネル** | Premiereへスクリプトを投げる | `pr.sh` が全部45秒でタイムアウト。**毎セッション手動で Start Bridge** |
| **After Effects**（26系で実測） | **テンプレを作る／文字幅を測る** | 既存の `.mogrt` を使うだけなら**不要** |
| **Adobe Media Encoder** | 書き出し | `encodeSequence` が使えない |
| **ffmpeg** | 書き出したファイルの画素比較 | `ssim_check.sh` が使えない（検証が主観になる） |
| **Python 3** | 付属スクリプト | — |

★アプリ名・プリセットのパスは**2026版で決め打ち**している箇所がある。
バージョンが違う場合は `AE_APP` 環境変数（`ae.sh`）と
`TELOP-WORKFLOW.md §5` のプリセットパスを読み替える。

★**書体は環境依存。** 未インストールのフォントは**AEもPremiereも警告なしに代替する**。
`assets/telop_3slot_v20.mogrt` はフォント編集が解禁済みなので、
**その環境に実在する PostScript 名**を指定すればよい。

## 0-1. すぐ使いたいなら

**AEもテンプレ作成も不要。** `assets/telop_3slot_v20.mogrt` を Premiere に読み込むだけで、
本文＋33項目（書体・サイズ・色・縁・グロー・出現アニメ・強調3スロット）が使える。
配置とパラメータ投入は `templates/pr_place_mogrt.jsx` が定型を持っている。
→ `assets/README.md`

## 0. 結論（これだけ守れば動く）

| | やること |
|---|---|
| 接続 | Premiere で `MCP Bridge (CEP)` パネル → Save Configuration → **Start Bridge**（毎セッション手動） |
| 投げ方 | `.jsx` に書いて **`bash pr.sh <script.jsx> [timeoutMs]`** |
| `.jsx` の書き方 | **末尾は `return <式>;`**（ドライバが関数に包む。**素の `return` は構文エラー**） |
| 結果の受け取り | **.jsx 内からファイルへ書き出し**、Bash で読む（版番号を毎回変える） |
| 使わない | `mcp__premiere-pro__execute_extendscript`（**戻り値を返さない**） |
| 対象の固定 | **`documentID` ＋ `path` の2点**（`documentID` は**コピーで重複する**・`app.project` は「今アクティブなもの」しか返さない） |
| 開く前に | `list_projects.jsx` で **`documentID` の重複を確認**（重複したまま作業すると本番を編集する） |
| 絶対にやらない | **`.prproj` のコピーを開く**（シーケンスが合流して汚染される・アンドゥも効かない） |
| 複数本 | 編集は並行・**Premiereへの投入は直列キュー**（`prq.py`）・書き出しは**AMEキュー** |
| 素材の入れ方 | **★切らずにトリム**。元素材を取り込み `setInPoint`/`setOutPoint`（**2引数・mediaType必須**）を打ってから置く。切り出しファイルを作らない（14条・§3-1） |
| 配置 | **`overwriteClip`**（`insertClip` は後続を押し出す） |
| クリップ有効無効 | **`clip.disabled`**（読み書き両方できる。`isDisabled()` は存在しない） |
| キーフレーム | 時刻は **`clip.inPoint.seconds` 基準**（静止画は約3600秒） |
| テキスト生成 | ネイティブGraphicは**作れない**。**MOGRT一択**（AE製のみ・`getMGTComponent()` が null でないこと） |
| 検証 | **書き出した実ファイルの画素/波形**で測る |

### この文書の地図

**★テロップを作る仕事なら、まず `references/TELOP-WORKFLOW.md` を読む。**
準備→テンプレ生成→配置→検証→書き出し→記録 の通し手順がそこにある。

- **§1 接続** — つなぐ。ここが通らないと何も始まらない
- **§2 並列** — 複数本を同時に進める。詳細な設計根拠は `references/PARALLEL-OPS.md`
- **§3 編集** — 何がどこまでできるか。全数マトリクスは `references/EDITING-MATRIX.md`
- **§4 検証** — 完了と言ってよい条件
- **テキストを作りたいなら** `references/MOGRT.md`（ネイティブGraphicは生成不可）
- **★書体を可変にしたいなら** `scripts/mogrt_enable_font_edit.py`
  （`.mogrt` の `capPropFontEdit` を立てれば**任意の書体を指定できる**。焼き込み不要）
- **MOGRTを自分で作りたいなら** `references/AE-MOGRT-BUILD.md`
  （AEはAppleScriptで直接叩ける＝**ブリッジ不要**。`scripts/ae.sh`）
- **UIでの操作をスクリプトに置き換えたいなら** `references/UI-EQUIV.md`
  （マスク・エフェクト順序・プリセット・調整レイヤーは**スクリプト不可**）
- **検証のやり方は** `references/VERIFY-METHOD.md`
  （書き出さずに測る／ffmpegで判定する／**対照実験を必ず置く**／測定器の盲点／診断物の作り方）
- **できる・できないの判断は** `references/DESIGN-BOUNDARY.md`
  （**クリップ全体か文字の中か**が分かれ目。原理的に無理なもの一覧）
- 罠の一覧は `references/API-TRAPS.md`

---

# §1. 接続

MCPサーバ(node)は自動起動するが、**Premiere側のブリッジは手動で開始が必要**。
パネルを開いただけでは動かない。これを飛ばすと**全ツールが45秒でタイムアウト**する。

1. Premiere Pro を起動
2. `ウィンドウ > 拡張機能 > MCP Bridge (CEP)` を開く
3. Temp Directory が `/tmp/premiere-mcp-bridge` か確認
4. **Save Configuration** をクリック
5. **Start Bridge** をクリック
6. `bash scripts/prcheck.sh` で1往復して確認する

### 未起動時の症状と見分け方

- 症状: `ping` を含む全ツールが `ExtendScript execution timed out after 45000ms`
- 見分け1: `/tmp/premiere-mcp-bridge/` に **未消費の `command-*.json` が溜まっている**
  （ブリッジが読んでいない＝Start Bridge が落ちている。実際に2件溜まって止まった）
- 見分け2: `response-*.json` の最終更新が古い
- 見分け3: `~/Library/Logs/CSXS/CEPHtmlEngine12-PPRO-*-com.mcp.premiere.cepbridge.panel.log` が古い
- **`/tmp` はOS再起動で消える**。再起動後は temp dir 再作成 → Save → Start をやり直す
- 詰まったらパネルの **Run Diagnostics** → `premiere-mcp-diagnostics-latest.json` を読む

### 同時に立てない

CEPブリッジは **使うMCPに対応する1つだけ Start する**（hetpatel と kavy を同時に立てない）。
導入済み3系統（いずれもuserスコープ）:

1. **premiere-pro**（本命・hetpatel-11/Adobe_Premiere_Pro_MCP・278ツール）
   `~/Documents/premiere-pro-mcp-hetpatel/dist/index.js` / temp=`/tmp/premiere-mcp-bridge`
   CEP拡張=`~/Library/Application Support/Adobe/CEP/extensions/MCPBridgeCEP` / パネル=**MCP Bridge (CEP)**
2. **premiere-pro-kavy**（次点・leancoderkavy/premiere-pro-mcp・269ツール）
   temp=`/tmp/premiere-mcp-bridge-kavy` / CEP拡張=`MCPBridgeCEP-Kavy`(symlink) / パネル=**MCP Bridge**
   ★kavyの `install-cep.sh` は素だと hetpatel 版を `rm -rf` で上書きするため別名にしてある
3. **adb-premiere**（mikechambers/adb-mcp）— Premiere Beta 25.3+必須・UXPプラグイン導入が未完

拡張が出ない場合は `環境設定 > プラグイン > UXPプラグイン > 開発者モード` を有効化（要再起動）。
公式「Adobe for creativity」コネクタはクラウドAPI方式で**タイムライン操作不可**。

## 1-2. 投げ方

```bash
cd ~/.claude/skills/premiere-bridge-ops/scripts
bash pr.sh myscript.jsx 120000
```

`pr.sh` は `.jsx` を読んで `{"id","script","timeoutMs"}` を `<bridge dir>/command-<id>.json` に置き、
`response-<id>.json` が現れるまで1秒間隔で待って中身を出す。

- **cwd に注意**: 相対パスで呼ぶなら `pr.sh` のあるディレクトリに `cd` してから
- 別ブリッジは `PR_BRIDGE_DIR=/tmp/premiere-mcp-bridge-kavy bash pr.sh ...`
- 終了コード: `0`=応答あり / `1`=引数・環境の誤り / `2`=タイムアウト

### ★トップレベルの `return` は構文エラー（最初に踏む罠）

CEP はスクリプトを**そのまま `evalScript` に渡す**。関数に包んでくれない。

| スクリプト | 結果（実測） |
|---|---|
| `"plain-ok";` | `result: "plain-ok"` |
| `if (1) return "ret-ok";` | **`ExtendScript execution failed via CEP evalScript()`** |
| `(function(){ if (1) return "wrapped-ok"; })();` | `result: "wrapped-ok"` |

エラー文言は「host-side scripting failure or CEP compatibility issue」だけで、
**構文エラーだと分からない**。中断を `return "★中断: ..."` で書く流儀と正面衝突する。

**対処**: `pr.sh` と `prq.py` は既定で本体を `(function(){ ... })();` に包む。
包むと**末尾の裸の式は返らない**ので、`.jsx` の末尾は必ず **`return <式>;`**。
包みたくない使い捨て（末尾が裸の式）は `PR_WRAP=0 bash pr.sh ...`。

### 結果は必ずファイル経由で受け取る

```javascript
var fo = new File("/tmp/premiere-mcp-bridge/state_v3.txt");  // ★毎回新しい名前
fo.encoding = "UTF-8";
fo.open("w"); fo.write(out.join("\n")); fo.close();
return out.join(" | ");   // 短い要約だけ戻り値に載せる
```

- **同名ファイルを再利用すると前回の残骸を読む**。版番号を付けて毎回変える
- `evalScript` の戻り値は長いと切れる。全量はファイルへ
- `mcp__premiere-pro__execute_extendscript` は**戻り値を返さない**（常に `"undefined"`）。使わない

### タイムアウト＝失敗ではない

`create_sequence` が45秒でタイムアウトした後、シーケンスは実際に作られていた。
**失敗と決めつけて作り直す前に必ず現状を読み戻す**（二重作成・二重配置の原因）。

---

# §2. 並列で進める（編集は並行・書き出しは直列キュー）

## 2-1. 層を分けるという考え方

**ブリッジは構造的に直列**。パネルは250msごとに `isProcessing` を見て、偽のときだけ
ディレクトリを走査し、**最初に見つけた `command-*.json` を1件だけ**処理して `return` する。
**同時に2本の ExtendScript を走らせることは原理的にできない。**

だから並行化は「Premiereを同時に叩く」ではなく、**層を分けて**実現する。

| 層 | 何をするか | 並行度 |
|---|---|---|
| L1 準備 | 素材解析・ffmpeg・テロップPNG生成・box JSON・検品 | **真の並行**（Premiereを触らない） |
| L2 Premiere変更 | クリップ配置・差し替え・エフェクト・尺調整 | **直列**（1本のディスパッチャ経由） |
| L3 書き出し | AMEキューへ投入 | **直列**（AMEが順次消化） |

L2 の1ジョブは数秒で終わる。重い処理は全部 L1 と L3 にあるので、
**L2 が直列でもボトルネックにならない**。結果として N 本の動画が同時に進む。

## 2-2. 手順

### ① 対象の識別子を採る（起点）

```bash
bash pr.sh ../templates/list_projects.jsx
```

開いている全プロジェクトの `documentID` と全シーケンスの `sequenceID` が出る。
**以降の全ジョブにこれを渡す。** `app.project` は使わない（アクティブが変わると対象が変わる）。

`app.projects` が開いている全プロジェクトのコレクションで、`Project` のメソッド
（`importFiles` / `save` / `sequences` / `rootItem` …）は
**非アクティブなプロジェクトにも直接呼べる**。だからフロントに出す必要はない。
`app.projects[i]` の**並び順は開いた順ではない**（実測で最後に作ったものが `[0]` だった）。

### ★★★ documentID は「ユニークなUUID」ではない（2026-08-08 実害あり）

**`.prproj` をコピーすると `documentID` まで複製される。**
動画案件は `v1 / v2 / v3` と `.prproj` を複製するのが常態なので、**必ず衝突する**。

実際にクライアントの本番プロジェクトを `cp` してテスト用に開いたところ、
**両方が同じ `documentID` を持ち**、`documentID` だけで引くと
**本番の方が返りうる状態**になった（`prqResolveProject()` は最初の一致を返す）。

さらに悪いことに、**同じ `documentID` のプロジェクトを2つ開くと、
Premiere が両者を同一視してシーケンスが合流する**。
本番プロジェクトのシーケンスが **5本 → 10本**（元の5本＋コピー側5本、全部別ID）に増え、
コピーを閉じても**戻らなかった**。保存していれば原本が壊れていた。

**したがって**:

| やること | 理由 |
|---|---|
| 対象は **`documentID` ＋ `path` の2点**で特定する | `documentID` 単独では別プロジェクトを掴む |
| **一致が2件以上あったら黙って1件目を使わず中断する** | ここで止めないと本番を編集する |
| **同じ `documentID` のものを2つ開かない** | 開いた時点でシーケンスが合流する |
| 作業前に `list_projects.jsx` で**重複を検出する** | 起点で気づくため（重複時に★★★警告を出す） |

`prq.py` は `--proj-path` を受け取り、上記をプリアンブル側で強制する。
パスは **`list_projects.jsx` が出したものをそのまま貼る**。
★Premiere は日本語名を **NFD** で返す（ド = ト + U+3099）。こちらの入力は NFC のことが多い。
**「結合濁点を落として比較」は NFC 側が変わらないので効かない**（これで正しいパスを
中断させる誤検出を出した）。`prq.py` は **NFC/NFD 両形を渡して**どちらかに一致すればOKとする。

```bash
prq.py enqueue work/a.jsx \
  --doc-id "xxxxxxxx-…" \
  --proj-path "/Volumes/…/案件.prproj"
```

`--proj-path` を省くと警告が出る。スクリプト側は次の形で書く:

```javascript
var proj = prqResolveProject();
if (!proj) return prqWhy();     // 中断理由（重複・パス不一致・未オープン）を返す
```

**★まだ UI 依存が残るもの（ここを踏むと別プロジェクトを編集する）**:

| やってはいけない | 理由 | 代わりに |
|---|---|---|
| `app.project.activeSequence` | アクティブなシーケンスは**アプリ全体で1本**。別プロジェクトのものが返る | `sequenceID` で `project.sequences` から引く |
| `app.executeCommand(id)` | **26.3.2 には存在しない**（`typeof`=`undefined`）。Web上の解説は古い | オブジェクトのメソッドを使う（他に選択肢が無い） |
| QE の `qe.project` / `getActiveSequence()` | **アクティブ依存**。しかも両者が食い違うことがある | 対象と照合してから触る（§3-4 C） |

### ② ジョブを積む

```bash
prq.py enqueue work/a_place.jsx --doc-id "xxxx-...-a" --label A_place
prq.py enqueue work/b_place.jsx --doc-id "xxxx-...-b" --label B_place
prq.py enqueue work/a_fix.jsx   --doc-id "xxxx-...-a" --label A_fix
```

`--doc-id` を渡すと、スクリプト先頭に `prqResolveProject()` /
`prqFindSequence(proj, seqId)` が自動注入される。`.jsx` はそれを呼ぶだけでよい。

**投入時に落とすもの**: ブリッジの `validateScript` は
`require(` / `process.` / `eval(` / `new Function(` / `__dirname` / `__filename` /
`child_process` を含むスクリプトを問答無用で弾く。**コメント内でもアウト**で、
返るのは `Script validation failed` だけ。`prq.py enqueue` が事前に検出して中断する。

### ③ 1本のディスパッチャで流す

```bash
prq.py run       # 1件ずつ。投入順を保証する
prq.py status
```

**なぜ自前のキューが要るか**: パネルの走査は `fs.readdirSync()` 順で**時系列順ではない**。
12件まとめて置いて実測したら `n01 n10 n06 n07 n11 n04 n12 n08 n09 n05 n02 n03` の順で返った。
**投入順を守るには、ブリッジに置く command を常に1件だけ**にして順番はこちらで持つしかない。

**タイムアウトしたらキューを止める**。タイムアウトは失敗ではなく、Premiere側で処理が
続いている可能性がある。次を投げると**二重実行**になる。`prq.py run` は exit 2 で停止し、
ジョブを `running/` に残す。状態を読み戻してから再開すること。

### ④ 書き出しは AME キューへ投げる

`sequence.exportAsMediaDirect(...)` は**その場でレンダーする**。ExtendScript は同期なので
**レンダーが終わるまでブリッジ全体が塞がる**。並行運用では使わない。

```javascript
app.encoder.launchEncoder();                                  // 未起動なら起動
var jobID = app.encoder.encodeSequence(seq, OUT, EPR, 0, 0);  // 積んで即返る
app.encoder.startBatch();
```

`workArea`: `0`=シーケンス全体 / `1`=イン〜アウト / `2`=ワークエリア。
**実測で 0.45秒で jobID を返し**、AMEがエンコード中に別プロジェクトの編集ジョブが
0.46秒で通った。**AMEは別ソース同士を同時にエンコードしない**ので、
キューは自動的に直列になる（こちらで直列化する必要はない）。
テンプレは `templates/export_to_ame.jsx`。

### ⑤ 完了は AME のログで確かめる

`encodeSequence` が返す jobID は「**キューに積めた**」証拠であって「書き出せた」証拠ではない。
ExtendScript 側に完了通知は来ない。

```bash
ame_watch.py wait "/path/to/out.mp4" --timeout-sec 7200   # exit 0 = 成功
ame_watch.py list --last 5
```

ログは `~/Documents/Adobe/Adobe Media Encoder/<ver>/AMEEncodingLog.txt`。
**UTF-16LE**（`cat` すると化ける）。
★ログの「正常にエンコードされました」は **AMEが落ちなかった**という意味しかない。
中身は §4 のとおり**書き出した実ファイルの画素**で測る。

## 2-3. やらないこと

**1台のMacで並列レンダーはしない。** Premiere に `aerender` 相当の公式CLIは無い。
`open -n` での複数インスタンスはAdobe非サポートで、環境設定・メディアキャッシュDB・
Dynamic Link・GPU/ハードウェアエンコーダを共有して競合する。1台で2本回すと
**直列より遅くなることがある**。本当に並列が要るならマシンを分ける。

→ 設計根拠・ブリッジ実装の解析・AMEの制約の詳細は **`references/PARALLEL-OPS.md`**

---

# §3. 編集

## 3-0. 全スクリプトの冒頭に置く定型（`templates/guard.jsx`）

### なぜ要るか — `app.project` は「手前のプロジェクト」を返す

複数プロジェクトが開いているのは常態（実測で同時7本）。
ユーザーが参考動画のプロジェクトを開いて確認した直後、`app.project` がそちらを指しているのに
気づかず作業を続け、**参考プロジェクトのSEを削除して書き出し、納品名で保存**した。
その間の報告（「SEは1本」等）はすべてよそのプロジェクトの内容だった。

**返り値で中断する**のが要点（警告して続行では意味がない）。
照合は **プロジェクト名＋シーケンス名＋クリップ枚数の3点**。
並行運用では、これを `documentID` 照合に置き換える（§2-2 ①）。

### 日本語名は NFD で返る

Premiere が返す名前は NFD（ブ=12501,12441 / ザ=12469,12441）。素の `===` では一致しない。
`String.fromCharCode()` で組み立て、`charCodeAt` 配列で比較する。配列の作り方:

```bash
python3 -c 'import sys,unicodedata as u; print(",".join(str(ord(c)) for c in u.normalize("NFD", sys.argv[1])))' '案件名_確認用.prproj'
```

### トラック数を先に読む

```javascript
var NV = S.videoTracks.numTracks;   // シーケンスによって本数が違う（V0-V3 の4本だけのこともある）
```

`videoTracks[4]` を触ると `ExtendScript execution failed via CEP evalScript()`（実際に踏んだ）。

## 3-1. 配置・尺・削除の作法

### ★★★ 素材は切らずにトリムで入れる（絶対厳守14条・2026-08-13 実機確立）

**ffmpeg で `src_in`〜`src_out` を切り出した `c01.mp4` を作って置いてはいけない。**
元素材1本を取り込み、**イン点/アウト点だけを打って置く**。前後がハンドルとして残るので、
投入後に人が端を掴んで伸ばす・スリップするという**手直しの余地が保たれる**。
切り出し方式はこれが原理的に不可能で、「あと0.3秒前から」の一言で ffmpeg からやり直しになる。

```javascript
function T(sec) { var t = new Time(); t.seconds = sec; return t; }
function grid(sec) { return Math.round(sec * FPS) / FPS; }   // ★フレーム格子に乗せる

for (var k = 0; k < CUTS.length; k++) {
    var c = CUTS[k], item = items[k];
    // ★setInPoint / setOutPoint は「2引数」。mediaType を省くと Not Enough Parameters で落ちる
    item.setInPoint (T(grid(c.src_in )), 4);
    item.setOutPoint(T(grid(c.src_out)), 4);
    V.overwriteClip(item, T(grid(c.tl)));    // ★素材の in/out を尊重して置かれる
}
```

**実測（合成素材3カット＋実写4K素材3カットで実証・2026-08-13）**:

| 確かめたこと | 結果 |
|---|---|
| `overwriteClip` は素材の in/out を尊重するか | **する**。設計どおりのフレーム数で乗る |
| リンク音声はどうなるか | **同区間で自動的に付く**（A1側を別途置く必要がない） |
| 1フレーム過剰配置は起きるか | **フレーム格子に乗せれば起きない**（6カットとも厳密一致） |
| 置いた後に `clip.end` で伸ばせるか | **伸びる。元の out 点より先の実フレームが本当に出る** |

**検算の作法（ここを間違えると「効いていない」ことに気づけない）**:

- **`inPoint`/`outPoint` の読み戻しでトリムを検算してはいけない。**
  `clip.end` で伸ばしても `outPoint` は**元の値のまま**を返す（実測: tl 8-14＝6秒のクリップが
  `src=5.0-9.0`＝4秒を返した）。§3-3 のキーフレーム事故と同じ「読み戻しでは検出できない」型
- 尺は **`end − start`** で見る。最終判断は**書き出した実ファイルの画素**（§4）
- 実写素材は焼き込みTCが無いので、**書き出しフレーム vs 元素材の該当フレームを SSIM で突合**する。
  必ず**対照実験**を置く（「フリーズ仮説」「隣接フレーム」と比べる。実測でハンドル 0.951 に対し
  フリーズ 0.465・別素材 0.287 と明確に割れた）。±5F を1F刻みでスキャンして
  **0Fずれに単峰のピーク**が立てばフレーム厳密と言える

**★★★ 素材尺を超える in/out を打ってはいけない（黙って黒が焼き込まれる）**

60.0秒の素材に `in=55.0 / out=65.0` を打つと、**エラーにもクランプにもならず10秒のクリップが出来る**。
そして書き出すと **5.000秒ちょうどから末尾まで完全な黒（音声も -47.8dB の無音）**。
`setOutPoint` は成功し、読み戻しも `65.000` を返し、**配置の機械検算（クリップ数・`end−start`）も
PASS する**。「検算は全部通ったのに完成品の後半が真っ黒」がこれで起きる（2026-08-13 実測）。

**トリム範囲は生成の時点で ffprobe の実尺と突き合わせて落とす。**
`place_premiere.py` の `guard_range()` が `src_out > 実尺` / `src_in < 0` / `src_out <= src_in`
で中断する。手書きの jsx を投げるときも素材尺を確かめてから打つこと。

**ハンドルの限界を先に計算する**: 伸ばせるのは素材の実尺までで、
**`clip.start` に負の `Time` を代入するとスクリプトごと落ちる**（`ExtendScript execution failed`。
エラーにすらならない）。伸ばす前に残ハンドル量でクランプすること。

雛形は `templates/place_clip_trim.jsx`（cutlist をそのまま食える形）。
生成は `_video-core/pipeline/scripts/place_premiere.py`。

### その他の作法

- ★**カットはフレーム格子に乗せる**（2026-08-09 実測）。設計秒をそのまま `Time.seconds` に
  入れるとカット間に**サブフレームの隙間**ができる。フレーム数で計算してから秒に戻す
- ★**全トラックの終端を機械検算する**。1トラックだけ最終カットが 1F 短い穴は目視では
  絶対に見つからない。配置後に全トラックの `clips[last].end` を並べて比較する
- ★**`縦横比を固定`（AnchorToInPoint系プロパティ）の既定は false**。`スケール(高さ)` だけ
  動かすと縦に伸びるだけでズームにならない。true にしてから倍率を打つ
- ★**`app.newProject()` はダイアログで止まりスクリプトが返らないことがある**。
  タイムアウト≠失敗（プロジェクトとシーケンスは出来ていた）。**二度実行せず、まず読み戻す**
- **調整レイヤーはスクリプトから作れない**。同じ効果（ズーム/Lumetri）は各カットのクリップへ
  直接掛ければ絵は等価（テロップより下という重なり順が同じため）
- **縦型シーケンスはスクリプトで作れる**（従来「未調査」→ 2026-08-09 解消）:
  ```javascript
  var st = seq.getSettings();
  st.videoFrameWidth = 1080; st.videoFrameHeight = 1920;
  var t = new Time(); t.ticks = "8467200000"; st.videoFrameRate = t;   // 30fps
  st.videoPixelAspectRatio = "1:1";
  st.editingMode = "795454d9-d3c2-429d-9474-923ab13b7018";
  st.videoFieldType = 0;
  seq.setSettings(st);
  ```
- **配置は `overwriteClip`**。`insertClip` は挿入編集で後続を押し出す。
  insertClip で組んだら V1が31→35本、A2が27→61本、尺が68.78→94.80秒に膨らんだ
- 時刻は数値ではなく `Time` オブジェクト: `var t = new Time(); t.seconds = AT;`
- `overwriteClip` は**1フレーム長く置くことがある**（実例: 36.3363 と 36.3026 で 1F ずれた）。
  `clip.end` で詰める: `var e = new Time(); e.seconds = WANT_END; clip.end = e;`
- 削除は `cl.remove(false, false)`（ripple=false）。`ripple=true` は後続をずらす
- 開始秒で照合するときの許容は**1フレーム分以上**取る（60fpsで0.0167s）。
  0.01sにしたら44本中14本が照合できなかった。**並び順で対応付ける方が安全**
- QE の `getVideoTrackAt(n).numItems` は **Empty（空き）も数える**。
  `type === "Clip"` だけ集めてから添字を使う（実例: numItems=8 だが実クリップ4本）
- タイムコード→TL秒: `TL = h*3600 + m*60 + s + f/fps`（29.97系は `fps = 30000/1001`）
- **projectItem は名前ではなくパスで探す**。版が変わってもファイル名は同じで、
  名前で探すと**前の版で取り込んだ項目**を掴む（実際に旧版PNGが敷かれ「テロップが消えてる」）。
  `getMediaPath()` で照合する（`templates/place_clip.jsx` の `findByPath`）

## 3-2. クリップの有効/無効は `clip.disabled`

```javascript
var cl = S.videoTracks[2].clips[0];
cl.disabled;          // 読み → true / false
cl.disabled = true;   // ★書きもできる（2026-08-08 実機で確認）
```

`clip.isDisabled()` / QE `trackItem.isEnabled()` / `setEnabled()` は**すべて存在しない**
（`ReferenceError`）。`setEnabled()` が無いので「無効化はUIでしかできない」と思い込みがちだが、
**プロパティへの代入で書ける**。旧版を無効化して残す運用がスクリプトだけで完結する。

`track.isMuted()` は動くが**トラック単位のミュート**でクリップの無効化とは別物。
トラックが `muted=false` でも、その上のクリップが `disabled=true` は普通に起きる。
**片方を見て他方を判断してはいけない。**

`for (var k in cl)` で列挙できる TrackItem のプロパティ:
`components, disabled, duration, end, inPoint, matchName, mediaType, name, nodeId,
outPoint, parentTrackIndex, projectItem, start, type`

**なぜ重要か**: 旧版を消さず上のトラックに重ねて残す運用では同じ区間に複数版が積まれる。
無効化されているかを読めないと**書き出しで旧版が焼き込まれる**。
**書き出し前に全クリップの `disabled` を列挙する**（`templates/dump_state.jsx`）。

## 3-3. キーフレームは `inPoint` 基準（★最も見つけにくい事故）

`addKey(t)` / `setValueAtKey(t, v)` の `t` は **クリップの inPoint 基準の秒**。
**静止画クリップの inPoint は慣例で 3600秒（実測 3599.969秒）**。
0.0〜0.3秒に打つと可視範囲の3600秒手前に置かれ、レンダラーは最後のキーの値を保持し続ける。

```javascript
var OFF = clip.inPoint.seconds;
pr.addKey(OFF + t);
pr.setValueAtKey(OFF + t, v, true);
// 検算: Math.abs(pr.getKeys()[0].seconds - clip.inPoint.seconds) < 0.01
```

**実際の事故**: テロップ46枚にアニメーションとエフェクトを付け、APIで読み戻して80枚全数
「時刻も値も設計どおり」を確認しレンダーまで出したが、**完成MP4では全く効いていなかった**。

**なぜ読み戻しで気づけないか（本質）**: `getKeys()` も `getValueAtTime()` も
**自分が書いた座標系で返す**。書き込みと読み出しが同じ誤りを共有するので照合は必ず通る。
**同じAPIで書いて同じAPIで読む検算は、座標系の誤りを原理的に検出できない。**

**症状の見分け**: 「配置（クリップ・尺・音）は正しいのに、アニメーション/エフェクトだけ
効かない」→ 時間軸の基準（inPoint / シーケンス / ソース）を疑うのが最短。

その他:
- キーを打つ前に `setTimeVarying(false)` で一旦消す
- **`getKeys()` は time-varying でないとき `undefined`**。`getKeys().length` は落ちる
- 位置は**正規化座標**。中心 `[0.5, 0.5]`、±Npx は `0.5 + N/1080`（縦は `/1920`）
- `component.remove()` は**存在しない**。キーフレームだけ消すと方向ブラーの適用量が残り
  **常時ボケる**。QE の `TrackItem.removeEffects()` を使う
- **エフェクトは決め打ちで探さない。`qe.project.getVideoEffectList()` で全列挙する**
  （実測 **136種**。従来この文書には5つしか書いていなかった）
  - グロー系: **VR グロー / アルファグロー / エコーグロー / エッジグロー / ワンダーグロー**
  - ブラー系: VR ブラー / カメラブラー / ブラー (ガウス)(レガシ) / ブラー(滑らか) /
    エッジのぼかし / ピクセルモーションブラー / 指向性ブラー(レガシー) / ガウスぼかし
  - よく使うもの: プロセスアンプ / 方向ブラー / VR デジタルグリッチ / トランスフォーム
  - **テロップのソフトグローは「アルファグロー」が第一候補**（文字のアルファ外側に光が出る）。
    「芯（小半径×高gain）+ 広がり（大半径×低gain）」の二重掛けは**2つ重ねれば再現できる**
- **エフェクトはクリップ全体にかかる。** 「この単語だけ光らせる」はできない
  （単語単位でやるなら MOGRT + AEレンジセレクター・§3-5-2）
- エフェクトのプロパティ名は**決め打ちせず必ず列挙してから参照**
  （半角カナ登録「ｺﾝﾎﾟｼﾞｼｮﾝのｼｬｯﾀｰ角度を使用」、「スケール (高さ)/(幅)」分裂等）

## 3-4. どこまで非アクティブのままできるか（3階層）

複数本を並行で進めるとき、**ユーザーのフォーカスを奪うかどうか**で操作は3つに分かれる。
Premiere 26.3.2 で全数実測した（各操作の直前にフォーカスを戻して1件ずつ）。

**A. フォーカスを奪わずに通る** — ユーザーが別プロジェクトを触っていても邪魔しない

読み取り全般 / `overwriteClip` / `insertClip` / `clip.start=` / `clip.end=` /
`clip.disabled=` / `clip.name=` / `remove()` / マーカー一式 / `setInPoint` / `setOutPoint` /
`seq.name=` / `getSettings` / `exportAsFinalCutProXML` / **`sequence.clone()`**（★`createNewSequence` はダイアログで止まる・§3-1） /
`track.setMute` / 素材の `setScaleToFrameSize`・`setInPoint`・`setOutPoint`・`getMarkers` /
**キーフレーム一式**（`getValue`/`setValue`/`setTimeVarying`/`addKey`/`setValueAtKey`/`getValueAtKey`）/
ネスト（`seq.projectItem` を置く）/ 選択（`setSelected`/`getSelection`）/
`moveBin`・`deleteBin` / オーディオトラック一式 / `save()` / `encodeSequence()`

**固有エフェクト（モーション・不透明度）のキーフレームが全部ここに入る**のが大きい。
テロップのアニメーション・位置・スケールの作業は**非アクティブのまま完結する**。

**B. 通るがフォーカスを奪う** — セットアップ段でまとめる

`importFiles` / `createBin` / `createSubClip` / `createNewSequenceFromClips` /
`createSubsequence` / `clone` / `deleteSequence`

**「新しく作る」系が奪う**と覚えると外さない。
★**`createNewSequence` は引数に関係なくダイアログが開いて止まる**（2026-08-13 再訂正）。
  無人で作るなら **`sequence.clone()`**（奪わない）か `createNewSequenceFromClips`（奪う）。

**C. 対象をアクティブにしないとできない（QE依存）**

**QE はアクティブなプロジェクトしか見えない。** 実測で `qe.project.name` は対象ではなく
アクティブ側を返し、`getSequenceAt(i)` もアクティブ側しか列挙しなかった。
エフェクト追加・トランジション・`addTracks`・`razor`・`removeEffects` がここに入る。

**回避策**: `proj.openSequence(sequenceID)` が `true` を返し、
**プロジェクトとシーケンスの両方をアクティブにする**。その後 QE が追従する。

→ **運用**: エフェクト追加はセットアップ段に寄せ、以降の調整（キーフレーム・尺・有効無効）は
**Aの範囲で回す**。これがユーザーの操作を邪魔しない組み方。

→ 全数マトリクス・QEの詳細・プロジェクト間の移動は **`references/EDITING-MATRIX.md`**

## 3-5. できないこと

- **`app.executeCommand` は存在しない**（26.3.2 で `typeof` が `undefined`）。
  Web上には「メニューコマンドを叩ける」という解説があるが**このバージョンには無い**。
  UIのコピー&ペーストやメニュー操作は script から叩けない
- **アンドゥでスクリプトの変更は戻せない**。`qe.project.undo()` は呼べるが、
  直前に足したクリップは対象・アクティブ**どちらも戻らなかった**。
  **元に戻せない前提で作業する**（＝上書きせず新規版を作る運用がここでも効く）
- **ネイティブGraphic（テロップ）の本文は読み書きできない**。
  `projectItem` が null、`getMGTComponent()` も null、
  `ソーステキスト.getValue()` は本文ではなく**1文字の不透明値**（実測 charCode 580 / 過去記録 600。
  値は個体差があり、**「1文字しか返らない」ことが本質**）。
  **これは仕様**で、Adobe が Premiere 26.x のバグ報告に対し
  「That's correct behavior. The ExtendScript API is designed to work with .mogrts,
  created within After Effects.」と回答している（2026年4月）。UXP 26.x にも `setText()` は無い。
  **ただし本文以外（位置・スケール・不透明度・ベクトルモーション）は普通のコンポーネント**なので
  触れる（詳細は `references/EDITING-MATRIX.md` §F）。AE製MOGRTなら本文も変更可。
  **★ライブAPIで取れないだけで、`.prproj` を直接読めば本文・フォント名・フォントサイズは取れる**
  （`scripts/prproj_telop_dump.py`・Premiereを閉じてから実行）。
  参考動画の .prproj がある案件では書体特定を機械化できる。
  Premiere を閉じた状態で `.prproj` 内の Graphic バイナリを差し替える方法も
  実機で成功している（フォント差し替えのみ・本文は未検証）

## 3-5-2. テキストを「作りたい」なら MOGRT（唯一の道）

ネイティブグラフィックは**新規作成できず本文も触れない**（§3-5）。
**スクリプトからテキストを生成・制御する手段は MOGRT だけ。**

```javascript
var clip = sequence.importMGT(path, ticks, videoTrackOffset, audioTrackOffset);
```

実測でできたこと: **本文の差し替え / フォント変更 / サイズ変更 / 改行(`\n`) /
色（独立パラメータ） / 部分強調（複数ラン）**。

**★3つの落とし穴**（詳細は `references/MOGRT.md`）:

1. **AE製でないと使えない。** `getMGTComponent()` が `null` なら Premiere製で、
   挿入した瞬間に**ネイティブグラフィック化する**。Adobe同梱は大半が Premiere製
2. **フォント/サイズは AE側で有効化が必要。** `capPropFontEdit` は
   **キーがあっても値が false のことが多い**（同梱78個中、trueは14個だけ）
3. **★per-run配列は7つ全部の長さを揃える。** 1つでも揃えないと、
   `setValue` は成功し読み戻しも通るのに**UIで開いた瞬間にPremiereが落ちる**（実際に落とした）

**部分強調で文字が消えたら、幅を疑う。** ランではなくテキストボックスの溢れで、
**行頭から欠ける**（1文字だけ欠ける事例あり）。自前テンプレで幅を広く取れば起きない。

**ラン単位の色とグローはできない**（色は per-run に無く、エフェクトはクリップ全体）。
単語単位でやるなら **AEのレンジセレクター**を公開する。

**★MOGRT は自分で作れる。** AE は AppleScript で直接操作できる（**ブリッジ不要**）ので、
要件に合うテンプレートが無ければ生成する。`bash scripts/ae.sh work.jsx`。
1つの雛形から**書体・サイズ・色・グロー・フチ**を Premiere 側で変える設計は
`references/AE-MOGRT-BUILD.md`。要点だけ:

- **書体は式で切り替えられない**（式で組んだ TextDocument は描画されない）。
  値として焼き込んだレイヤーをドロップダウンで出し分ける
- **フチは「ソーステキスト」に含まれない。** テキスト**アニメーター > 線幅**を露出する。
  文字パネルの基準線幅が 0 だと、いくら動かしても出ない（加算のため）
- **フォントは `app.fonts.allFonts` で実在を確かめてから使う**（未インストールでも黙って代替される）
- **レイヤースタイルはスクリプトから有効化できない**（`canSetEnabled=false`）

## 3-5-3. UIでできてスクリプトでできないこと（4つだけ）

「クリップに直接エフェクトを付けて数値とキーフレームを動かす」範囲は
**UIとスクリプトで完全に等価**。等価でないのは次の4つ（すべて `typeof`=`undefined`）。

| できないこと | 回避策 |
|---|---|
| **マスク** | **マスクを使わない設計にする**。部分処理は別トラックに素材を重ねる |
| **エフェクトの順序変更** | **付ける順番を最初から正しくする**（追加した順に積まれるだけ） |
| **プリセット** | **レシピJSON＋適用スクリプト**を自前で持つ（実質これがプリセット） |
| **調整レイヤー** | QEの `newTransparentVideo` で代替できる可能性（未検証） |

**「属性をペースト」相当は自前で実装できる**（読んで書くだけ・プロジェクトを跨げる）。
実測でエフェクト2個/パラメータ37件のうち**34件が完全一致**、キーフレームも再現。
**色だけはパック整数で再現できない**。詳細は `references/UI-EQUIV.md`。

## 3-6. プロジェクトファイルの取り扱い（★事故が集中する場所）

- **同じ `.prproj` を2重に開いたまま片方を保存すると、もう片方の古い内容で上書きされ作業が消える**
  （実際に17の作業が消えた）
- **`.prproj` のコピーを開いてはいけない。** コピーは `documentID` まで複製するので、
  開いた瞬間に Premiere が両者を同一視し、**シーケンスが合流して汚染される**
  （実測: 本番 5本 → 10本。コピーを閉じても戻らない）。保存すれば原本が壊れる
- **アンドゥは効かない**（§3-5）。だから壊してから気づいても戻せない
- 作業前に必ず `list_projects.jsx` を流す。**`documentID` の重複を★★★で警告する**

### 汚染してしまったときの復旧

原本ファイルは `save()` を呼ばない限り無傷（ディスク上の md5 とタイムスタンプで確認できる）。

1. 対象プロジェクトを **「保存せずに」閉じる**（`Cmd+S` を押さない）
2. 元のパスから開き直す
3. `list_projects.jsx` でシーケンス本数が元に戻ったか確認する

**自動保存フォルダ（`Adobe Premiere Pro Auto-Save/`）には汚染後の状態が書かれている**ので、
そこから復元するときは汚染前のタイムスタンプのものを選ぶこと。

---

# §4. 検証は「書き出した実ファイルの画素」で行う

**①スクリプトの戻り値 ②アプリからの読み戻し だけで「適用済み」と報告してはならない。**
③書き出した実ファイルを画素/波形で測るまで完了と言わない（§3-3 がその理由）。

- 書き出しプリセット「Mobile Device 1080p HD」は**1920×1080の横向きに強制する**。
  縦型は **「Match Source - High bitrate」**（`.../MediaIO/systempresets/4E49434B_48323634/`）
- 音声の変更検証は**変更前後のMP4の音声差分**が確実（差分＝消えた音そのものが出る）
- タイムラインへ差し込むMP4は**元素材とメタデータを揃える**
  （フレームレートと timescale が違うと尺がずれる）:
  ```bash
  ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate,time_base -of default=nw=1 src.mp4
  ffmpeg -v error -y -r <r_frame_rate> -i in.mp4 -c:v copy -video_track_timescale <1/time_base> out.mp4
  ```

**実例（この方式で実際に確かめた）**: 非アクティブなプロジェクトで V2 にクリップを置き、
`clip.end` で 4.5秒に詰めてから書き出し、画素を測ったら
`t=0.5s → ff1900`(赤/V0) `t=2.5s → 0010ff`(青/置いたもの) `t=4.9s → ff1900`(尺詰めが効いている)。
**API の戻り値ではなく画素で「効いている」ことを確認した。**

---

# §5. 同梱ファイル

| パス | 用途 |
|---|---|
| `scripts/pr.sh` | `.jsx` をブリッジへ投げる。`PR_BRIDGE_DIR`/`PR_PYTHON`/`PR_WRAP` |
| `scripts/prcheck.sh` | 作業前の生存確認。未消費コマンド件数＋実際に1往復 |
| `scripts/wait_render.sh` | **書き出し完了を待つ**。★**拡張子はプリセットのコンテナに上書きされる**（`.mp4`指定でも`.mov`）ので吸収する |
| `scripts/ssim_check.sh` | **書き出した2本を画素で比べる**。`ffmpeg` の ssim/psnr を判定文つきで出す |
| `scripts/mogrt_enable_font_edit.py` | **`.mogrt` のフォント編集を解禁**する。zip内 `definition.json` の `capPropFontEdit` 等を立てる。**AEにAPIが無いのでこれが唯一の道**。これで書体を焼き込む必要が無くなる |
| **`scripts/mogrt_scrub.py`** | **`.mogrt` から作者マシンの絶対パスを消す（配布前の必須処理）**。AEは同梱サムネ `thumb.mp4` のXMPに生成元 `.aep` のフルパスを残す。`distcheck` はテキストしか見ないので**素通りする**。mp4のボックス長を壊さないよう**同じバイト長の中立文字列で埋める** |
| `scripts/ae.sh` | **AE に `.jsx` を投げる**（AppleScript直・ブリッジ不要）。`log()` 注入・ダイアログ抑止・改行正規化 |
| `scripts/aecheck.sh` | AE の生存確認。**`get version` は当てにならない**ので実際にファイルを書かせて判定 |
| `scripts/prq.py` | **直列ジョブキュー**。投入順保証・`documentID` 注入・禁止語の事前検出・タイムアウトで停止 |
| `scripts/ame_watch.py` | **書き出し完了の実測**。AMEログ(UTF-16LE)を解析して待つ |
| `scripts/prproj_telop_dump.py` | **`.prproj` からテロップ様式を抽出**（本文・フォント名・サイズ）。APIで取れないものが取れる。読み取り専用・**Premiereを閉じてから** |
| `templates/list_projects.jsx` | 全 `documentID` と全 `sequenceID` を採る。**並行運用の起点** |
| `templates/guard.jsx` | 3点照合の定型（NFD比較つき） |
| `templates/dump_state.jsx` | 全トラック＋`disabled` のダンプ。**書き出し前に必ず** |
| `templates/place_clip.jsx` | 取り込み→`overwriteClip`→尺詰め→読み戻し |
| `templates/export_to_ame.jsx` | シーケンスをAMEキューへ投入（非ブロッキング） |
| `templates/ae_build_telop_mogrt.jsx` | **AE用**。本文/書体/サイズ/文字色/縁の太さ/縁の色/グローを Premiereから変えられるテロップMOGRTを作る雛形。`bash scripts/ae.sh` で投げる |
| `templates/pr_place_mogrt.jsx` | **Premiere用**。MOGRTを置いてパラメータを流し込む定型。ticksの文字列渡し・3点照合・ドロップダウンの−1・**本文の配列長の検算**・モーション位置まで畳み込み済み |
| `templates/ae_measure_text.jsx` | **AE用**。AEを**文字幅の計算機**として使う。1行を複数クリップに分けて横に並べるときの配置座標を出す（両端合わせ・正規化位置まで計算）。SSIM 0.9997 で再現を実証済み |
| **`templates/ae_build_telop_mogrt_v7.jsx`** | **AE用・統合版（v25）**。v24の影/下地/重心アンカー＋v22の強調3スロット＋**文字色グラデ（2色）**＋**文字間隔**。本文＋69項目。グラデはテキストをアルファマットにしてグラデソリッドを抜く方式（マットは本文の複製・影とフチは外す）。グラデと強調色は排他。効き0で単色に戻る |
| **`templates/ae_build_telop_mogrt_v8.jsx`** | **AE用・4色グラデ版（v26）**。v25 の2色グラデを `ADBE 4ColorGradient`（4点×4色を自由配置）に差し替え。本文＋78項目。**5色以上の多段ストップは原理的に不可** |
| `templates/ae_build_telop_mogrt_v4.jsx` | **AE用・現行の推奨版**。v3のカラーピッカーを全廃し、色を**0〜100の数値スライダー3本**で持つ。本文＋49項目 |
| `templates/ae_build_telop_mogrt_v3.jsx` | **AE用・現行の推奨版**。テキストレイヤー1枚で、書体はPremiereから任意指定（`mogrt_enable_font_edit.py` を通す前提）。強調3スロット独立。本文＋33項目（強調は色/大きさ/縁の色/縁の太さ/縦オフセット）。v2の5レイヤー・式75件に対し**1レイヤー・式31件** |
| `templates/ae_build_telop_mogrt_v2.jsx` | **AE用**。上記に**出現アニメ5種**（なし/フェード/ポップ/下からスライド/タイプライター）、**部分強調**（何文字目から何文字目・色・大きさ）、**強調モーション**（なし/後から跳ねる/後から色が乗る/跳ねて色も乗る・遅れ）を足した版。計16項目 |
| `templates/probe_focus.jsx` | ある操作が非アクティブで通るか／フォーカスを奪うかの**測定器** |
| `references/PARALLEL-OPS.md` | 並列運用の設計根拠（ブリッジ実装の解析・AMEの制約・キュー詳細） |
| `references/EDITING-MATRIX.md` | 編集操作の全数マトリクス・QE・プロジェクト間の移動 |
| `references/UI-EQUIV.md` | **UI操作↔スクリプトの対応表**。現行パネル構成(25.0でプロパティへ移動)・できない4つ(マスク/順序/プリセット/調整レイヤー)と回避策・エフェクト複製の実装・実測した演出レシピ |
| `references/MOGRT.md` | **MOGRT の全知見**。挿入・本文/書体/サイズ/色の変更・部分強調（複数ラン）・配列長を揃えないと落ちる・欠けは幅が原因・レンジセレクター設計 |
| `references/AE-MOGRT-BUILD.md` | **AE側でMOGRTを作る全知見**。AE接続6つの罠・EGPに出せる型と「範囲を編集」・書体切替の設計・フチはアニメーター線幅・フォント実在確認・参照が無効化される2操作 |
| **`assets/telop_v25_fontedit.mogrt`** | **★グラデ／文字間隔が要るならこれ**。本文＋69項目（v24の影・下地＋強調3スロット＋2色グラデ＋文字間隔）。フォント編集解禁済み |
| `assets/telop_v26_fontedit.mogrt` | 上記の**4色グラデ版**。本文＋78項目。2色で出せない虹系・ネオン系のとき |
| **`assets/telop_3slot_v22.mogrt`** | **★強調スロット中心ならこれ。すぐ使えるMOGRT本体**。本文＋49項目・1レイヤー・フォント編集解禁済み・**色も0〜100の数値で指定できる**（スクリプト運用向け） |
| `assets/telop_3slot_v20.mogrt` | 同上の**カラーピッカー版**（本文＋33項目）。**人がUIで色を選ぶ**運用向け。色はスクリプトから設定できない |
| `assets/telop_fontbaked_v14.mogrt` | 書体5種を焼き込んだ版（本文＋8項目）。人がUIで書体を選ぶ運用向け |
| `assets/README.md` | 同梱MOGRTの項目一覧と使うときの注意 |
| `references/TELOP-WORKFLOW.md` | **★テロップ制作の通し手順**。準備→テンプレ生成→配置→検証→書き出し→記録。**この工程での絶対厳守12条**つき |
| `references/VERIFY-METHOD.md` | **★検証の工程**。`sourceRectAtTime` で書き出さずに測る／ffmpegのSSIM・PSNR／**対照実験**／**測定器の盲点**／診断物で1回で決着させる／ユーザーへの渡し方 |
| `references/DESIGN-BOUNDARY.md` | **★設計の境界線**。クリップ全体か文字の中か／**原理的に無理なもの一覧**／テンプレ項目の設計原則／迷ったときの早見表 |
| `references/API-TRAPS.md` | 実在しないAPI／挙動が直感と違うAPIの一覧 |

# §6. 関連

- `~/.claude/skills/_video-core/PRINCIPLES.md` §12
- memory `reference_premiere_mcp_setup.md` / `reference_premiere_script_safety.md`
  / `reference_premiere_clip_name_cache.md` / `reference_telop_emphasis_codisplay.md`
  / `reference_premiere_native_text_impossible.md`
