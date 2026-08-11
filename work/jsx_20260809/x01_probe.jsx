var L=[]; function log(s){L.push(String(s));}
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var TPF=8467200000;
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
log("videoTracks="+seq.videoTracks.numTracks);
var tr=seq.videoTracks[5];   // V6 = 👇
for(var k=0;k<tr.clips.numItems;k++){
  var cl=tr.clips[k];
  log("V6["+k+"] "+cl.name+"  "+Math.round(Number(cl.start.ticks)/TPF)+"-"+Math.round(Number(cl.end.ticks)/TPF)+"F");
  var mp=""; try{ mp=cl.projectItem.getMediaPath(); }catch(e){}
  log("    path="+mp);
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q];
    if(cp.displayName!=="モーション") continue;
    for(var r=0;r<cp.properties.numItems;r++){
      var p=cp.properties[r];
      if(p.displayName==="位置"||p.displayName==="スケール"||p.displayName==="アンカーポイント")
        log("    "+p.displayName+"="+p.getValue());
    }
  }
}
// c01 テロップの現状
var V3=seq.videoTracks[2];
var m=V3.clips[0].getMGTComponent();
for(var q=0;q<m.properties.numItems;q++){
  var p=m.properties[q];
  if(p.displayName==="本文"){ var b=p.getValue();
    log("c01本文 "+(b.match(/"textEditValue":"([^"]*)"/)||[])[1]+" / "+(b.match(/"fontEditValue":\["([^"]*)"\]/)||[])[1]+" / "+(b.match(/"fontSizeEditValue":\[([^\]]*)\]/)||[])[1]); }
  if(p.displayName==="縦位置") log("c01縦位置="+p.getValue());
}
var f=new File("@@BRIDGE_DIR@@/x01.txt"); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
