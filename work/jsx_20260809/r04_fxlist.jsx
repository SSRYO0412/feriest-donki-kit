var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/fxlist.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
proj.openSequence(seq.sequenceID);
var qp=qe.project;
log("qe.project.name="+qp.name+"  （対象と一致するか）");
var lst=qp.getVideoEffectList();
log("エフェクト総数="+lst.length);
var hit=[];
for(var i=0;i<lst.length;i++){
  var n=String(lst[i]);
  if(n.indexOf("トランスフォーム")>=0 || n.indexOf("Lumetri")>=0 || n.indexOf("ルメトリ")>=0) hit.push(n);
}
log("該当: "+hit.join(" | "));
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
