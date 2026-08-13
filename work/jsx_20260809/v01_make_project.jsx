// ★★★2026-08-13 追記: このスクリプトの proj.createNewSequence は
//   【新規シーケンスダイアログが開き、人が OK を押すまで返らない】（引数を何にしても出る）。
//   無人で回すと必ずタイムアウトする。★新版 v01b_make_project.jsx を使うこと
//   （createNewSequenceFromClips でダイアログ無しに作る）。
//   このファイルは記録として残してある（上書き禁止）。

var L = [];
function log(s){ L.push(String(s)); }
function flush(p){ var f=new File(p); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close(); }

var OUT = "@@BRIDGE_DIR@@/ebi_v01.txt";
var PROJ_PATH = "@@FERIEST_ROOT@@/02_work/premiere/FERIEST_0801_ebi_v1.prproj";

// ★参考プロジェクトを絶対に触らないための確認
var REF_ID = "6822d0d1-041a-46a0-a5ff-735087200a01";
for (var i=0;i<app.projects.numProjects;i++){
  log("before["+i+"] "+app.projects[i].name+"  id="+app.projects[i].documentID);
}

// 既に同名が開いていないか
var exists = null;
for (var i=0;i<app.projects.numProjects;i++){
  if (String(app.projects[i].path) === PROJ_PATH) exists = app.projects[i];
}
if (exists){
  log("既に開いている: " + exists.name + " id=" + exists.documentID);
} else {
  var f = new File(PROJ_PATH);
  if (f.exists){ log("★中断: ファイルが既に存在する（上書きしない）: " + PROJ_PATH); flush(OUT); }
  else {
    app.newProject(PROJ_PATH);
    log("newProject 実行");
  }
}

var proj = null;
for (var i=0;i<app.projects.numProjects;i++){
  if (String(app.projects[i].path) === PROJ_PATH) proj = app.projects[i];
}
if (!proj){ log("★中断: 作成後も見つからない"); flush(OUT); }
else {
  log("target name=" + proj.name + " id=" + proj.documentID + " path=" + proj.path);
  if (proj.documentID === REF_ID){ log("★★★中断: 参考と同じdocumentID"); flush(OUT); }
  else {
    // シーケンスを作って既定設定を読む
    var seq = null;
    if (proj.sequences.numSequences === 0){
      proj.createNewSequence("0801_ebi", "seq0801ebi");
    }
    for (var s=0;s<proj.sequences.numSequences;s++) if (proj.sequences[s].name==="0801_ebi") seq = proj.sequences[s];
    if (!seq){ log("★中断: シーケンスが作れていない"); }
    else {
      log("seq=" + seq.name + " id=" + seq.sequenceID);
      var st = seq.getSettings();
      log("既定 videoFrameWidth=" + st.videoFrameWidth + " height=" + st.videoFrameHeight);
      log("既定 videoFrameRate(ticks)=" + st.videoFrameRate);
      log("typeof setSettings=" + (typeof seq.setSettings));
    }
    log("--- after ---");
    for (var i=0;i<app.projects.numProjects;i++) log("after["+i+"] "+app.projects[i].name+" id="+app.projects[i].documentID);
  }
  flush(OUT);
}
return L.length + " lines -> " + OUT;
