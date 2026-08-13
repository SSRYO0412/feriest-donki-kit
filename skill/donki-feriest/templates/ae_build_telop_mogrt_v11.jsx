// ae_build_telop_mogrt_v11.jsx — telop_v29（統合版＋グロー）
//
// ★この版の狙い: 【長尺に耐える】。素材長を 60秒(1800F) にした。
//   MOGRT の素材長は【コンプ長】で決まる。5秒版は clip.end で 150F を超えて伸ばすと
//   以降が描画されない（絶対厳守13条）。しかも読み戻しでは分からない。
//   60秒あれば実務のテロップ区間はほぼ1枚で賄える。使うときは clip.end で必要な尺へ詰める。
//   ★もっと要るなら DUR を上げて作り直すだけ（尺はコンプ長で決まる）。
//   ※挿入時の既定クリップ長もコンプ長（60秒）になる。★必ず clip.end で詰めて使う。
//   書き出しでレンダーされるのはタイムラインに乗っている尺だけ（コンプ長は上限でしかない）。
//   v24（影・下地・重心アンカー）＋ v22（強調3スロット）＋ 文字色グラデ ＋ 文字間隔
//
// 2026-08-13 に AE 26.3 で実測して分かったこと（これに基づく設計）:
//   ・文字間隔 = テキストアニメーターの `ADBE Text Tracking Amount`（EGP露出可・1あたり約7px@120px）
//   ・グラデ   = テキストのアルファで グラデーション(ADBE Ramp) を敷いたソリッドを抜く
//   ・行間（ADBE Text Line Spacing）は EGP に露出できない（addToMGT が undefined を返す）
//   ・`ADBE Text Tracking Type` という matchName は無い。正しくは `ADBE Text Track Type`
//
// レイヤー構成（上から）:
//   1. マット … 本文の複製。影もフチも持たない「グリフの形だけ」。グラデを抜くためだけに在る
//                （AEがトラックマットに設定した時点で自動的に非表示になる）
//   2. グラデ … ADBE Ramp を敷いたソリッド。マットのアルファで抜かれる
//                グラデ表示=0 のときは不透明度0で消える → 本文がそのまま見える
//   3. 本文   … 露出するソーステキスト。フチ・影・強調スロット・タイプライターはここ
//   4. 下地   … 半透明の黒板（本文の実寸に追従）
//
// ★グラデONのとき強調の「色」は見えない（グラデが全文字を覆うため）。仕様として排他にしてある。
//   強調の「大きさ・跳ね・縦オフセット」はマット側も同じ式で動くのでグラデONでも効く。
//
// つまみは全部 0〜100 に収める（EGPのスライダーは Premiere 側で 0〜100 に丸められるため）。
//   ・色は 0〜100（％）。R=100,G=84,B=0 で金
//   ・文字間隔 / 開始X・Y / 終了X・Y は 50 が中立。50 からの差が効き量
//   ・秒のものは ×0.01秒（出現の尺=50 → 0.5秒）
//
// ★書き出したあと必ず mogrt_enable_font_edit.py を通す（通さないと書体もサイズも変えられない）。
// 書き出し先は ae.sh が AE_OUTDIR として注入する。★絶対パスを直書きしない
var OUTDIR = (typeof AE_OUTDIR !== "undefined" && AE_OUTDIR)
             ? AE_OUTDIR : Folder.temp.fsName + "/vops-mogrt";
(function(){ var d = new Folder(OUTDIR); if (!d.exists) d.create(); })();

var W = 1080, H = 1920, FPS = 30, DUR = 60.0;
var NAME = "telop_v29";
var SLOTS = 3;
var DEFAULT_FONT = "GenShinGothic-Regular";

// ★app.newProject() は呼ばない。未保存プロジェクトがあると「別名で保存」モーダルで
//   AE ごと固まり、以後すべてのスクリプトが返らなくなる（2026-08-13 実際に踏んだ）。
app.beginUndoGroup("build " + NAME);
var proj = app.project;
for (var z = proj.items.length; z >= 1; z--) {
    var it0 = proj.items[z];
    if (it0 instanceof CompItem && it0.name.indexOf(NAME) === 0) it0.remove();
}
var c = proj.items.addComp(NAME, W, H, 1.0, DUR, FPS);

