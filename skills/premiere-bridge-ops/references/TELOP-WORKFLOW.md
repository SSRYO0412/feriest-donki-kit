# テロップ制作の通し手順（MOGRT運用の実務書）

**このファイルだけ読めば、テンプレの生成から納品用の配置まで一通り回せる**ように書いた。
個々のAPIの詳細は `MOGRT.md` / `AE-MOGRT-BUILD.md` / `API-TRAPS.md` を参照。
検証のやり方は `VERIFY-METHOD.md`、何ができて何ができないかの判断は `DESIGN-BOUNDARY.md`。

すべて **Premiere 26.3.2 / After Effects 26.3x87 / macOS** の実機実測（2026-08-08〜09）。

---

## ★★★ この工程での絶対厳守（違反したら作業をやり直す）

1. **①スクリプトの戻り値 ②アプリからの読み戻し だけで「できた」と報告しない。**
   **③書き出した実ファイルの画素で測るまで完了と言わない。**
   同じAPIで書いて同じAPIで読む検算は、座標系や単位の誤りを**原理的に検出できない**。
2. **絵の最終判断はユーザーがする。** こちらは機械検算まで通し、
   **どこを見るか・その結果でどう分岐するかを添えて渡して止まる。**
3. **`.mogrt` を書き出したら必ず `scripts/mogrt_enable_font_edit.py` を通す。**
   通さないと Premiere から書体もサイズも変えられない。
4. **本文（`textEditValue`）を変えたら `fontTextRunLength` を文字数に合わせる。**
   揃えないと `setValue` は成功し読み戻しも通るのに、**UIで開いた瞬間に Premiere が落ちる。**
5. **対象プロジェクトは `documentID` で固定し、名前と3点照合してから触る。**
   実案件のプロジェクトが同時に開いていても**絶対に触らない**。
6. **上書きしない。** テンプレも `.aep` も `.mogrt` も**v番号を上げて新規に作り、却下版も残す**。
7. **露出項目は後から増やせない。** 増やすと**配置済みクリップの差し替え**になる。
   設計時にドロップダウンへ「なし」を入れ、余裕を持たせる。
8. **テキストアニメーターの数値プロパティは「加算」される。** スロット側は**追加分だけ**返す。
9. **ドロップダウンは Premiere が0始まり・AEが1始まり。** スクリプトからは `AEの値 − 1` を渡す。
10. **色はスクリプトから設定できない。** 色はテンプレ側の既定値として焼くか、人がUIで触る。
11. **「効いていない」と思ったら、まず背景色と測定器を疑う。** レンダラーの非互換を疑うのはその後。
12. **作ったスクリプト・テンプレは台帳の `revision_record_db` に1行記録する**（`§7`）。

---

## 1. 準備

```bash
bash scripts/prcheck.sh     # Premiere: ブリッジが生きているか（未消費コマンド件数＋1往復）
bash scripts/aecheck.sh     # AE: スクリプトが実行できるか（ファイルを書けるかで判定）
```

★AEの `get version` は**ダイアログが開いていても応答する**ので生存確認に使えない。
★Premiere側は **Start Bridge が毎セッション手動**。押し忘れると全部45秒でタイムアウトする。

**対象プロジェクトを固定する。** 実案件が同時に開いていることが普通にあるので、必ず列挙してから選ぶ。

```javascript
for (var i=0;i<app.projects.numProjects;i++){
  var p=app.projects[i];
  log("["+i+"] "+p.name+"  docID="+p.documentID+"  path="+(p.path||"(未保存)"));
}
```

以降のスクリプトは冒頭で必ずこれを通す（`templates/guard.jsx` と同じ考え方）:

```javascript
var DOC="<documentID>", proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
if(!proj || proj.name.indexOf("<想定する名前>")!==0){ log("★中断"); flush(); }
```

★**`documentID` はユニークなUUIDではない。** `.prproj` をコピーすると複製される。
同じIDが2つ見つかったら**中断**する（過去にこれで実案件のシーケンスが5→10に増えて汚染した）。

