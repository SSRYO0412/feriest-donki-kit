var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/u09.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var TPF=8467200000;
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var V1=seq.videoTracks[0];
for(var k=0;k<V1.clips.numItems;k++){
  var cl=V1.clips[k];
  var sf=Math.round(Number(cl.start.ticks)/TPF), ef=Math.round(Number(cl.end.ticks)/TPF);
  var OFF=cl.inPoint.seconds, NF=ef-sf;
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q];
    if(cp.displayName!=="トランスフォーム") continue;
    for(var r=0;r<cp.properties.numItems;r++){
      var p=cp.properties[r];
      if(p.displayName==="縦横比を固定"){ p.setValue(true,true); }
    }
    for(var r=0;r<cp.properties.numItems;r++){
      var p=cp.properties[r];
      if(p.displayName!=="スケール (高さ)") continue;
      var had=p.getKeys().length;
      if(had===0){
        p.setTimeVarying(true);
        if(k===0){ // 冒頭だけパンチ（参考の文法）
          p.addKey(OFF+0);     p.setValueAtKey(OFF+0,100,true);
          p.addKey(OFF+4/30);  p.setValueAtKey(OFF+4/30,120,true);
          p.addKey(OFF+6/30);  p.setValueAtKey(OFF+6/30,110,true);
        } else {
          p.addKey(OFF+0);          p.setValueAtKey(OFF+0,100,true);
          p.addKey(OFF+(NF-1)/30);  p.setValueAtKey(OFF+(NF-1)/30,115,true);
        }
        log("c0"+(k+1)+" キーが無かったので追加（尺"+NF+"F）");
      }
    }
  }
}
log("--- 全数の読み戻し ---");
var ng=0;
for(var k=0;k<V1.clips.numItems;k++){
  var cl=V1.clips[k];
  var sf=Math.round(Number(cl.start.ticks)/TPF), ef=Math.round(Number(cl.end.ticks)/TPF);
  var OFF=cl.inPoint.seconds, NF=ef-sf, line="c0"+(k+1)+" "+NF+"F";
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q];
    if(cp.displayName!=="トランスフォーム") continue;
    for(var r=0;r<cp.properties.numItems;r++){
      var p=cp.properties[r];
      if(p.displayName==="縦横比を固定") line+="  固定="+p.getValue();
      if(p.displayName==="スケール (高さ)"){
        var ks=p.getKeys(), arr=[];
        for(var z=0;z<ks.length;z++) arr.push(Math.round((ks[z].seconds-OFF)*30)+"F:"+p.getValueAtKey(ks[z]));
        if(!ks.length) ng++;
        line+="  keys="+(arr.length?arr.join("/"):"★なし")+"  頭ズレ="+(ks.length?Math.abs(ks[0].seconds-OFF).toFixed(4):"-");
      }
    }
  }
  log(line);
}
log("キーが無いカット="+ng+"（0が正常）");
proj.save(); log("save");
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
