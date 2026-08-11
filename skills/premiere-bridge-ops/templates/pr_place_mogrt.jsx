// pr_place_mogrt.jsx — MOGRT をシーケンスに置いてパラメータを流し込む定型（Premiere用）
//
// bash scripts/pr.sh でこのファイルを投げる。★結果はファイル経由でしか受け取れない。
//
// ここに畳み込んである罠（どれも実機で踏んだ）:
//   1. ブリッジは戻り値を返さない → 結果は File に書く。File.lineFeed="Unix" を忘れない
//   2. documentID はユニークではない（.prproj のコピーで複製される）→ 名前と2点照合し、
//      重複したら中断する
//   3. importMGT の第2引数 ticks は **文字列**。数値だと時刻が効かず全部0秒に入る
//   4. ドロップダウンは Premiere が0始まり・AEが1始まり → **AEの値 − 1** を渡す
//   5. 色は setValue できない（読みは64bit・書きは32bitに丸める）→ テンプレ側の既定値で持つ
//   6. 本文を変えたら fontTextRunLength を文字数に合わせる。揃えないと **UIで開いた瞬間に落ちる**
//   7. モーションの「位置」は正規化(0〜1)。「グラフィックパラメーター」側にも「位置」があるので
//      コンポーネント名で絞る
//   8. importFiles は非同期。呼んだ直後には rootItem から見つからない

// ==================== 設定 ====================
var OUT       = "/tmp/pr_place_out.txt";       // 結果の書き出し先（毎回変えること）
var DOC_ID    = "<documentID をここに>";
var PROJ_HINT = "<プロジェクト名の先頭一致>";   // 3点照合の2点目
var SEQ_NAME  = "<シーケンス名>";
var MOGRT     = "/path/to/テンプレ_fontedit.mogrt";   // ★fontedit を通したもの
var FRAME_W   = 1920;

// 置きたいものを並べる。dropdown は「AEの値」で書いてよい（内部で −1 する）
var PLAN = [
  { sec: 0.0, track: 1, text: "これは",
    font: "Toppan-BunkyuMidashiGoStdN-EB", size: 120,
    x: 0.356281,                                   // ae_measure_text.jsx で出した正規化位置
    nums: { "縁の太さ": 10, "縦位置": 50, "出現の尺": 0.5 },
    drops: { "出現の型": 2, "強調の出方": 1 } },    // AEの値（2=フェード / 2=後から跳ねる）
  { sec: 0.45, track: 2, text: "グローです",
    font: "Toppan-BunkyuMidashiGoStdN-EB", size: 120,
    x: 0.588813,
    nums: { "縁の太さ": 10, "縦位置": 50, "出現の尺": 0.5, "グローの強さ": 55 },
    drops: { "出現の型": 3, "グローの種類": 2 } }
];
var CLEAR_TRACKS_FROM = 1;   // このトラック番号以降を掃除する（0にすると背景も消える）

// ==================== ここから下は定型 ====================
var L = [];
function log(s) { L.push(String(s)); }
function flush() {
    var f = new File(OUT); f.encoding = "UTF-8"; f.lineFeed = "Unix";
    f.open("w"); f.write(L.join("\n")); f.close();
}
var TPS = 254016000000;

// ---- ① 対象プロジェクトを固定する（3点照合・重複したら中断）----
var hits = [];
for (var i = 0; i < app.projects.numProjects; i++)
    if (app.projects[i].documentID === DOC_ID) hits.push(app.projects[i]);
