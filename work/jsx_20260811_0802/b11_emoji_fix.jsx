var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/b11.txt";
var TPF=8467200000;
var proj=null;
for(var i=0;i<app.projects.numProjects;i++)
  if(app.projects[i].path && app.projects[i].path.indexOf("FERIEST_0802_spray_v1")>=0) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++)
  if(proj.sequences[s].name==="0802_spray") seq=proj.sequences[s];
proj.openSequence(seq.sequenceID);
var V8=seq.videoTracks[7];
for(var k=0;k<V8.clips.numItems;k++){
  var c=V8.clips[k];
  for(var q=0;q<c.components.numItems;q++){
    var cp=c.components[q];
    if(cp.displayName!=="モーション") continue;
    for(var r=0;r<cp.properties.numItems;r++)
      if(cp.properties[r].displayName==="位置"){ cp.properties[r].setValue([0.797,0.457],true); log("😂 x=0.797"); }
  }
}
proj.save();
var f2=new File(OUT); f2.encoding="UTF8"; f2.open("w"); f2.write(L.join("\n")); f2.close();
return "done";