★**結果は必ずファイル経由で受け取る。** ブリッジは戻り値を返さない（`"result":"undefined"` になる）。

```javascript
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
```

---

## 2. テンプレートを用意する

### 2-0. ★作らずに済ませる（通常はこれ）

**`assets/telop_3slot_v20.mogrt` が完成品として同梱してある。**
フォント編集は解禁済みなので、**AEを起動する必要すら無い**。
項目一覧と注意は `assets/README.md`。§3 の配置へ進んでよい。

**AEが要るのは次の2つの場合だけ**:
- テンプレの**構造**を変えたい（項目を増やす・スロット数を変える・出現の型を足す）
- **文字幅を測りたい**（1行を複数クリップに分けて横に並べるとき・§3-6）

### 2-1. 既存の雛形を使う

`templates/ae_build_telop_mogrt_v3.jsx` が現行の推奨版。**テキストレイヤー1枚**で、
Premiere から **本文＋33項目**を操作できる。

| 分類 | 項目 |
|---|---|
| 文字 | 本文（＋**書体・サイズ**はJSON経由） |
| 配置 | 縦位置 |
| 見た目 | 文字の色 / 縁の太さ / 縁の色 / グローの強さ / グローの種類 |
| 出現 | 出現の型（なし・フェード・ポップ・下からスライド・タイプライター）/ 出現の尺 |
| 強調 | 強調の出方（なし・後から跳ねる・後から色が乗る・跳ねて色も乗る） |
| 強調×3 | 開始 / 終わり / 色 / 大きさ / 遅れ / 縁の色 / 縁の太さ / 縦オフセット |

### 2-2. 新しく作る（案件で書体や項目を変えたいとき）

**4段の手順。どれも飛ばさない。**

```bash
# ① AEで生成（雛形の冒頭の定数を書き換えてから）
bash scripts/ae.sh /tmp/build_v21.jsx 240

# ② AE内で機械検算（VERIFY-METHOD.md §1）
bash scripts/ae.sh /tmp/verify_v21.jsx 200

# ③ ★フォント編集を解禁（これを忘れると書体もサイズも変えられない）
python3 scripts/mogrt_enable_font_edit.py 出力.mogrt 出力_fontedit.mogrt

# ④ Premiereに配置して確認（§3）
```

設計上の注意は `AE-MOGRT-BUILD.md`。特に、
**`td.applyStroke = true` が無いと縁がまったく効かない**／
**スクリプトで足したアニメーターはセレクターが空**／
**式で組んだ TextDocument は描画されない**／
**フォントは `app.fonts.allFonts` で実在確認してから使う**（未インストールは黙って代替される）。

---

## 3. Premiere に配置する

### 3-1. シーケンスを用意する

```javascript
proj.createNewSequence("名前", "任意のID");   // ★既定プリセット = 1920x1080 / 23.976fps
proj.openSequence(seq.sequenceID);             // プロジェクトとシーケンスを同時にアクティブ化
```

★★★**第2引数を空文字列 `""` にしてはいけない。**「新規シーケンス」ダイアログが開き、
**人が OK を押すまでスクリプトが返らない**（2026-08-13 実測。無人で回すと必ずタイムアウトする）。
ここに「任意のID」と書いてあるのが正しい。中身は見ていないので何でもよい。

★**縦型（1080x1920）はスクリプトで作れる**（2026-08-09 解消・2026-08-13 に無人化まで確認）。
プリセットのパスを渡しても**内容は反映されない**（何を渡しても 1920x1080/23.976）ので、
**作ってから `setSettings` で上書きする**のが唯一の道。

```javascript
proj.createNewSequence(name, "vops");         // ★空文字列にしない
var st = seq.getSettings();
st.videoFrameWidth = 1080; st.videoFrameHeight = 1920;
var tk = new Time(); tk.ticks = "8467200000"; st.videoFrameRate = tk;   // 30fps
st.videoPixelAspectRatio = "1:1";
st.editingMode = "795454d9-d3c2-429d-9474-923ab13b7018";
st.videoFieldType = 0;
seq.setSettings(st);                           // 実測: 1080x1920 / ticks=8467200000 / V=3 A=4
```

