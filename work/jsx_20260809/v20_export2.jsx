var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v17.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var DST="@@FERIEST_ROOT@@/03_render/premiere_202608/ebi_pre02";
var EPR="@@AME_PRESET@@";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var e=new File(EPR); log("preset exists="+e.exists);
if(!e.exists){ log("★中断: プリセットが無い"); }
else{
  app.encoder.launchEncoder();
  var jid = app.encoder.encodeSequence(seq, DST, EPR, 0, 0);
  log("jobID="+jid+"  (0なら投入失敗)");
  app.encoder.startBatch();
  log("startBatch 実行");
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
