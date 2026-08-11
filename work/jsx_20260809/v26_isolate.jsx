var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v26.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
// V1,V2,V3,V5 を無効化して V4 だけ残す
for(var v=0;v<seq.videoTracks.numTracks;v++){
  var tr=seq.videoTracks[v];
  var off = (v!==3);
  for(var k=0;k<tr.clips.numItems;k++) tr.clips[k].disabled = off;
  log("V"+(v+1)+" disabled="+off+" clips="+tr.clips.numItems);
}
// V4のモーションも確認
var cl=seq.videoTracks[3].clips[0];
for(var q=0;q<cl.components.numItems;q++){
  var cp=cl.components[q];
  var ps=[];
  for(var r=0;r<cp.properties.numItems;r++){
    var p=cp.properties[r];
    var v2=""; try{ v2=String(p.getValue()); }catch(e){ v2="?"; }
    if(v2.length>60) v2=v2.substring(0,60)+"…";
    ps.push(p.displayName+"="+v2);
  }
  log("  comp["+q+"] "+cp.displayName+" : "+ps.join(" / "));
}
proj.save(); log("save");
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
