var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/w06.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var TPF=8467200000;
var POS=[[3,0.4704,"V4 ロックアップ1行目"],[4,0.3787,"V5 ロックアップ2行目"]];
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
for(var pi=0; pi<POS.length; pi++){
  var vi=POS[pi][0], px=POS[pi][1], nm=POS[pi][2];
  var tr=seq.videoTracks[vi];
  for(var k=0;k<tr.clips.numItems;k++){
    var cl=tr.clips[k], done=false;
    for(var q=0;q<cl.components.numItems && !done;q++){
      var cp=cl.components[q];
      if(cp.displayName!=="モーション") continue;
      for(var r=0;r<cp.properties.numItems;r++){
        if(cp.properties[r].displayName==="位置"){ cp.properties[r].setValue([px,0.5],true); done=true; break; }
      }
    }
    var got="?";
    for(var q=0;q<cl.components.numItems;q++){
      var cp=cl.components[q];
      if(cp.displayName!=="モーション") continue;
      for(var r=0;r<cp.properties.numItems;r++)
        if(cp.properties[r].displayName==="位置") got=String(cp.properties[r].getValue());
    }
    log(nm+" ["+k+"] "+Math.round(Number(cl.start.ticks)/TPF)+"-"+Math.round(Number(cl.end.ticks)/TPF)+"F  位置="+got+(done?"":"  ★設定できず"));
  }
}
proj.save(); log("save");
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
