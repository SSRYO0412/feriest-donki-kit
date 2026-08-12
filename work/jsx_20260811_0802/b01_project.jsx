var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/b01.txt";
var P="@@FERIEST_ROOT@@/02_work/premiere/FERIEST_0802_spray_v1.prproj";
var REF="6822d0d1-041a-46a0-a5ff-735087200a01";
// 既に開いていれば使う。無ければ新規作成
var proj=null;
for(var i=0;i<app.projects.numProjects;i++){
  var pr=app.projects[i];
  if(pr.path && pr.path.indexOf("FERIEST_0802_spray_v1")>=0) proj=pr;
}
if(!proj){
  var f=new File(P);
  if(f.exists){ app.openDocument(P); }
  else { app.newProject(P); }
  for(var i=0;i<app.projects.numProjects;i++)
    if(app.projects[i].path && app.projects[i].path.indexOf("FERIEST_0802_spray_v1")>=0) proj=app.projects[i];
}
if(!proj){ log("★プロジェクト作成失敗"); }
else if(proj.documentID===REF){ log("★中断: 参照prproj"); }
else{
  log("project="+proj.name+" documentID="+proj.documentID);
  // シーケンス
  var seq=null;
  for(var s=0;s<proj.sequences.numSequences;s++)
    if(proj.sequences[s].name==="0802_spray") seq=proj.sequences[s];
  if(!seq){
    // ダミー作成→設定を縦型へ
    proj.createNewSequence("0802_spray","seq0802");
    for(var s=0;s<proj.sequences.numSequences;s++)
      if(proj.sequences[s].name==="0802_spray") seq=proj.sequences[s];
    var st=seq.getSettings();
    st.videoFrameWidth=1080; st.videoFrameHeight=1920;
    var t=new Time(); t.ticks="8467200000"; st.videoFrameRate=t;
    st.videoPixelAspectRatio="1:1";
    st.editingMode="795454d9-d3c2-429d-9474-923ab13b7018";
    st.videoFieldType=0;
    seq.setSettings(st);
  }
  proj.openSequence(seq.sequenceID);
  var st2=seq.getSettings();
  log("seq="+seq.name+" "+st2.videoFrameWidth+"x"+st2.videoFrameHeight+" tracks="+seq.videoTracks.numTracks);
  proj.save();
}
var f2=new File(OUT); f2.open("w"); f2.write(L.join("\n")); f2.close();
return "done";
