var L=[]; function log(s){L.push(String(s));}
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var TPF=8467200000;
var NX=969/1080.0, NY=869.5/1920.0;   // 本文右端890 + 間25 + 半幅54 = 969
var EPR="@@AME_PRESET@@";
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var ec=seq.videoTracks[8].clips[0];
for(var q=0;q<ec.components.numItems;q++){
  var cp=ec.components[q];
  if(cp.displayName!=="モーション") continue;
  for(var r=0;r<cp.properties.numItems;r++){
    var p=cp.properties[r];
    if(p.displayName==="位置"){ p.setValue([NX,NY],true); log("位置="+p.getValue()+" ＝ px("+(NX*1080).toFixed(0)+", "+(NY*1920).toFixed(0)+")"); }
    if(p.displayName==="スケール") log("スケール="+p.getValue());
  }
}
proj.save();
seq.setInPoint(T(0)); seq.setOutPoint(T(28*TPF));
log("書き出し= "+seq.exportAsMediaDirect("@@FERIEST_ROOT@@/02_work/premiere/verify_20260809/c01_final_v2",EPR,1));
var f=new File("@@BRIDGE_DIR@@/y06.txt"); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
