// list_projects.jsx — 開いている全プロジェクトと全シーケンスの識別子を吐く。
//
// 複数本を並行で進めるときの **最初の1手**。ここで採った documentID / sequenceID を
// 以降の全ジョブに渡す（prq.py --doc-id）。これをやらずに app.project を使うと、
// ユーザーがタイムラインをクリックした瞬間に対象が変わる。
//
// ★app.project は「今UIでアクティブなプロジェクト」しか返さない。
//   app.projects が開いている全プロジェクトのコレクションで、
//   Project のメソッドは **非アクティブなプロジェクトにも直接呼べる**。
//   だから「フロントに出していないと操作できない」は回避できる。
//
// ★ただしアクティブなシーケンスはアプリ全体で1本しかない。
//   project.activeSequence を近道に使うと別プロジェクトを触る。必ず sequenceID で引く。

var out = [];
var n = app.projects.numProjects;
out.push("numProjects=" + n);

// ★documentID は .prproj をコピーすると複製される。ユニークではない。
//   同じIDのプロジェクトが2つ開いていると、documentID で引いたとき
//   どちらが返るか保証がない（＝本番を編集しうる）。
//   さらに、同じIDのものを2つ開くと **シーケンスが合流して汚染される**（実測）。
//   だから起点のここで真っ先に検出して警告する。
var idCount = {};
for (var d = 0; d < n; d++) {
    var did = app.projects[d].documentID;
    idCount[did] = (idCount[did] || 0) + 1;
}
var dupFound = false;
for (var key in idCount) {
    if (idCount[key] > 1) {
        dupFound = true;
        var who = [];
        for (var e = 0; e < n; e++) {
            if (app.projects[e].documentID !== key) continue;
            var pp = ""; try { pp = app.projects[e].path; } catch (ex) { pp = "(取得不可)"; }
            who.push(app.projects[e].name + " <" + pp + ">");
        }
        out.push("");
        out.push("★★★ 危険: documentID が重複している (" + idCount[key] + "件) " + key);
        out.push("    " + who.join("\n    "));
        out.push("    → どちらか閉じるまで documentID 指定の作業をしないこと。");
        out.push("    → 同じIDのものを2つ開いた時点でシーケンスが合流している可能性がある。");
        out.push("      片方を **保存せずに** 閉じ、開き直して本数を確認すること。");
    }
}
if (!dupFound) out.push("documentID の重複なし");

var activeID = "";
try { activeID = app.project.documentID; } catch (e) {}

for (var i = 0; i < n; i++) {
    var p = app.projects[i];
    var mark = (p.documentID === activeID) ? " [ACTIVE]" : "";
    out.push("");
    out.push("PROJ[" + i + "]" + mark);
    out.push("  name=" + p.name);
    out.push("  documentID=" + p.documentID);
    var pth = "";
    try { pth = p.path; } catch (e) { pth = "(取得不可)"; }
    out.push("  path=" + pth);

    var sn = 0;
    try { sn = p.sequences.numSequences; } catch (e) {}
    out.push("  numSequences=" + sn);
    for (var j = 0; j < sn; j++) {
        var s = p.sequences[j];
        var vt = "?", at = "?";
        try { vt = s.videoTracks.numTracks; } catch (e) {}
        try { at = s.audioTracks.numTracks; } catch (e) {}
        out.push("    SEQ[" + j + "] " + s.name);
        out.push("      sequenceID=" + s.sequenceID);
        out.push("      V=" + vt + " A=" + at);
    }
}

// 戻り値は長いと切れるのでファイルへも書く。ファイル名は毎回変えること
// （同じ名前だと前回の残骸を読んでしまう）
var fo = new File("/tmp/premiere-mcp-bridge/list_projects_RENAME.txt");
fo.encoding = "UTF-8";
fo.open("w"); fo.write(out.join("\n")); fo.close();

return out.join("\n");