// ================= 下地（いちばん下） =================
var plate = c.layers.addShape();
plate.name = "下地";
var grp = plate.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group");
grp.property("ADBE Vectors Group").addProperty("ADBE Vector Shape - Rect");
grp.property("ADBE Vectors Group").addProperty("ADBE Vector Graphic - Fill")
   .property("ADBE Vector Fill Color").setValue([0, 0, 0, 1]);

// ================= 本文 =================
var tl = c.layers.addText("テロップ");
tl.name = "本文";
var tp = tl.property("ADBE Text Properties");
var sp = tp.property("ADBE Text Document");
var td = sp.value;
td.resetCharStyle();
td.font = DEFAULT_FONT;
td.fontSize = 90;
td.applyFill = true;  td.fillColor = [1, 1, 1];
td.applyStroke = true;                       // ★false だとアニメーターの線幅が効かない
td.strokeWidth = 0; td.strokeColor = [0, 0, 0]; td.strokeOverFill = false;
td.justification = ParagraphJustification.CENTER_JUSTIFY;
td.autoLeading = false; td.leading = 106;
sp.setValue(td);
var fontOK = (sp.value.font === DEFAULT_FONT);

// ================= つまみ =================
function addCtl(mn, label) { var i = tl.Effects.addProperty(mn).propertyIndex; tl.Effects.property(i).name = label; }
function addDD(label, items) {
    var i = tl.Effects.addProperty("ADBE Dropdown Control").propertyIndex;
    tl.Effects.property(i).property(1).setPropertyParameters(items);   // ★この後に改名する
    tl.Effects.property(i).name = label;
}
function ctl(n) { return tl.Effects.property(n).property(1); }

addCtl("ADBE Slider Control", "縦位置");
addCtl("ADBE Slider Control", "文字間隔");
addCtl("ADBE Slider Control", "文字色R"); addCtl("ADBE Slider Control", "文字色G"); addCtl("ADBE Slider Control", "文字色B");
addCtl("ADBE Slider Control", "縁の太さ");
addCtl("ADBE Slider Control", "縁色R"); addCtl("ADBE Slider Control", "縁色G"); addCtl("ADBE Slider Control", "縁色B");
addCtl("ADBE Slider Control", "影の距離"); addCtl("ADBE Slider Control", "影の柔らかさ"); addCtl("ADBE Slider Control", "影の濃さ");
addCtl("ADBE Slider Control", "下地の表示"); addCtl("ADBE Slider Control", "下地の濃さ");
addCtl("ADBE Slider Control", "下地の横余白"); addCtl("ADBE Slider Control", "下地の縦余白");
addDD("出現の型", ["なし", "フェード", "ポップ", "下からスライド", "タイプライター"]);
addCtl("ADBE Slider Control", "出現の尺");
addCtl("ADBE Slider Control", "グローの強さ");
addDD("グローの種類", ["なし", "ソフト", "ハード", "ワイド"]);
// ── グラデ
addCtl("ADBE Slider Control", "グラデ表示");
addCtl("ADBE Slider Control", "開始色R"); addCtl("ADBE Slider Control", "開始色G"); addCtl("ADBE Slider Control", "開始色B");
addCtl("ADBE Slider Control", "終了色R"); addCtl("ADBE Slider Control", "終了色G"); addCtl("ADBE Slider Control", "終了色B");
addCtl("ADBE Slider Control", "開始X"); addCtl("ADBE Slider Control", "開始Y");
addCtl("ADBE Slider Control", "終了X"); addCtl("ADBE Slider Control", "終了Y");
addCtl("ADBE Slider Control", "グラデの効き");
addCtl("ADBE Slider Control", "グラデのざらつき");
addDD("グラデの形", ["線形", "放射状"]);
// ── 強調
addDD("強調の出方", ["なし（最初から）", "後から跳ねる", "後から色が乗る", "跳ねて色も乗る"]);
for (var i = 1; i <= SLOTS; i++) {
    addCtl("ADBE Slider Control", "強調" + i + "開始");
    addCtl("ADBE Slider Control", "強調" + i + "終わり");
    addCtl("ADBE Slider Control", "強調" + i + "の大きさ");
    addCtl("ADBE Slider Control", "強調" + i + "の遅れ");
    addCtl("ADBE Slider Control", "強調" + i + "の縁の太さ");
    addCtl("ADBE Slider Control", "強調" + i + "の縦オフセット");
    addCtl("ADBE Slider Control", "強調" + i + "色R");
    addCtl("ADBE Slider Control", "強調" + i + "色G");
    addCtl("ADBE Slider Control", "強調" + i + "色B");
    addCtl("ADBE Slider Control", "強調" + i + "縁色R");
    addCtl("ADBE Slider Control", "強調" + i + "縁色G");
    addCtl("ADBE Slider Control", "強調" + i + "縁色B");
}

