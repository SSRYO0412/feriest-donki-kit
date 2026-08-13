// v01b_make_project.jsx — 新規プロジェクト＋縦型シーケンスを【無人で】作る
//
// ★v01_make_project.jsx からの変更点（2026-08-13）:
//   proj.createNewSequence を使うと【新規シーケンスダイアログが開き、人が OK を押すまで返らない】。
//   引数を何にしても出る（実測。誰も触らないと15秒でタイムアウトした）。
//   → 無人で作れる2つの手段のうち、新規プロジェクトには【素材から作る】方を使う。
//        proj.createNewSequenceFromClips(name, [item], bin)   … 87ms・ダイアログ無し
//        sequence.clone()                                     … 複製元が要るので新規では使えない
//   仕様は作った後に setSettings で決める（プリセットの内容は反映されないため）。
//
// ★上書き禁止のため v01 は残してある。こちらが新版。

var L = [];
function log(s){ L.push(String(s)); }
function flush(p){ var f=new File(p); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close(); }

var OUT = "@@BRIDGE_DIR@@/ebi_v01b.txt";
var PROJ_PATH = "@@FERIEST_ROOT@@/02_work/premiere/FERIEST_0801_ebi_v1.prproj";
var SEQ_NAME = "0801_ebi";
// 素材が1つ要る（シーケンスの種にするだけ。あとで中身は消す）
var SEED_MEDIA = "@@FERIEST_ROOT@@/00_source_drive/…差し替える…";

var REF_ID = "6822d0d1-041a-46a0-a5ff-735087200a01";
for (var i=0;i<app.projects.numProjects;i++){
  log("before["+i+"] "+app.projects[i].name+"  id="+app.projects[i].documentID);
}

var exists = null;
for (var i=0;i<app.projects.numProjects;i++){
  if (String(app.projects[i].path) === PROJ_PATH) exists = app.projects[i];
}
if (exists){
  log("既に開いている: " + exists.name + " id=" + exists.documentID);
} else {
  var f = new File(PROJ_PATH);
  if (f.exists){ log("★中断: ファイルが既に存在する（上書きしない）: " + PROJ_PATH); flush(OUT); }
  else { app.newProject(PROJ_PATH); log("newProject 実行"); }
}

var proj = null;
for (var i=0;i<app.projects.numProjects;i++){
  if (String(app.projects[i].path) === PROJ_PATH) proj = app.projects[i];
}
if (!proj){ log("★中断: 作成後も見つからない"); flush(OUT); }
else if (proj.documentID === REF_ID){ log("★★★中断: 参考と同じdocumentID"); flush(OUT); }
else {
  log("target name=" + proj.name + " id=" + proj.documentID);

  function findSeq(nm){
    for (var s=0;s<proj.sequences.numSequences;s++) if (proj.sequences[s].name===nm) return proj.sequences[s];
    return null;
  }
  var seq = findSeq(SEQ_NAME);

  if (!seq){
    // ── 種になる素材を1つ用意する（既に取り込み済みならそれを使う）
    var item = null;
    (function walk(bin){
      for (var i=0;i<bin.children.numItems && !item;i++){
        var it = bin.children[i];
        if (it.type === 2) walk(it); else if (it.type === 1) item = it;
      }
    })(proj.rootItem);

    if (!item){
      var sf = new File(SEED_MEDIA);
      if (!sf.exists){ log("★中断: 種にする素材が無い。SEED_MEDIA を実在するパスに直す: " + SEED_MEDIA); flush(OUT); }
      else {
        proj.importFiles([SEED_MEDIA], false, proj.rootItem, false);
        log("種の素材を取り込んだ（importFiles は非同期。見つからなければもう一度実行する）");
        (function walk2(bin){
          for (var i=0;i<bin.children.numItems && !item;i++){
            var it = bin.children[i];
            if (it.type === 2) walk2(it); else if (it.type === 1) item = it;
          }
        })(proj.rootItem);
      }
    }

    if (item){
      // ★ダイアログを出さずにシーケンスを作る唯一の道（新規プロジェクトの場合）
      proj.createNewSequenceFromClips(SEQ_NAME, [item], proj.rootItem);
      log("createNewSequenceFromClips 実行（ダイアログ無し）");
      seq = findSeq(SEQ_NAME);
    }
  }

  if (!seq){ log("★中断: シーケンスが作れていない"); }
  else {
    // ── 仕様を決める（プリセットは反映されないので必ずここで上書きする）
    var st = seq.getSettings();
    log("上書き前 " + st.videoFrameWidth + "x" + st.videoFrameHeight + " ticks=" + st.videoFrameRate.ticks);
    st.videoFrameWidth = 1080; st.videoFrameHeight = 1920;
    var tk = new Time(); tk.ticks = "8467200000"; st.videoFrameRate = tk;   // 30fps
    st.videoPixelAspectRatio = "1:1";
    st.editingMode = "795454d9-d3c2-429d-9474-923ab13b7018";
    st.videoFieldType = 0;
    seq.setSettings(st);
    var st2 = seq.getSettings();
    log("上書き後 " + st2.videoFrameWidth + "x" + st2.videoFrameHeight + " ticks=" + st2.videoFrameRate.ticks
        + " V=" + seq.videoTracks.numTracks + " A=" + seq.audioTracks.numTracks);

    // ── 種のクリップを消して空にする
    var removed = 0;
    for (var v=0; v<seq.videoTracks.numTracks; v++){
      var V = seq.videoTracks[v];
      for (var c=V.clips.numItems-1; c>=0; c--){ V.clips[c].remove(false,false); removed++; }
    }
    for (var a=0; a<seq.audioTracks.numTracks; a++){
      var A = seq.audioTracks[a];
      for (var c=A.clips.numItems-1; c>=0; c--){ A.clips[c].remove(false,false); removed++; }
    }
    log("種を削除: " + removed + " クリップ / seq.end=" + (seq.end/254016000000).toFixed(3));
    log("seq=" + seq.name + " id=" + seq.sequenceID);
  }
  log("--- after ---");
  for (var i=0;i<app.projects.numProjects;i++) log("after["+i+"] "+app.projects[i].name+" id="+app.projects[i].documentID);
  flush(OUT);
}
return L.length + " lines -> " + OUT;
