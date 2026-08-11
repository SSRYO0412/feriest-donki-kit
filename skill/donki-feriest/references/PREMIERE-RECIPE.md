# Premiere の組み方（0801「海老ドーン」がそのまま雛形）

---

## 0. 接続（毎セッション手動が必要）

1. Premiere Pro を起動
2. `ウィンドウ > 拡張機能 > MCP Bridge (CEP)` を開く
3. Temp Directory が `/tmp/premiere-mcp-bridge` か確認
4. **Start Bridge を押す**

```bash
bash skill/donki-feriest/scripts/pr.sh <script.jsx> 60000
```

★**正本はキット内の `skill/donki-feriest/scripts/pr.sh`。**
`skills/premiere-bridge-ops/scripts/pr.sh`（framework 由来・編集禁止レイヤ）は
トークン解決を持たないので、案件 jsx を投げると `@@FERIEST_ROOT@@` が生のまま Premiere に届く。

★**ブリッジが止まると外部から再開できない。** ユーザーに押してもらうしかない。
再開前に**未消費の `command-*.json` を必ず消す**（溜まった分が一気に実行される）。

★**スクリプト冒頭で3点照合して中断させる**（`app.project` は手前のプロジェクトを返す）:

```javascript
var proj=null;
for(var i=0;i<app.projects.numProjects;i++)
  if(app.projects[i].documentID===DOC) proj=app.projects[i];
if(!proj) return "★中断: 対象なし";
if(proj.documentID===REF) return "★★★中断: 参考と同一ID";
```

---

## 1. 対象プロジェクト（0801）

| | |
|---|---|
| prproj | `work/premiere/FERIEST_0801_ebi_v1.prproj`（キット同梱。素材は `FERIEST_ROOT` から自動再リンク）|
| documentID | `3ea1839d-a639-48ba-acae-e0d506adfd39` |
| シーケンス | `0801_ebi` / **1080×1920 / 30fps / 337F = 11.233秒** |
| 版の退避 | `02_work/premiere/prproj_versions/`（★開かない） |
| スクリプト | `work/jsx_20260809/`（98本・キット同梱。パスはトークン化・v20参照5本は `_rejected/`）|
| 解析出力 | `02_work/ref_analysis/premiere_20260809/` |
| 検証書き出し | `02_work/premiere/verify_20260809/`（★納品物ではない） |

## 2. トラック構成

| | 中身 |
|---|---|
| V1 | カット10枚 |
| V2 | ドンペンロゴ（0-337F） |
| V3 | テロップ上段 6枚（スロット境界＝コンテ準拠） |
| V4 | ロックアップ1行目（**3枚に分割**・0-150 / 150-300 / 300-337） |
| V5 | ロックアップ2行目（同上） |
| V6 | 👇 画像（0-337F） |
| V7 | c04 下段1行目（162-227F） |
| V8 | c04 下段2行目（162-227F） |
| V9 | 🍤 画像（0-28F） |

★**V4/V5 が3枚に分かれているのは、MOGRT の素材長が 150F（5.000秒）しかないため。**
超えて `clip.end` で伸ばすと **150F以降は描画されない**（読み戻しでは気づけない）。

## 3. 縦型シーケンスの作り方

```javascript
var st = seq.getSettings();
st.videoFrameWidth = 1080; st.videoFrameHeight = 1920;
var t = new Time(); t.ticks = "8467200000"; st.videoFrameRate = t;   // 30fps
st.videoPixelAspectRatio = "1:1";
st.editingMode = "795454d9-d3c2-429d-9474-923ab13b7018";
st.videoFieldType = 0;
seq.setSettings(st);
```

`TICKS_PER_SECOND = 254016000000` → 30fps の1フレーム = **8467200000 ticks**（= TPF）。

## 4. カットの配置

```javascript
var a=new Time(); a.seconds=tin;               item.setInPoint(a,4);
var b=new Time(); b.seconds=tin+(nf+2)/30.0;   item.setOutPoint(b,4);   // 余裕2F
V1.overwriteClip(item, T(f0*TPF));
// 位置を確定してからフレーム格子へ詰める
V1.clips[k].end = T(f1*TPF);
```

★**カットはフレーム格子に乗せる**。設計秒をそのまま入れるとサブフレームの隙間ができる。

★★**余裕2Fを付けて置くと、隣のクリップの頭を2F侵す。**
差し替えのたびに検算して戻し、**戻したらそのクリップのズームキーを inPoint 基準で打ち直す**
（頭が伸びるとキーが -2F ずれる）。

## 5. カットの共通設定

| | 値 |
|---|---|
| モーション スケール | **88.889**（3840×2160 の高さを1920へ） |
| モーション 位置 | 0.5, 0.5 |
| トランスフォーム 縦横比を固定 | **true**（★既定は false） |
| トランスフォーム ズーム | 冒頭=`0F:100 / 4F:120 / 6F:110`、他=`0F:100 / (尺-1)F:115` |
| Lumetri 彩度 | **106**（★最初の1つだけ。複数あるので `break` する） |

```javascript
// エフェクトの付与は QE（アクティブ化が必要）
proj.openSequence(seq.sequenceID);
var qp=qe.project, qs=qp.getActiveSequence(), qt=qs.getVideoTrackAt(0);
// ★Empty も数えるので type==="Clip" だけ集める
var qclips=[];
for(var z=0;z<qt.numItems;z++){ var it=qt.getItemAt(z); if(it.type==="Clip") qclips.push(it); }
qclips[k].addVideoEffect(qp.getVideoEffectByName("トランスフォーム"));
qclips[k].addVideoEffect(qp.getVideoEffectByName("Lumetri カラー"));
```