// 既定値
ctl("縦位置").setValue(75);
ctl("文字間隔").setValue(50);                       // 50=標準
ctl("文字色R").setValue(100); ctl("文字色G").setValue(100); ctl("文字色B").setValue(100);
ctl("縁の太さ").setValue(0);
ctl("縁色R").setValue(0); ctl("縁色G").setValue(0); ctl("縁色B").setValue(0);
ctl("影の距離").setValue(6); ctl("影の柔らかさ").setValue(18); ctl("影の濃さ").setValue(45);
ctl("下地の表示").setValue(0); ctl("下地の濃さ").setValue(42);
ctl("下地の横余白").setValue(18); ctl("下地の縦余白").setValue(22);
ctl("出現の型").setValue(1); ctl("出現の尺").setValue(50);
ctl("グローの強さ").setValue(0);      // 既定0＝無効（付けたいときだけ上げる）
ctl("グローの種類").setValue(2);      // ソフト
ctl("グラデ表示").setValue(0);                      // 既定OFF＝従来どおりの単色＋強調
ctl("開始色R").setValue(100); ctl("開始色G").setValue(84); ctl("開始色B").setValue(0);   // 金
ctl("終了色R").setValue(60);  ctl("終了色G").setValue(10); ctl("終了色B").setValue(0);   // 赤茶
ctl("開始X").setValue(50); ctl("開始Y").setValue(50);
ctl("終了X").setValue(50); ctl("終了Y").setValue(50);
ctl("グラデの効き").setValue(100);      // 100=グラデそのもの / 0=文字色の単色
ctl("グラデのざらつき").setValue(0);
ctl("グラデの形").setValue(1);
ctl("強調の出方").setValue(2);
for (var j = 1; j <= SLOTS; j++) {
    ctl("強調" + j + "開始").setValue(0); ctl("強調" + j + "終わり").setValue(0);
    ctl("強調" + j + "の大きさ").setValue(25);
    ctl("強調" + j + "の遅れ").setValue(40 + (j - 1) * 25);      // ×0.01秒
    ctl("強調" + j + "の縁の太さ").setValue(0);
    ctl("強調" + j + "の縦オフセット").setValue(6);
    var SC = [[100, 85, 0], [35, 85, 100], [100, 45, 55]][j - 1];
    ctl("強調" + j + "色R").setValue(SC[0]); ctl("強調" + j + "色G").setValue(SC[1]); ctl("強調" + j + "色B").setValue(SC[2]);
    ctl("強調" + j + "縁色R").setValue(0); ctl("強調" + j + "縁色G").setValue(0); ctl("強調" + j + "縁色B").setValue(0);
}

// ================= 式の共通部品 =================
var M = 'thisComp.layer("本文")';
var RGBFN = 'function rgb(r,g,b){ return [r/100, g/100, b/100, 1]; }\n';
var HEAD = 'var T=' + M + ';\n'
         + 'var ty=T.effect("出現の型")(1), d=Math.max(T.effect("出現の尺")(1)/100,0.001);\n'
         + 'var p=Math.min(Math.max(time/d,0),1);\n'
         + 'var e=1-Math.pow(1-p,3);\n';

