var L=[]; function log(s){L.push(String(s));}
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var TPF=8467200000;
var NX=(896+30)/1080.0;   // 「合」との重なり17pxを解消して十分な間を空ける
var NY=(862+7)/1920.0;    // 本文の中心y=869.5 に合わせる
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
  for(var r=0;r<cp.properties.numItems;r++)
    if(cp.properties[r].displayName==="位置") cp.properties[r].setValue([NX,NY],true);
}
for(var q=0;q<ec.components.numItems;q++){
  var cp=ec.components[q];
  if(cp.displayName!=="モーション") continue;
  for(var r=0;r<cp.properties.numItems;r++){
    var p=cp.properties[r];
    if(p.displayName==="位置")     log("位置="+p.getValue()+"  ＝ px("+(NX*1080).toFixed(0)+", "+(NY*1920).toFixed(0)+")");
    if(p.displayName==="スケール") log("スケール="+p.getValue());
  }
}
proj.save();
seq.setInPoint(T(0)); seq.setOutPoint(T(28*TPF));
log("書き出し= "+seq.exportAsMediaDirect("@@FERIEST_ROOT@@/02_work/premiere/verify_20260809/c01_emoji_v2",EPR,1));
var f=new File("@@BRIDGE_DIR@@/x05.txt"); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
