var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/u04.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var V1=seq.videoTracks[0];
log("=== 全6カットの Lumetri 彩度（現状）===");
for(var k=0;k<V1.clips.numItems;k++){
  var cl=V1.clips[k], vals=[];
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q];
    if(cp.displayName!=="Lumetri カラー") continue;
    for(var r=0;r<cp.properties.numItems;r++)
      if(cp.properties[r].displayName==="彩度") vals.push(r+":"+cp.properties[r].getValue());
  }
  log("  c0"+(k+1)+" "+cl.name+"  彩度="+vals.join(" , "));
}
log("");
log("=== c04 を他カットと同じ形へ揃える ===");
// 基準: c01 の彩度プロパティ配列
var ref=[];
for(var q=0;q<V1.clips[0].components.numItems;q++){
  var cp=V1.clips[0].components[q];
  if(cp.displayName!=="Lumetri カラー") continue;
  for(var r=0;r<cp.properties.numItems;r++)
    if(cp.properties[r].displayName==="彩度") ref.push([r,cp.properties[r].getValue()]);
}
var cl4=V1.clips[3];
for(var q=0;q<cl4.components.numItems;q++){
  var cp=cl4.components[q];
  if(cp.displayName!=="Lumetri カラー") continue;
  var n=0;
  for(var r=0;r<cp.properties.numItems;r++){
    var p=cp.properties[r];
    if(p.displayName!=="彩度") continue;
    if(n<ref.length && typeof ref[n][1]!=="boolean"){ p.setValue(ref[n][1],true); }
    n++;
  }
}
log("=== 揃えた後 ===");
for(var k=0;k<V1.clips.numItems;k++){
  var cl=V1.clips[k], vals=[];
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q];
    if(cp.displayName!=="Lumetri カラー") continue;
    for(var r=0;r<cp.properties.numItems;r++)
      if(cp.properties[r].displayName==="彩度") vals.push(String(cp.properties[r].getValue()));
  }
  log("  c0"+(k+1)+"  彩度="+vals.join(" , "));
}
proj.save(); log("save");
var fo=new File(OUT); fo.encoding="UTF-8"; fo.lineFeed="Unix"; fo.open("w"); fo.write(L.join("\n")); fo.close();
return "ok";