// ================= トランスフォーム（本文とマットで完全に同じ） =================
function place(layer) {
    var xf = layer.property("ADBE Transform Group");
    xf.property("ADBE Anchor Point").expression =
        'var r=thisLayer.sourceRectAtTime(time,false);\n[r.left + r.width/2, r.top + r.height/2];';
    xf.property("ADBE Opacity").expression = HEAD + 'var f=(ty==2)?e:1;\n100*f;';
    xf.property("ADBE Scale").expression = HEAD
        + 'var m=1;\n'
        + 'if(ty==3){ if(p<0.6){ var q=p/0.6; m=0.6+0.5*(1-Math.pow(1-q,3)); }\n'
        + '           else { var q2=(p-0.6)/0.4; m=1.10-0.10*(1-Math.pow(1-q2,3)); } }\n'
        + '[100*m,100*m];';
    xf.property("ADBE Position").expression = HEAD
        + 'var y=thisComp.height*T.effect("縦位置")(1)/100;\n'
        + 'if(ty==4){ y = y + (1-e)*140; }\n'
        + '[thisComp.width/2, y];';
}
place(tl);

// ================= アニメーター（本文） =================
// ① 文字間隔
var anT = tp.property("ADBE Text Animators").addProperty("ADBE Text Animator");
anT.name = "字間";
anT.property("ADBE Text Selectors").addProperty("ADBE Text Selector");
anT.property("ADBE Text Animator Properties").addProperty("ADBE Text Tracking Amount")
   .expression = M + '.effect("文字間隔")(1) - 50;';

// ② 基本スタイル（全文字）
var an1 = tp.property("ADBE Text Animators").addProperty("ADBE Text Animator");
an1.name = "基本";
an1.property("ADBE Text Selectors").addProperty("ADBE Text Selector");
var ap1 = an1.property("ADBE Text Animator Properties");
ap1.addProperty("ADBE Text Stroke Width").expression = M + '.effect("縁の太さ")(1)';
ap1.addProperty("ADBE Text Stroke Color").expression = RGBFN
    + 'var T=' + M + '; rgb(T.effect("縁色R")(1),T.effect("縁色G")(1),T.effect("縁色B")(1));';
ap1.addProperty("ADBE Text Fill Color").expression = RGBFN
    + 'var T=' + M + '; rgb(T.effect("文字色R")(1),T.effect("文字色G")(1),T.effect("文字色B")(1));';

// ③ 強調スロット
for (var k = 1; k <= SLOTS; k++) {
    var an = tp.property("ADBE Text Animators").addProperty("ADBE Text Animator");
    an.name = "強調" + k;
    var sel = an.property("ADBE Text Selectors").addProperty("ADBE Text Selector");
    sel.property("ADBE Text Range Advanced").property("ADBE Text Selector Smoothness").setValue(0);
    var LEN = 'var T=' + M + ';\n'
            + 'var n=Math.max((""+T.text.sourceText).length,1);\n'
            + 'var a=T.effect("強調' + k + '開始")(1), b=T.effect("強調' + k + '終わり")(1); if(b<a) b=a;\n';
    sel.property("ADBE Text Percent Start").expression = LEN + 'Math.min(Math.max((a-1)/n*100,0),100);';
    sel.property("ADBE Text Percent End").expression   = LEN + 'Math.min(Math.max(b/n*100,0),100);';
    var EH = 'var T=' + M + ';\n'
           + 'var md=T.effect("強調の出方")(1);\n'
           + 'var t0=Math.max(T.effect("出現の尺")(1)/100,0)+T.effect("強調' + k + 'の遅れ")(1)/100;\n'
           + 'var q=Math.min(Math.max((time-t0)/0.45,0),1);\n'
           + 'var g=1;\n'
           + 'if(md==2||md==4){\n'
           + '  if(q<=0){ g=0; }\n'
           + '  else if(q<0.55){ var r=q/0.55; g=1.35*(1-Math.pow(1-r,3)); }\n'
           + '  else { var r2=(q-0.55)/0.45; g=1.35-0.35*(1-Math.pow(1-r2,3)); }\n'
           + '}\n'
           + 'var e2=1-Math.pow(1-q,3);\n';
    var ap = an.property("ADBE Text Animator Properties");
    ap.addProperty("ADBE Text Fill Color").expression = RGBFN + EH
        + 'var c2=rgb(T.effect("強調' + k + '色R")(1),T.effect("強調' + k + '色G")(1),T.effect("強調' + k + '色B")(1));\n'
        + 'if(md==3||md==4){ var c1=rgb(T.effect("文字色R")(1),T.effect("文字色G")(1),T.effect("文字色B")(1)); c2=c1+(c2-c1)*e2; }\n'
        + 'c2;';
    ap.addProperty("ADBE Text Scale 3D").expression = EH
        + 'var v=100+T.effect("強調' + k + 'の大きさ")(1)*g;\n[v,v,100];';
    // ★アニメーターの数値は「加算」される。本文の縁を足すと二重に乗るので追加分だけ返す
    ap.addProperty("ADBE Text Stroke Width").expression = EH + 'T.effect("強調' + k + 'の縁の太さ")(1)*g;';
    ap.addProperty("ADBE Text Stroke Color").expression = RGBFN + EH
        + 'var s2=rgb(T.effect("強調' + k + '縁色R")(1),T.effect("強調' + k + '縁色G")(1),T.effect("強調' + k + '縁色B")(1));\n'
        + 'if(md==3||md==4){ var s1=rgb(T.effect("縁色R")(1),T.effect("縁色G")(1),T.effect("縁色B")(1)); s2=s1+(s2-s1)*e2; }\n'
        + 's2;';
    ap.addProperty("ADBE Text Position 3D").expression = EH + '[0, -T.effect("強調' + k + 'の縦オフセット")(1)*g, 0];';
}

