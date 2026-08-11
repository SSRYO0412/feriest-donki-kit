var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/u12.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var TPF=8467200000;
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var V1=seq.videoTracks[0];
var cl=V1.clips[4];
var sf=Math.round(Number(cl.start.ticks)/TPF), ef=Math.round(Number(cl.end.ticks)/TPF);
var OFF=cl.inPoint.seconds, NF=ef-sf;
log("c05 "+sf+"-"+ef+"F ("+NF+"F) inPoint="+OFF.toFixed(4));
for(var q=0;q<cl.components.numItems;q++){
  var cp=cl.components[q];
  if(cp.displayName!=="トランスフォーム") continue;
  for(var r=0;r<cp.properties.numItems;r++){
    var p=cp.properties[r], n=p.displayName;
    if(n!=="スケール" && n!=="スケール (高さ)") continue;
    var tv=false; try{ tv=p.isTimeVarying(); }catch(e){}
    if(!tv) continue;
    log("  対象プロパティ="+n+"  removeKey="+(typeof p.removeKey));
    // キーを全消し → 打ち直し
    p.setTimeVarying(false);
    p.setValue(100,true);
    p.setTimeVarying(true);
    p.addKey(OFF+0);          p.setValueAtKey(OFF+0,100,true);
    p.addKey(OFF+(NF-1)/30);  p.setValueAtKey(OFF+(NF-1)/30,115,true);
    var ks=p.getKeys(), arr=[];
    for(var z=0;z<ks.length;z++) arr.push(Math.round((ks[z].seconds-OFF)*30)+"F:"+p.getValueAtKey(ks[z]));
    log("  打ち直し後 keys="+arr.join("/")+"  頭ズレ="+Math.abs(ks[0].seconds-OFF).toFixed(4)+"秒");
  }
}
log("--- 全数再検算 ---");
var ng=0;
for(var k=0;k<V1.clips.numItems;k++){
  var c=V1.clips[k];
  var s2=Math.round(Number(c.start.ticks)/TPF), e2=Math.round(Number(c.end.ticks)/TPF);
  var O=c.inPoint.seconds, N=e2-s2, lock="?", info="なし", bad=[];
  for(var q=0;q<c.components.numItems;q++){
    var cp=c.components[q];
    if(cp.displayName!=="トランスフォーム") continue;
    for(var r=0;r<cp.properties.numItems;r++){
      var p=cp.properties[r], n=p.displayName;
      if(n==="縦横比を固定") lock=String(p.getValue());
      if(n==="スケール"||n==="スケール (高さ)"){
        var tv=false; try{ tv=p.isTimeVarying(); }catch(e){}
        if(!tv) continue;
        var ks=p.getKeys(), arr=[];
        for(var z=0;z<ks.length;z++) arr.push(Math.round((ks[z].seconds-O)*30)+"F:"+p.getValueAtKey(ks[z]));
        info=arr.join("/");
        if(Math.abs(ks[0].seconds-O)>0.01) bad.push("★頭ズレ");
        if(Math.round((ks[ks.length-1].seconds-O)*30)>N-1) bad.push("★尺超過");
      }
    }
  }
  if(lock!=="true") bad.push("★縦横比未固定");
  if(info==="なし") bad.push("★キーなし");
  if(bad.length) ng++;
  log("  c0"+(k+1)+" "+N+"F 固定="+lock+" keys="+info+(bad.length?("  "+bad.join(" ")):"  OK"));
}
log("不備="+ng+"（0が正常）");
proj.save(); log("save");
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
