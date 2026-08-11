var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/stroke.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
function setStroke(v,val,label){
  var tr=seq.videoTracks[v]; var n=0;
  for(var k=0;k<tr.clips.numItems;k++){
    var m=null; try{ m=tr.clips[k].getMGTComponent(); }catch(e){}
    if(!m) continue;
    for(var q=0;q<m.properties.numItems;q++) if(m.properties[q].displayName==="縁の太さ"){ m.properties[q].setValue(val,true); n++; }
  }
  log(label+" 縁の太さ="+val+" を "+n+"枚へ");
}
setStroke(2,11,"V3 本文テロップ");   // 参考 暗/白=1.49 に対し 本作1.15 → 8×1.30
setStroke(3,10,"V4 ロックアップ1行目"); // 参考2.42 / 本作1.39 → 6×1.74 ≒ 10
setStroke(4,10,"V5 ロックアップ2行目");
proj.save(); log("save");
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
