var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/check_tf.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var cl=seq.videoTracks[0].clips[0];
for(var q=0;q<cl.components.numItems;q++){
  var cp=cl.components[q];
  if(cp.displayName!=="トランスフォーム") continue;
  log("--- トランスフォーム ("+cp.properties.numItems+"項目)");
  for(var r=0;r<cp.properties.numItems;r++){
    var p=cp.properties[r];
    var v=""; try{ v=String(p.getValue()); }catch(e){ v="?"; }
    var tv=false; try{ tv=p.isTimeVarying(); }catch(e){}
    log("   "+p.displayName+" = "+v+(tv?"  ★可変":""));
  }
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