// ④ タイプライター
var an3 = tp.property("ADBE Text Animators").addProperty("ADBE Text Animator");
an3.name = "タイプライター";
var s3 = an3.property("ADBE Text Selectors").addProperty("ADBE Text Selector");
s3.property("ADBE Text Range Advanced").property("ADBE Text Selector Smoothness").setValue(0);
s3.property("ADBE Text Percent Start").expression = HEAD + '(ty==5) ? p*100 : 100;';
s3.property("ADBE Text Percent End").setValue(100);
an3.property("ADBE Text Animator Properties").addProperty("ADBE Text Opacity").setValue(0);

// ⑤ 影（レイヤースタイルはスクリプトから使えないのでエフェクトで）
var ds = tl.Effects.addProperty("ADBE Drop Shadow");
// ★色は4次元で返す。'[0,0,0]' は「エクスプレッションが無効（4次元である必要があります）」で
//   黙って既定値に落ちる。既定が黒なので絵は正しく見えてしまい、誰も気づかない
//   （同じ誤りが ae_build_telop_mogrt_v6.jsx = v24 にも入っている・2026-08-13 実測）
ds.property("ADBE Drop Shadow-0001").expression = '[0,0,0,1]';
ds.property("ADBE Drop Shadow-0002").expression = M + '.effect("影の濃さ")(1)*255/100';
ds.property("ADBE Drop Shadow-0003").setValue(135);
ds.property("ADBE Drop Shadow-0004").expression = M + '.effect("影の距離")(1)';
ds.property("ADBE Drop Shadow-0005").expression = M + '.effect("影の柔らかさ")(1)';

// ================= マット（本文の複製・影とフチを外す） =================
// ★複製してから作るのが要点。強調の大きさ/跳ね/字間まで同じ式で動くので、
//   グラデが文字とズレない（別々に組むと必ずズレる）。
var matte = tl.duplicate();
matte.name = "マット";
matte.moveToBeginning();
// 影は外す（残すと影のアルファまでグラデに染まる）
for (var q3 = matte.Effects.numProperties; q3 >= 1; q3--) {
    if (matte.Effects.property(q3).matchName === "ADBE Drop Shadow") matte.Effects.property(q3).remove();
}
// フチは0にする（残すとフチまでグラデに染まる）
var mtp = matte.property("ADBE Text Properties");
mtp.property("ADBE Text Animators").property("基本")
   .property("ADBE Text Animator Properties").property("ADBE Text Stroke Width").expression = '0';
for (var k2 = 1; k2 <= SLOTS; k2++) {
    mtp.property("ADBE Text Animators").property("強調" + k2)
       .property("ADBE Text Animator Properties").property("ADBE Text Stroke Width").expression = '0';
}
// 本文の文字をそのまま受ける（★他レイヤーの sourceText を返す式は書式を奪わない）
mtp.property("ADBE Text Document").expression = M + '.text.sourceText;';