### 3-2. 背景を敷く（検証用）

**黒背景に黒フチのテロップを置くと、正しく出ていても見えない。** 必ず敷く。

```bash
ffmpeg -y -f lavfi -i color=c=0x4A4A52:s=1920x1080 -frames:v 1 bg_gray.png -loglevel error
```

```javascript
proj.importFiles([BG], true, proj.getInsertionBin(), false);
```

★**`importFiles` は非同期。** 呼んだ直後に `rootItem.children` を探しても**見つからない**。
**別のスクリプト実行に分ける**か、見つからなければ次回に回す作りにする。

```javascript
for(var t=0;t<20;t+=5) seq.videoTracks[0].overwriteClip(bgItem, String(Math.round(t*TPS)));
```

### 3-3. MOGRTを置く

```javascript
var TPS = 254016000000;
var clip = seq.importMGT(path, String(Math.round(sec*TPS)), videoTrackIndex, audioTrackIndex);
```

★**第2引数の ticks は「文字列」で渡す。** 数値だと時刻が効かず、**全部0秒に入る**（実際に踏んだ）。
★掃除は `clip.remove(false, false)` を後ろから回す。

### 3-4. パラメータを入れる

```javascript
function param(clip,nm){ var m=clip.getMGTComponent();
  for(var k=0;k<m.properties.numItems;k++) if(m.properties[k].displayName===nm) return m.properties[k];
  return null; }
```

| 種類 | 入れ方 |
|---|---|
| 数値 | `p.setValue(値, true)` そのまま |
| **ドロップダウン** | **`AEの値 − 1`** を渡す（Premiereは0始まり） |
| **色** | **設定できない**。64bitで読めるが `setValue` は32bitに丸める。テンプレ側の既定値で持つ |
| **本文・書体・サイズ** | JSON文字列を書き換える（下記） |

```javascript
var v = p.getValue();
p.setValue(
  v.replace(/"textEditValue":"[^"]*"/, '"textEditValue":"'+txt+'"')
   .replace(/"fontTextRunLength":\[[^\]]*\]/, '"fontTextRunLength":['+txt.length+']')   // ★必須
   .replace(/"capPropDefault":"[^"]*"/, '"capPropDefault":"'+txt+'"')
   .replace(/("fontEditValue":\[)"[^"]*"(\])/, '$1"'+postScript名+'"$2')
   .replace(/("fontSizeEditValue":\[)[^\]]*(\])/, '$1'+サイズ+'$2'), true);
```

**入れたあと必ず読み返して、配列長が文字数と一致しているか検算する。**

### 3-5. 位置を動かす（モーション）

★**MOGRT のコンプはフレーム中央に「等倍」で置かれる（縮尺されない）。**
コンプ1080幅・フレーム1920幅なら **コンプpx = フレームpx**、水平オフセットは `+420`。

```javascript
for (var q=0;q<clip.components.numItems;q++){ var cp=clip.components[q];
  for (var r=0;r<cp.properties.numItems;r++){ var pr=cp.properties[r];
    // ★「グラフィックパラメーター」側にも「位置」があるので取り違えない
    if (pr.displayName==="位置" && cp.displayName==="モーション") pr.setValue([x,0.5],true); } }
```

位置は**正規化**（0〜1）。`x = (フレーム幅/2 + ずらす量) / フレーム幅`。

### 3-6. 1行を複数クリップに分ける（文字単位のグローなどが要るとき）

グローはレイヤーに掛かるので**一部の文字だけ光らせることはテンプレ内ではできない**。
行を分けて別クリップにすれば解決する（書体・サイズ・出現タイミングも独立する）。

```bash
bash scripts/ae.sh templates/ae_measure_text.jsx 120   # PARTS を書き換えて実行
```

