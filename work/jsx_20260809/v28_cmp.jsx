var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v28.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
function dump(v,k,label){
  var cl=seq.videoTracks[v].clips[k];
  var out=label+"  name="+cl.name+" disabled="+cl.disabled;
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q];
    if(cp.displayName!=="不透明度") continue;
    for(var r=0;r<cp.properties.numItems;r++){
      var p=cp.properties[r];
      out+="  "+p.displayName+"="+p.getValue();
    }
  }
  log(out);
}
dump(2,3,"V3[3] (162F-227F 同じ文言・描画されている)");
dump(3,0,"V4[0] (ロックアップ・描画されない)");
// 全トラックの有効状態も
for(var v=0;v<seq.videoTracks.numTracks;v++){
  var tr=seq.videoTracks[v]; var st="";
  for(var k=0;k<tr.clips.numItems;k++) st+=(tr.clips[k].disabled?"x":"o");
  log("V"+(v+1)+" clips="+tr.clips.numItems+" 有効="+st);
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
