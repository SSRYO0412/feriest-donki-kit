// dump_state.jsx — 書き出し前・作業前に必ず撮る「全トラックの状態」。
//
// ★このダンプの最重要列は disabled。
// 旧版のクリップを消さず上のトラックに重ねて残す運用（履歴を残すため）では、
// 同じ区間に複数の版が積まれる。無効化されているかを読めないと書き出しで旧版が焼き込まれる。
//
// clip.isDisabled() / QEの isEnabled() / setEnabled() は **どれも存在しない**（ReferenceError）。
// track.isMuted() は動くがトラック単位のミュートでクリップの無効化とは別物。
// 正解は DOM TrackItem の `disabled` プロパティ（getter として読める）。

var P = app.project;
var S = P.activeSequence;
var o = [];
o.push("proj=" + P.name);
o.push("seq=" + S.name + " id=" + S.sequenceID);
o.push("nVtracks=" + S.videoTracks.numTracks + " nAtracks=" + S.audioTracks.numTracks);

for (var t = 0; t < S.videoTracks.numTracks; t++) {
    var T = S.videoTracks[t];
    o.push("-- V" + t + " n=" + T.clips.numItems);
    for (var c = 0; c < T.clips.numItems; c++) {
        var cl = T.clips[c];
        var d = "?"; try { d = cl.disabled; } catch (e) { d = "ERR"; }
        o.push("V" + t + "|" + c
            + " disabled=" + d
            + " " + cl.start.seconds.toFixed(4) + "-" + cl.end.seconds.toFixed(4)
            + " dur=" + (cl.end.seconds - cl.start.seconds).toFixed(4)
            + " in=" + cl.inPoint.seconds.toFixed(4)
            + " " + cl.name);
    }
}
for (var a = 0; a < S.audioTracks.numTracks; a++) {
    o.push("-- A" + a + " n=" + S.audioTracks[a].clips.numItems);
}

// ★注意: QE の getVideoTrackAt(n).numItems は Empty（空き）も数える。
// type === "Clip" だけ集めてから添字を使う（実例: numItems=8 だが実クリップ4本）。

var fo = new File("/tmp/premiere-mcp-bridge/state_RENAME.txt");
fo.encoding = "UTF-8";
fo.open("w"); fo.write(o.join("\n")); fo.close();
return "wrote " + o.length + " lines";