```javascript
// ズームのキーは inPoint 基準
var OFF = cl.inPoint.seconds;
p.setValue(100,true); p.setTimeVarying(true);
p.addKey(OFF+0);          p.setValueAtKey(OFF+0,100,true);
p.addKey(OFF+(NF-1)/30);  p.setValueAtKey(OFF+(NF-1)/30,115,true);
```

★★**`縦横比を固定=true` にすると、プロパティ名が `スケール (高さ)` → `スケール` に変わる。**
検算では**両方の名前を受ける**。片方しか見ないと「キーフレームが無い」と誤判定する
（実際に6カット中3カットを誤報告した）。

## 6. 書き出し

```javascript
// ★AME のパスはバージョンで変わる。決め打ちにすると他マシンで書き出しが全滅する。
// pr.sh が投入直前に @@AME_PRESET@@ を実パスへ置換する（未検出なら投入せず落ちる）。
var EPR="@@AME_PRESET@@";
seq.setInPoint(T(0)); seq.setOutPoint(T(337*TPF));
seq.exportAsMediaDirect(dst, EPR, 1);   // workAreaType 1 = イン〜アウト
```

★**プリセット「Mobile Device 1080p HD」は1920×1080の横向きに強制する。**
縦型は **「Match Source - High bitrate」**。
★出力の拡張子はプリセットが上書きする（`.mp4` を渡しても `.mov` で出る）。

## 7. 毎回やる機械検算（全部0件が正常）

```
V1の隙間/重なり              前のendフレーム == 次のstartフレーム を全数
同一素材・同一区間の重複      cl.name + "@" + inPoint で数える
全トラックの終端ずれ          各トラックの clips[last].end を並べて比較
fontTextRunLength 不一致      本文の文字数と一致するか
ズームキーの inPoint 頭ズレ   |keys[0].seconds - inPoint| <= 0.01
```

## 8. 完成画素での検証（読み戻しだけで「できた」と言わない）

```
設計カット点で画が変わっているか   フレーム間差が平均の2倍を超えるか（全数）
設計外の画変わり                  冒頭のズームパンチ区間は除外する
白飛び2%超のショット              輝度≥250の画素比。★他のショットと比べて初めて異常と分かる
黒フレーム / 0.40秒未満のショット
```

★**同じAPIで書いて同じAPIで読む検算は、座標系・単位の誤りを原理的に検出できない。**

★**動く被写体は倍率相関で測れない**（相関0.12〜0.73）。
測れないものは**「測れていない」と書く**。読み戻しが通ったことを根拠に「効いている」と書かない。

## 9. 0801 の現在の構成（v7・10ショット）

| # | スロット | F範囲 | 尺 | 素材 | tin |
|---|---|---|---|---|---|
| 1 | c01 | 0-28 | 0.93秒 | `IMG_2855` | 3.700 |
| 2 | c02a | 28-57 | 0.97秒 | `a0929` | 3.033 |
| 3 | c02b | 57-86 | 0.97秒 | `a0925` | 47.667 |
| 4 | c03a | 86-111 | 0.83秒 | `IMG_2852` | 17.100 |
| 5 | c03b | 111-136 | 0.83秒 | `a0931` | 3.333 |
| 6 | c03c | 136-162 | 0.87秒 | `IMG_2857` | 17.567 |
| 7 | **c04** | 162-227 | 2.17秒 | `a0924` | 1.467（★ズーム **115→135**） |
| 8 | c05 | 227-282 | 1.83秒 | `a0928` | 3.667 |
| 9 | c06a | 282-309 | 0.90秒 | `IMG_2848` | 2.333 |
| 10 | c06b | 309-337 | 0.93秒 | `IMG_2856` | 7.467 |

**テロップ**

| | 本文 | 書体 | サイズ | 色 | 縦位置 |
|---|---|---|---|---|---|
| c01 | 海老好き大集合␣ | **HeiseiMinStd-W9** | **109** | **黄 `#EFE919`** (93.7/91.4/9.8) | 47.5 |
| c02 | 主役は海老 | mplus-1p-heavy | 68.948 | 白 | 47.5 |
| c03 | ぷりぷり♡トロトロ♡ | **HeiseiMinStd-W9** | **109** | 白 | 47.5 |
| c04 上段 | 海老ドーン | mplus-1p-heavy | 68.948 | 白 | 43.65 |
| **c04 下段1** | 贅沢ぷりぷり | mplus-1p-heavy | **141** | **`#F2704F`** (94.9/43.9/31.0) | 50.73 |
| **c04 下段2** | 海老マヨピザ | mplus-1p-heavy | **141** | 同上 | 57.81 |
| c05 | お盆はドンキのピザに決まり! | mplus-1p-heavy | 68.948 | 白 | 47.5 |
| c06 | 海老、海老、海老... | mplus-1p-heavy | 68.948 | 白 | 47.5 |

フチは**全て `#3C3934`** = (24, 22, 20)、太さ 11。

**c01 の強調**: `強調1開始=5 / 終わり=7`（「大集合」）／`強調の出方=1`／`大きさ=40`／
`遅れ=0.10`／`出現の型=1`（フェード）`尺=0.15`

**🍤**: `1f364.png` ／ スケール **151.39%**（=109÷72）／ 位置 (0.89722, 0.45286)

**ロックアップ**: V4 位置 x=**0.4704** ／ V5 位置 x=**0.3787**（★`importMGT` で敷き直すと
既定の中央に戻るので必ず再設定する）

**テンポ**: 10ショット / cuts/分 **53.4** / 尺中央値 **0.93秒** / 1テロップあたり **1.67**
