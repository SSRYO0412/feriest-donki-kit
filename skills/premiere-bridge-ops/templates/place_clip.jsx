// place_clip.jsx — 素材を取り込んで、指定時刻に置いて、尺を合わせて、読み戻す。
// 差し替え作業の実務はほぼこの形になる。
//
// 踏んだ罠を全部畳み込んである:
//   - insertClip は挿入編集で後続を押し出す → 必ず overwriteClip
//   - 時刻は数値ではなく Time オブジェクトで渡す
//   - overwriteClip は1フレーム長く置くことがある → clip.end で詰める
//   - projectItem は名前ではなく getMediaPath() で照合（同名の旧版を掴む）
//   - remove(false, false) = ripple false（true は後続をずらす）

function s(a) { var r = ""; for (var i = 0; i < a.length; i++) r += String.fromCharCode(a[i]); return r; }

// ==== 埋める ====
var PATH_CODES = [/* NFD charcodes of the absolute media path */];
var TRACK    = 1;    // 置くビデオトラック（numTracks 未満であること）
var AT       = 0.0;  // 開始秒（タイムライン基準）
var WANT_END = 0;    // 終了秒。尺を厳密に合わせたいときだけ指定（0 で無効）
var TAG     = "myclip_v1"; // 既存配置を掃除するための識別子（置くファイル名の先頭）
// ================

if (!PATH_CODES.length) return "★中断: PATH_CODES が未設定";

var P = app.project, S = P.activeSequence, out = [];
var path = s(PATH_CODES);

var f = new File(path);
out.push("fileExists=" + f.exists);
if (!f.exists) return "★中断: ファイルが無い " + path;

P.importFiles([path], false, P.rootItem, false);

// ★名前ではなくパスで照合する
function findByPath(p, bin) {
    for (var i = 0; i < bin.children.numItems; i++) {
        var it = bin.children[i];
        if (it.type === 2) { var r = findByPath(p, it); if (r) return r; }
        else { var mp = ""; try { mp = it.getMediaPath(); } catch (e) {} if (mp === p) return it; }
    }
    return null;
}
var item = findByPath(path, P.rootItem);
out.push("item=" + (item ? item.name : "NULL"));
if (!item) return "★中断: projectItem が見つからない";

if (TRACK >= S.videoTracks.numTracks)
    return "★中断: トラックが無い (numTracks=" + S.videoTracks.numTracks + ")";
var V = S.videoTracks[TRACK];

// 同じ素材の既存配置を掃除（ripple=false）
var removed = 0;
for (var c = V.clips.numItems - 1; c >= 0; c--) {
    if (V.clips[c].name.indexOf(TAG) === 0) { V.clips[c].remove(false, false); removed++; }
}
out.push("removed=" + removed);

var t = new Time(); t.seconds = AT;
V.overwriteClip(item, t);          // ★insertClip ではない

// 尺の詰め（overwriteClip の1F過剰を直す）
for (var k = 0; k < V.clips.numItems; k++) {
    var q = V.clips[k];
    if (q.name.indexOf(TAG) !== 0) continue;
    if (WANT_END && Math.abs(q.end.seconds - WANT_END) > 0.001) {
        var e = new Time(); e.seconds = WANT_END; q.end = e;
    }
    out.push("RB V" + TRACK + "|" + k + " " + q.name
        + " " + q.start.seconds.toFixed(4) + "-" + q.end.seconds.toFixed(4)
        + " F=" + Math.round((q.end.seconds - q.start.seconds) * 30000 / 1001));
}

var fo = new File("/tmp/premiere-mcp-bridge/place_RENAME.txt");
fo.encoding = "UTF-8";
fo.open("w"); fo.write(out.join("\n")); fo.close();
return out.join(" | ");
