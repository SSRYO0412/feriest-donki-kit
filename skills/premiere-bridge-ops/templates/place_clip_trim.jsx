// place_clip_trim.jsx — ★素材を切らずに、イン点/アウト点だけで敷く（絶対厳守14条）
//
// place_clip.jsx との違い:
//   place_clip.jsx      … 素材を丸ごと置いてから clip.end で詰める（1本の差し替え向き）
//   place_clip_trim.jsx … cutlist の {src_in, src_out, tl} をトリムで敷く（本編組み立て向き）
//
// ★ffmpeg で切り出した c01.mp4 を作って置いてはいけない。前後がハンドルとして残らないと、
//   投入後に人が端を掴んで伸ばせない＝修正のたび ffmpeg へ戻ることになる。
//   横断原則は _video-core/PRINCIPLES.md §16。
//
// 踏んだ罠を全部畳み込んである:
//   - setInPoint/setOutPoint は【2引数】。mediaType を省くと "Not Enough Parameters"
//   - mediaType 0/1/2/4 は同じ値を共有する（3 は無効で 0 を返す）。4 を使えばよい
//   - 時刻は必ずフレーム格子に乗せる（サブフレームの隙間が出る）
//   - overwriteClip は素材の in/out を尊重する（insertClip は後続を押し出すので使わない）
//   - projectItem は名前ではなく getMediaPath() で照合（同名の旧版を掴む）
//   - 日本語パスは Premiere 側が NFD で返す。NFC/NFD 両形で照合する
//   - ★outPoint の読み戻しでトリムを検算しない（伸ばしても伸びない）。尺は end - start
//   - ★clip.start に負の Time を代入するとスクリプトごと落ちる。ハンドル量でクランプする
//   - ★★★ src_out が素材の実尺を超えていないか、投げる前に ffprobe で確かめる。
//     超えてもエラーにもクランプにもならず、超過分に【完全な黒＋無音】が焼き込まれる。
//     しかも下の機械検算は PASS してしまう（配置は設計どおりになるため）。
//     ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 <素材>
//
// 検証は「書き出した実ファイルの画素」で行う（§4 / references/VERIFY-METHOD.md）。

function s(a) { var r = ""; for (var i = 0; i < a.length; i++) r += String.fromCharCode(a[i]); return r; }

// ==== 埋める ====
var PPATH = "";      // 対象 .prproj のフルパス（documentID と2点照合する）
var DOCID = "";      // list_projects.jsx で採った documentID
var SEQNAME = "";    // 敷く先のシーケンス名
var VTRACK = 0;      // ビデオトラック index
var ATRACK = 0;      // オーディオトラック index
var FPS = 30.0;      // シーケンスのfps（29.97なら 30000/1001）
var CLEAR_FIRST = true;   // 敷く前に対象トラックを掃除するか

// cutlist: nfc/nfd は素材フルパスの charcodes（下のコマンドで作る）
//   python3 -c 'import sys,unicodedata as u;print(",".join(str(ord(c)) for c in u.normalize("NFC",sys.argv[1])))' '/path/to.mov'
var CUTS = [
    // { nfc: s([...]), nfd: s([...]), src_in: 3.0, src_out: 7.0, tl: 0.0 }
];
// ================

var out = [];
if (!CUTS.length) return "★中断: CUTS が未設定";

// --- 対象の固定（documentID + path の2点照合・重複したら中断） ---
var proj = null, hits = 0;
for (var j = 0; j < app.projects.numProjects; j++) {
    var p = app.projects[j];
    if (p.documentID === DOCID && p.path === PPATH) { proj = p; hits++; }
}
if (hits !== 1) return "★中断: docID+path の一致が " + hits + " 件（1件でなければ触らない）";

