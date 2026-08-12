var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/b07.txt";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++)
  if(app.projects[i].path && app.projects[i].path.indexOf("FERIEST_0802_spray_v1")>=0) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++)
  if(proj.sequences[s].name==="0802_spray") seq=proj.sequences[s];
proj.openSequence(seq.sequenceID);
var n=0;
for(var a=0;a<seq.audioTracks.numTracks;a++){
  var A=seq.audioTracks[a];
  for(var k=A.clips.numItems-1;k>=0;k--){ A.clips[k].remove(false,false); n++; }
}
log("removed audio clips="+n);
proj.save();
var f2=new File(OUT); f2.encoding="UTF8"; f2.open("w"); f2.write(L.join("\n")); f2.close();
return "done";
