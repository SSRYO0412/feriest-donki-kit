var L=[]; function log(s){L.push(String(s));}
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39"; var TPF=8467200000;
var EPR="@@AME_PRESET@@";
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var m=seq.videoTracks[2].clips[0].getMGTComponent();
for(var q=0;q<m.properties.numItems;q++){
  var p=m.properties[q];
  if(p.displayName==="強調1の大きさ") p.setValue(40,true);   // 60だとピーク時に🍤へ53px食い込む
}
var ec=seq.videoTracks[8].clips[0];
for(var q=0;q<ec.components.numItems;q++){
  var cp=ec.components[q];
  if(cp.displayName!=="モーション") continue;
  for(var r=0;r<cp.properties.numItems;r++)
    if(cp.properties[r].displayName==="位置") cp.properties[r].setValue([976/1080.0,869.5/1920.0],true);
}
log("強調1の大きさ=40 / 🍤 位置=px(976, 870)");
proj.save();
seq.setInPoint(T(0)); seq.setOutPoint(T(28*TPF));
log("書き出し= "+seq.exportAsMediaDirect("@@FERIEST_ROOT@@/02_work/premiere/verify_20260809/c01_anim",EPR,1));
var f=new File("@@BRIDGE_DIR@@/z06.txt"); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