var seq = null;
for (var i = 0; i < proj.sequences.numSequences; i++) {
    if (proj.sequences[i].name === SEQNAME) seq = proj.sequences[i];
}
if (!seq) return "★中断: シーケンスが無い " + SEQNAME;
if (VTRACK >= seq.videoTracks.numTracks) return "★中断: V" + VTRACK + " が無い";
if (ATRACK >= seq.audioTracks.numTracks) return "★中断: A" + ATRACK + " が無い";

// --- 取り込み（NFC/NFD 両形で照合） ---
function findByPath(nfc, nfd, bin) {
    for (var i = 0; i < bin.children.numItems; i++) {
        var it = bin.children[i];
        if (it.type === 2) { var r = findByPath(nfc, nfd, it); if (r) return r; }
        else { var mp = ""; try { mp = it.getMediaPath(); } catch (e) {} if (mp === nfc || mp === nfd) return it; }
    }
    return null;
}
var items = [];
for (var k = 0; k < CUTS.length; k++) {
    var c = CUTS[k];
    var it = findByPath(c.nfc, c.nfd, proj.rootItem);
    if (!it) { proj.importFiles([c.nfc], false, proj.rootItem, false); it = findByPath(c.nfc, c.nfd, proj.rootItem); }
    items.push(it);
}
for (var k = 0; k < items.length; k++) {
    // importFiles は非同期。取り込めていなければ中断してもう一度実行する
    if (!items[k]) return "★中断: 素材の取り込みが未完（非同期）。もう一度実行する / cut[" + k + "]";
}

// --- 敷く ---
function T(sec) { var t = new Time(); t.seconds = sec; return t; }
function grid(sec) { return Math.round(sec * FPS) / FPS; }

var V = seq.videoTracks[VTRACK], A = seq.audioTracks[ATRACK];
if (CLEAR_FIRST) {
    for (var c2 = V.clips.numItems - 1; c2 >= 0; c2--) V.clips[c2].remove(false, false);
    for (var c2 = A.clips.numItems - 1; c2 >= 0; c2--) A.clips[c2].remove(false, false);
}

for (var k = 0; k < CUTS.length; k++) {
    var c = CUTS[k], it = items[k];
    // ★2引数。mediaType 4 でよい（0/1/2/4 は同じ値を共有する）
    it.setInPoint (T(grid(c.src_in )), 4);
    it.setOutPoint(T(grid(c.src_out)), 4);
    V.overwriteClip(it, T(grid(c.tl)));
}

// --- 検算（尺は end - start。outPoint の読み戻しは信用しない） ---
var ng = 0;
out.push("track\tidx\tname\ttl_start\ttl_end\t実F\t設計F\t判定");
for (var k = 0; k < V.clips.numItems; k++) {
    var q = V.clips[k];
    var gotF = Math.round((q.end.seconds - q.start.seconds) * FPS);
    var wantF = (k < CUTS.length) ? Math.round((CUTS[k].src_out - CUTS[k].src_in) * FPS) : -1;
    var ok = (gotF === wantF);
    if (!ok) ng++;
    out.push("V" + VTRACK + "\t" + k + "\t" + q.name + "\t" + q.start.seconds.toFixed(4)
        + "\t" + q.end.seconds.toFixed(4) + "\t" + gotF + "\t" + wantF + "\t" + (ok ? "OK" : "★NG"));
}
out.push("V clips=" + V.clips.numItems + " / A clips=" + A.clips.numItems
    + " / 設計 " + CUTS.length + " カット");
out.push("seq.end=" + (seq.end / 254016000000).toFixed(4));
out.push(ng === 0 ? "尺の機械検算: 全カットPASS" : "★尺の機械検算: NG " + ng + " 件");
out.push("※これは配置の検算にすぎない。効いているかは【書き出した実ファイルの画素】で判定する（§4）");

proj.save();
var fo = new File("/tmp/premiere-mcp-bridge/place_trim_RENAME.txt");   // ★毎回新しい名前にする
fo.encoding = "UTF-8"; fo.open("w"); fo.write(out.join("\n")); fo.close();
return out.join("\n");