★**単純に幅を足してはいけない。** 実測（見出しゴシック120px）:
「これは」330.37 ＋「グローです」543.01 ＝ 873.38 に対し、
**連結「これはグローです」は 879.83**（6.45px 広い）。足し算だと字間が詰まる。
**両端合わせ**（左パーツを連結時の左端に、右パーツを右端に合わせる）にすると、
内側の隙間が自動的に自然な字間になる。

**実証**: 分割2クリップ vs 1クリップ **SSIM 0.999722**（わざと20pxずらした対照は 0.987369）。

### 3-7. 頭出し

```javascript
seq.setPlayerPosition("0");
```

---

## 4. 検証する

`VERIFY-METHOD.md` に従う。**最低限、次の3つは毎回やる。**

1. **AE内の機械検算** — 式のエラー0件／狙った変化が実寸に出るか
2. **書き出した実ファイルの比較** — 変えた前後で SSIM/PSNR が動くか（**対照も一緒に測る**）
3. **ユーザーに絵を見てもらう** — 見る場所と分岐を添えて渡す

---

## 5. 書き出す

```javascript
var PRESET="/Applications/Adobe Media Encoder 2026/Adobe Media Encoder 2026.app/Contents/"
         + "MediaIO/systempresets/3F3F3F3F_4D6F6F56/H264 Match Source - High bitrate.epr";
app.encoder.launchEncoder();
var jid = app.encoder.encodeSequence(seq, DST, PRESET, 0, 0);   // 0=シーケンス全体, 0=キューに残す
app.encoder.startBatch();
```

★**出力の拡張子はプリセットのコンテナに上書きされる。** `.mp4` を指定しても **`.mov` で出る。**
完了待ちで `.mp4` を探して「出ない」と誤判定した（実際に踏んだ）。

```bash
bash scripts/wait_render.sh /path/to/出力          # 拡張子違いを吸収して待つ
python3 scripts/ame_watch.py list                  # AMEログ（UTF-16LE）で結果を確認
```

★**`encodeSequence` は非ブロッキング**（投入0.45秒）。`exportAsMediaDirect` はブリッジを止めるので使わない。
★実測: **20秒のシーケンスが2秒**で書き出せる（ハードウェアエンコード）。待ち時間の見積もりに使う。

---

## 6. ユーザーに見てもらう

**こちらで絵の良し悪しを判定しない。** 渡すときは必ずこの4点を添える。

1. **どこにあるか**（シーケンス名・時間・ファイルパス）
2. **何が入っているか**（クリップごとの設定を表で）
3. **どこを見てほしいか**（1〜3点に絞る）
4. **その結果でどう分岐するか**（出た場合／出ない場合に次に何をするか）

★**配置まで済ませてから渡す。** 「このファイルを読み込んでください」で止めない。
★**背景を敷き、既定色が背景とぶつかっていないか確認してから渡す。**

---

## 7. 記録する

- **`.aep` / `.mogrt` / `.jsx` は上書きしない。** v番号を上げ、**却下版も理由つきで残す**
- **台帳の `revision_record_db`（修正記録DB）に1行**（記録名／対象ファイル_pyパス（フルパス）／
  バージョン／変更内容／変更理由（ユーザー指摘は**原文引用**）／採用状態／却下理由／検証方法／
  関連ファイルパス／実行日時）。MCP `ledger_upsert(db_key="revision_record_db", record_id=<記録名>)`。
  ★2026-08-12 に Notion から台帳へ移管した（案件ごとにテンプレDBを複製する運用は廃止。
  db_key は固定で、案件は `project_id` で分かれる）
- **採用版が変わった瞬間に台帳を更新する。** 未更新のまま「完了」と報告しない

### git

```bash
rsync -a --delete ~/.claude/skills/<skill>/ ~/dev/vof-push/skills/<skill>/
cd ~/dev/vof-push && git add -A skills/<skill> && git commit -F <msg> && git push origin <branch>
git ls-remote origin <branch>     # ★ローカルHEADとSHAが一致することを必ず確認
```

★**iCloud配下（`~/Documents` など）では作業しない。** 極端に遅く、TCCでEPERMになることもある。
★`main`/`master` へのpush・force push・mergeはしない。