// ================= グラデ =================
var grad = c.layers.addSolid([1, 1, 1], "グラデ", W, H, 1.0);
grad.moveAfter(matte);                       // マットの直下（マット > グラデ > 本文 > 下地）
// ★グラデの前に「塗り」で文字色を敷く。こうすると Ramp の『元の画像とブレンド』が
//   「グラデ ⇄ 文字色」の連続変化になる（白ソリッドのままだと薄めたとき白に寄ってしまう）
var fillFx = grad.property("ADBE Effect Parade").addProperty("ADBE Fill");
// 塗りのカラーは matchName を決め打ちせず、色型のプロパティを探して使う
(function () {
    var ff = grad.property("ADBE Effect Parade").property("ADBE Fill");
    for (var i = 1; i <= ff.numProperties; i++) {
        var p = ff.property(i);
        var isColor = false;
        try { isColor = (p.propertyValueType === PropertyValueType.COLOR); } catch (e) {}
        if (isColor) {
            p.expression = RGBFN + 'var T=' + M + ';\n'
                + 'rgb(T.effect("文字色R")(1),T.effect("文字色G")(1),T.effect("文字色B")(1));';
            break;
        }
    }
})();
var ramp = grad.property("ADBE Effect Parade").addProperty("ADBE Ramp");
var FOLLOW = 'var T=' + M + ';\n'
           + 'var L=thisComp.layer("マット");\n'
           + 'var r=L.sourceRectAtTime(time,false);\n'
           + 'var cx=r.left + r.width/2;\n';
function rampProp(mn) {
    var g2 = null;
    for (var i2 = 1; i2 <= c.numLayers; i2++) if (c.layer(i2).name === "グラデ") g2 = c.layer(i2);
    return g2.property("ADBE Effect Parade").property("ADBE Ramp").property(mn);
}
// 開始点/終了点は「文字ブロックへのオフセット」。50=ぴったり、±50 で ±200px
rampProp("ADBE Ramp-0001").expression = FOLLOW
    + 'L.toComp([cx + (T.effect("開始X")(1)-50)*4, r.top + (T.effect("開始Y")(1)-50)*4]);';
rampProp("ADBE Ramp-0003").expression = FOLLOW
    + 'L.toComp([cx + (T.effect("終了X")(1)-50)*4, r.top + r.height + (T.effect("終了Y")(1)-50)*4]);';
rampProp("ADBE Ramp-0002").expression = RGBFN + 'var T=' + M + ';\n'
    + 'rgb(T.effect("開始色R")(1),T.effect("開始色G")(1),T.effect("開始色B")(1));';
rampProp("ADBE Ramp-0004").expression = RGBFN + 'var T=' + M + ';\n'
    + 'rgb(T.effect("終了色R")(1),T.effect("終了色G")(1),T.effect("終了色B")(1));';
rampProp("ADBE Ramp-0005").expression = M + '.effect("グラデの形")(1);';   // 1=線形 2=放射状
// ★グラデの効き: 100=グラデそのもの / 0=文字色の単色。『元の画像とブレンド』は逆向きなので反転する
rampProp("ADBE Ramp-0007").expression = '100 - ' + M + '.effect("グラデの効き")(1);';
// ★ざらつき: 帯のバンディング（縞）を散らす
rampProp("ADBE Ramp-0006").expression = M + '.effect("グラデのざらつき")(1);';
// グラデ表示 0/100 で切り替え（＝強調色との排他）。本文の出現アニメにも追従させる
grad.property("ADBE Transform Group").property("ADBE Opacity").expression = HEAD
    + 'var on=(T.effect("グラデ表示")(1)>=50)?1:0;\n'
    + 'var f=(ty==2)?e:1;\n100*on*f;';
grad.setTrackMatte(matte, TrackMatteType.ALPHA);

// ================= 下地（本文の実寸に追従） =================
var FOLLOW2 = 'var T=' + M + ';\nvar r=T.sourceRectAtTime(time,false);\n';
var plate2 = null;
for (var i3 = 1; i3 <= c.numLayers; i3++) if (c.layer(i3).name === "下地") plate2 = c.layer(i3);
var grp2 = plate2.property("ADBE Root Vectors Group").property(1);
grp2.property("ADBE Vectors Group").property("ADBE Vector Shape - Rect")
    .property("ADBE Vector Rect Size").expression =
    FOLLOW2 + '[r.width + 2*T.effect("下地の横余白")(1), r.height + 2*T.effect("下地の縦余白")(1)];';
