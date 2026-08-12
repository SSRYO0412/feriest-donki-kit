var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/b06.txt";
var DST="@@FERIEST_ROOT@@/02_work/premiere/verify_20260811/0802_v3.mov";
var EPR="@@AME_PRESET@@";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++)
  if(app.projects[i].path && app.projects[i].path.indexOf("FERIEST_0802_spray_v1")>=0) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++)
  if(proj.sequences[s].name==="0802_spray") seq=proj.sequences[s];
proj.openSequence(seq.sequenceID);
var r=seq.exportAsMediaDirect(DST,EPR,app.encoder.ENCODE_ENTIRE);
log("export="+r);
var f2=new File(OUT); f2.encoding="UTF8"; f2.open("w"); f2.write(L.join("\n")); f2.close();
return "done";
