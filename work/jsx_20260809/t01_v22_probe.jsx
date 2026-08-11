var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/v22probe.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var MG="@@KIT_ROOT@@/skill/donki-feriest/assets/telop_3slot_v22.mogrt";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var f0=new File(MG); log("v22 exists="+f0.exists);
// 空きトラック(V7)を確保して試し置き
proj.openSequence(seq.sequenceID);
if(seq.videoTracks.numTracks<7){ try{ qe.project.getActiveSequence().addTracks(7-seq.videoTracks.numTracks,seq.videoTracks.numTracks,0,0,0,0);}catch(e){log("addTracks:"+String(e));} }
log("Vトラック="+seq.videoTracks.numTracks);
var TI=seq.videoTracks.numTracks-1;
var tr=seq.videoTracks[TI];
for(var k=tr.clips.numItems-1;k>=0;k--) tr.clips[k].remove(false,false);
seq.importMGT(MG, String(0), TI, -1);
tr=seq.videoTracks[TI];
if(tr.clips.numItems===0){ log("★中断: 置けていない"); }
else{
  var m=tr.clips[0].getMGTComponent();
  log("getMGTComponent="+(m?"OK":"null"));
  if(m){
    log("項目数="+m.properties.numItems);
    for(var k=0;k<m.properties.numItems;k++){
      var p=m.properties[k]; var v="";
      try{ v=String(p.getValue()); }catch(e){ v="?"; }
      if(v.length>70) v=v.substring(0,70)+"…";
      log("  ["+k+"] "+p.displayName+" = "+v);
    }
  }
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