plate2.property("ADBE Transform Group").property("ADBE Position").expression =
    FOLLOW2 + 'T.toComp([r.left + r.width/2, r.top + r.height/2]);';
plate2.property("ADBE Transform Group").property("ADBE Opacity").expression =
    'var T=' + M + ';\n(T.effect("下地の表示")(1)>=50) ? T.effect("下地の濃さ")(1) : 0;';


// ================= グロー（ADBE Glo2。★ADBE Glow は存在しない） =================
// ★2層構成なので、表示されている側だけを光らせる:
//   本文側 … グラデON のときは 0（グラデ本体が上に乗るので、本文色で光ると色が食い違う）
//   グラデ側 … グラデOFF のときは不透明度0なので、そもそも光らない
function addGlow(layer, gateOffWhenGradient) {
    var gl = layer.Effects.addProperty("ADBE Glo2");
    var A = 'var T=' + M + ';\nvar a=T.effect("グローの強さ")(1), s=T.effect("グローの種類")(1);\n';
    var GATE = gateOffWhenGradient
        ? 'if (T.effect("グラデ表示")(1)>=50) a=0;\n' : '';
    function setIf(nm, ex) { try { gl.property(nm).expression = ex; } catch (e) { log("グロー不可 " + nm); } }
    setIf("グロー半径",     A + GATE + 's==1?0 : s==2?a*3 : s==3?a*0.8 : a*6;');
    setIf("グロー強度",     A + GATE + 's==1?0 : s==2?a*0.04 : s==3?a*0.12 : a*0.03;');
    setIf("グローしきい値", 'var s=' + M + '.effect("グローの種類")(1); s==3?30:60;');
}
addGlow(tl, true);
(function () {
    for (var i = 1; i <= c.numLayers; i++)
        if (c.layer(i).name === "グラデ") addGlow(c.layer(i), false);
})();

// ================= 露出 =================
// ★addToMotionGraphicsTemplate は参照を無効化する。毎回 名前で取り直す
function ex(nm) {
    var pr = tl.Effects.property(nm).property(1);
    if (pr.canAddToMotionGraphicsTemplate(c)) { pr.addToMotionGraphicsTemplate(c); return true; }
    return false;
}
if (sp.canAddToMotionGraphicsTemplate(c)) sp.addToMotionGraphicsTemplate(c);
var ORDER = ["縦位置", "文字間隔", "文字色R", "文字色G", "文字色B",
             "縁の太さ", "縁色R", "縁色G", "縁色B",
             "影の距離", "影の柔らかさ", "影の濃さ",
             "下地の表示", "下地の濃さ", "下地の横余白", "下地の縦余白",
             "出現の型", "出現の尺", "グローの強さ", "グローの種類",
             "グラデ表示", "開始色R", "開始色G", "開始色B", "終了色R", "終了色G", "終了色B",
             "開始X", "開始Y", "終了X", "終了Y", "グラデの形", "グラデの効き", "グラデのざらつき",
             "強調の出方"];
for (var q4 = 1; q4 <= SLOTS; q4++)
    ORDER = ORDER.concat(["強調" + q4 + "開始", "強調" + q4 + "終わり", "強調" + q4 + "の大きさ",
                          "強調" + q4 + "の遅れ", "強調" + q4 + "の縁の太さ", "強調" + q4 + "の縦オフセット",
                          "強調" + q4 + "色R", "強調" + q4 + "色G", "強調" + q4 + "色B",
                          "強調" + q4 + "縁色R", "強調" + q4 + "縁色G", "強調" + q4 + "縁色B"]);
var ng = 0;
for (var e3 = 0; e3 < ORDER.length; e3++) if (!ex(ORDER[e3])) { log("露出 ❌ " + ORDER[e3]); ng++; }

c.motionGraphicsTemplateName = NAME;
var okExp = c.exportAsMotionGraphicsTemplate(true, OUTDIR);