if (hits.length === 0)      { log("★中断: documentID が見つからない"); flush(); }
else if (hits.length > 1)   { log("★中断: documentID が重複している（.prproj のコピーを開いている）"); flush(); }
else if (hits[0].name.indexOf(PROJ_HINT) !== 0) { log("★中断: 想定外のプロジェクト " + hits[0].name); flush(); }
else {
var proj = hits[0];
var seq = null;
for (var s = 0; s < proj.sequences.numSequences; s++)
    if (proj.sequences[s].name === SEQ_NAME) seq = proj.sequences[s];
if (!seq) { log("★中断: シーケンスが無い: " + SEQ_NAME); flush(); }
else {
proj.openSequence(seq.sequenceID);          // プロジェクトとシーケンスを同時にアクティブ化
log("対象: " + proj.name + " / " + seq.name);

// ---- ② 掃除 ----
for (var t = CLEAR_TRACKS_FROM; t < seq.videoTracks.numTracks; t++) {
    var tr = seq.videoTracks[t];
    for (var q = tr.clips.numItems - 1; q >= 0; q--) {
        try { tr.clips[q].remove(false, false); } catch (e) { log("掃除で例外: " + String(e)); }
    }
}

// ---- ③ 部品 ----
function param(clip, nm) {
    var m = clip.getMGTComponent();
    if (!m) return null;
    for (var k = 0; k < m.properties.numItems; k++)
        if (m.properties[k].displayName === nm) return m.properties[k];
    return null;
}
function setText(clip, txt, font, size, label) {
    var p = param(clip, "本文");
    if (!p) { log(label + " ★本文パラメータが無い"); return; }
    var v = p.getValue();
    var nv = v.replace(/"textEditValue":"[^"]*"/, '"textEditValue":"' + txt + '"')
              .replace(/"fontTextRunLength":\[[^\]]*\]/, '"fontTextRunLength":[' + txt.length + ']')
              .replace(/"capPropDefault":"[^"]*"/, '"capPropDefault":"' + txt + '"');
    if (font) nv = nv.replace(/("fontEditValue":\[)"[^"]*"(\])/, '$1"' + font + '"$2');
    if (size) nv = nv.replace(/("fontSizeEditValue":\[)[^\]]*(\])/, '$1' + size + '$2');
    p.setValue(nv, true);
    // ★必ず読み返して検算する（配列長がずれていると UI で開いた瞬間に落ちる）
    var a = p.getValue();
    var te = a.match(/"textEditValue":"([^"]*)"/), rl = a.match(/"fontTextRunLength":\[([^\]]*)\]/);
    var fe = a.match(/"fontEditValue":\["([^"]*)"\]/);
    var ok = (rl && String(rl[1]) === String(txt.length));
    log(label + " 本文=「" + (te ? te[1] : "?") + "」 配列長=" + (rl ? rl[1] : "?")
        + "（文字数" + txt.length + "）" + (ok ? " ✅" : " ★不一致＝落ちる危険")
        + (font ? ("  書体=" + (fe ? fe[1] : "?") + (fe && fe[1] === font ? " ✅" : " ★不一致")) : ""));
}
function setNums(clip, obj, label) {
    for (var nm in obj) { var p = param(clip, nm); if (p) p.setValue(obj[nm], true);
                          else log(label + " ★項目が無い: " + nm); }
}
function setDrops(clip, obj, label) {
    // ★AEの値 − 1 を渡す（Premiere は0始まり）
    for (var nm in obj) { var p = param(clip, nm); if (p) p.setValue(obj[nm] - 1, true);
                          else log(label + " ★項目が無い: " + nm); }
}
function setPos(clip, x, label) {
    var cs = clip.components, done = false;
    for (var q2 = 0; q2 < cs.numItems; q2++) {
        var cp = cs[q2];
        for (var r2 = 0; r2 < cp.properties.numItems; r2++) {
            var pr = cp.properties[r2];
            if (pr.displayName === "位置" && cp.displayName === "モーション") {
                pr.setValue([x, 0.5], true); done = true;
            }
        }
    }
    if (!done) log(label + " ★モーションの位置が見つからない");
}

// ---- ④ 配置 ----
for (var n = 0; n < PLAN.length; n++) {
    var P = PLAN[n], label = "[" + n + "]";
    var clip = null;
    try { clip = seq.importMGT(MOGRT, String(Math.round(P.sec * TPS)), P.track, 0); }
    catch (e) { log(label + " ★importMGT 例外: " + String(e)); continue; }
    if (!clip) { log(label + " ★importMGT が null（AE製でない可能性）"); continue; }
    log(label + " V" + (P.track + 1) + "  " + clip.start.seconds.toFixed(2)
        + "〜" + clip.end.seconds.toFixed(2) + "秒");
    if (P.text)  setText(clip, P.text, P.font, P.size, label);
    if (P.nums)  setNums(clip, P.nums, label);
    if (P.drops) setDrops(clip, P.drops, label);
    if (P.x !== undefined) setPos(clip, P.x, label);
}

// ---- ⑤ 結果を出して頭出し ----
log("--- 配置結果 ---");
for (var t2 = 0; t2 < seq.videoTracks.numTracks; t2++) {
    var tt = seq.videoTracks[t2];
    for (var j = 0; j < tt.clips.numItems; j++)
        log("  V" + (t2 + 1) + "  " + tt.clips[j].start.seconds.toFixed(2)
            + "〜" + tt.clips[j].end.seconds.toFixed(2) + "  " + tt.clips[j].name);
}
try { seq.setPlayerPosition("0"); } catch (e) { }
flush();
}}
