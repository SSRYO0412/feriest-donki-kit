var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/fix_lock.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var V1=seq.videoTracks[0]; var n=0;
for(var c=0;c<V1.clips.numItems;c++){
  var cl=V1.clips[c];
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q];
    if(cp.displayName!=="トランスフォーム") continue;
    for(var r=0;r<cp.properties.numItems;r++){
      var p=cp.properties[r];
      if(p.displayName==="縦横比を固定"){ p.setValue(true,true); n++; }
    }
  }
}
log("縦横比を固定=true にしたクリップ数="+n);
// 読み戻し
for(var c=0;c<V1.clips.numItems;c++){
  var cl=V1.clips[c];
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q];
    if(cp.displayName!=="トランスフォーム") continue;
    var lock="",sh="";
    for(var r=0;r<cp.properties.numItems;r++){
      var p=cp.properties[r];
      if(p.displayName==="縦横比を固定") lock=String(p.getValue());
      if(p.displayName==="スケール (高さ)"){ var tv=false; try{tv=p.isTimeVarying();}catch(e){} sh=(tv?"可変":"固定"); }
    }
    log("  c0"+(c+1)+" 縦横比を固定="+lock+"  スケール(高さ)="+sh);
  }
}
proj.save(); log("save");
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