// ================= 自己検算（式エラーが1つでもあれば絵は黙って壊れる） =================
var errs = [];
function walk(pg, path, depth) {
    if (depth > 6) return;
    for (var i4 = 1; i4 <= pg.numProperties; i4++) {
        var p = pg.property(i4);
        try {
            if (p.numProperties !== undefined && p.numProperties > 0) walk(p, path + "/" + p.name, depth + 1);
            else if (p.expression && p.expressionError) errs.push(path + "/" + p.name + ": " + p.expressionError);
        } catch (e) {}
    }
}
// ★★★ 露出/書き出しのあとは【コンプ参照 c そのものも無効になる】（2026-08-13 実測）。
//     既存文書は「setPropertyParameters と addToMotionGraphicsTemplate がプロパティ参照を
//     無効化する」と書いていたが、CompItem まで死ぬ。名前で取り直さないと numLayers で落ちる。
for (var z3 = app.project.items.length; z3 >= 1; z3--) {
    var it3 = app.project.items[z3];
    if (it3 instanceof CompItem && it3.name === NAME) { c = it3; break; }
}
for (var i5 = 1; i5 <= c.numLayers; i5++) {
    try { walk(c.layer(i5), c.layer(i5).name, 0); } catch (e) { errs.push("walk失敗 layer" + i5 + ": " + e); }
}

var order = [], matte2 = null, txt2 = null;
for (var i6 = 1; i6 <= c.numLayers; i6++) {
    order.push(i6 + ":" + c.layer(i6).name);
    if (c.layer(i6).name === "マット") matte2 = c.layer(i6);
    if (c.layer(i6).name === "本文")   txt2   = c.layer(i6);
}
log("font: " + (fontOK ? DEFAULT_FONT + " OK" : "★代替された → " + (txt2 ? txt2.property("ADBE Text Properties").property("ADBE Text Document").value.font : "?")));
log("レイヤー順: " + order.join(" / "));
log("トラックマット: マット.isTrackMatte=" + (matte2 ? matte2.isTrackMatte : "?"));
log("露出: 本文＋" + ORDER.length + "項目（失敗 " + ng + "件）");
log("式エラー: " + (errs.length ? "★" + errs.length + "件 → " + errs.slice(0, 6).join(" | ") : "なし"));
if (txt2) log("本文実寸: " + txt2.sourceRectAtTime(1.0, false).width.toFixed(1) + " x " + txt2.sourceRectAtTime(1.0, false).height.toFixed(1));
// ★絵で確かめるための診断カット（グラデOFF / グラデON / グラデON＋字間広げ）
try {
    var dg = new Folder(OUTDIR + "/diag"); if (!dg.exists) dg.create();
    function setv(nm, v) {
        for (var z2 = 1; z2 <= c.numLayers; z2++)
            if (c.layer(z2).name === "本文") c.layer(z2).Effects.property(nm).property(1).setValue(v);
    }
    // ★「全部同時」を確かめる。1枚ずつ足していって、どれが効いていないか分かるようにする
    setv("グラデ表示", 0); setv("グローの強さ", 0); setv("影の濃さ", 0); setv("縁の太さ", 0);
    c.saveFrameToPng(2.0, new File(OUTDIR + "/diag/1_plain.png"));
    setv("影の濃さ", 45);   c.saveFrameToPng(2.0, new File(OUTDIR + "/diag/2_shadow.png"));
    setv("縁の太さ", 10);   c.saveFrameToPng(2.0, new File(OUTDIR + "/diag/3_stroke.png"));
    setv("グラデ表示", 100); c.saveFrameToPng(2.0, new File(OUTDIR + "/diag/4_gradient.png"));
    setv("グローの強さ", 60); c.saveFrameToPng(2.0, new File(OUTDIR + "/diag/5_ALL.png"));
    setv("文字間隔", 62);   c.saveFrameToPng(2.0, new File(OUTDIR + "/diag/6_ALL_track.png"));
    // グローがグラデOFFでも効くか（本文側の経路）
    setv("グラデ表示", 0);  c.saveFrameToPng(2.0, new File(OUTDIR + "/diag/7_glow_nograd.png"));
    setv("グローの強さ", 0); setv("文字間隔", 50); setv("縁の太さ", 0); setv("影の濃さ", 45);
    log("診断PNG: 4枚 → " + OUTDIR + "/diag");
} catch (e) { log("診断PNG 失敗: " + e); }
log("export: " + okExp);
app.endUndoGroup();
