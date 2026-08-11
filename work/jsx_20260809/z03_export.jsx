var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var TPF=8467200000;
var EPR="@@AME_PRESET@@";
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
seq.setInPoint(T(0)); seq.setOutPoint(T(337*TPF));
var r=seq.exportAsMediaDirect("@@FERIEST_ROOT@@/02_work/premiere/verify_20260809/v7b",EPR,1);
var f=new File("@@BRIDGE_DIR@@/z03.txt"); f.encoding="UTF-8"; f.open("w"); f.write("export="+r); f.close();
return "ok";
