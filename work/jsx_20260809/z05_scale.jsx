var L=[]; function log(s){L.push(String(s));}
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39"; var TPF=8467200000;
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var V1=seq.videoTracks[0]; var ng=0;
for(var k=0;k<V1.clips.numItems;k++){
  var cl=V1.clips[k], ms="?", mp="?";
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q];
    if(cp.displayName!=="モーション") continue;
    for(var r=0;r<cp.properties.numItems;r++){
      var p=cp.properties[r];
      if(p.displayName==="スケール") ms=p.getValue();
      if(p.displayName==="位置") mp=String(p.getValue());
    }
  }
  var bad = Math.abs(Number(ms)-88.889)>0.01;
  if(bad) ng++;
  log("["+k+"] "+Math.round(Number(cl.start.ticks)/TPF)+"-"+Math.round(Number(cl.end.ticks)/TPF)+"F モーション スケール="+ms+" 位置="+mp+(bad?"  ★88.889でない":""));
}
log("スケールが違うクリップ="+ng+"（0が正常）");
var f=new File("@@BRIDGE_DIR@@/z05.txt"); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
