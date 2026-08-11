var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/fix1f.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var TPF=8467200000, TOTAL=337;
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var V1=seq.videoTracks[0];
var last=V1.clips[V1.clips.numItems-1];
var before=Math.round(Number(last.end.ticks)/TPF);
last.end=T(TOTAL*TPF);
var after=Math.round(Number(last.end.ticks)/TPF);
log("V1最終カット end: "+before+"F → "+after+"F");
// 全トラックの終端を検算
var bad=0;
for(var v=0;v<seq.videoTracks.numTracks;v++){
  var tr=seq.videoTracks[v];
  if(tr.clips.numItems===0) continue;
  var e=Math.round(Number(tr.clips[tr.clips.numItems-1].end.ticks)/TPF);
  var ok=(e===TOTAL);
  if(!ok) bad++;
  log("  V"+(v+1)+" 終端="+e+"F "+(ok?"OK":"★ずれ"));
}
// V1の隙間検算
var prev=0,gaps=0;
for(var k=0;k<V1.clips.numItems;k++){
  var sf=Math.round(Number(V1.clips[k].start.ticks)/TPF), ef=Math.round(Number(V1.clips[k].end.ticks)/TPF);
  if(sf!==prev) gaps++;
  prev=ef;
}
log("V1 隙間/重なり="+gaps+"（0が正常）  終端="+prev+"F");
log("終端ずれのトラック数="+bad+"（0が正常）");
proj.save(); log("save");
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
