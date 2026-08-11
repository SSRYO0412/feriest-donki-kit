var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/w03.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var TPF=8467200000;
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
proj.openSequence(seq.sequenceID);
var qp=qe.project;
log("qe.project="+qp.name);
var qs=qp.getActiveSequence();
var qt=qs.getVideoTrackAt(0);
// ★Empty も数えるので type==="Clip" だけ集める
var qclips=[];
for(var z=0;z<qt.numItems;z++){ var it=qt.getItemAt(z); if(it.type==="Clip") qclips.push(it); }
log("QEで見えるクリップ数="+qclips.length+"（DOMは"+seq.videoTracks[0].clips.numItems+"）");
var efTF=qp.getVideoEffectByName("トランスフォーム");
var efLU=qp.getVideoEffectByName("Lumetri カラー");
for(var k=0;k<qclips.length;k++){
  var has={};
  var cl=seq.videoTracks[0].clips[k];
  for(var q=0;q<cl.components.numItems;q++) has[cl.components[q].displayName]=1;
  if(!has["トランスフォーム"]) qclips[k].addVideoEffect(efTF);
  if(!has["Lumetri カラー"]) qclips[k].addVideoEffect(efLU);
}
log("エフェクト付与 完了");
// スケール・縦横比固定・ズーム・彩度
var V1=seq.videoTracks[0];
for(var k=0;k<V1.clips.numItems;k++){
  var cl=V1.clips[k];
  var sf=Math.round(Number(cl.start.ticks)/TPF), ef=Math.round(Number(cl.end.ticks)/TPF);
  var OFF=cl.inPoint.seconds, NF=ef-sf;
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q], n=cp.displayName;
    if(n==="モーション"){
      for(var r=0;r<cp.properties.numItems;r++)
        if(cp.properties[r].displayName==="スケール") cp.properties[r].setValue(88.889,true);
    }
    if(n==="トランスフォーム"){
      for(var r=0;r<cp.properties.numItems;r++)
        if(cp.properties[r].displayName==="縦横比を固定") cp.properties[r].setValue(true,true);
      for(var r=0;r<cp.properties.numItems;r++){
        var p=cp.properties[r], pn=p.displayName;
        if(pn!=="スケール" && pn!=="スケール (高さ)") continue;
        var tv=false; try{ tv=p.isTimeVarying(); }catch(e){}
        if(tv){ p.setTimeVarying(false); }
        p.setValue(100,true);
        p.setTimeVarying(true);
        if(k===0){                                     // 冒頭だけパンチ（参考の文法）
          p.addKey(OFF+0);          p.setValueAtKey(OFF+0,100,true);
          p.addKey(OFF+4/30);       p.setValueAtKey(OFF+4/30,120,true);
          p.addKey(OFF+6/30);       p.setValueAtKey(OFF+6/30,110,true);
        } else {
          p.addKey(OFF+0);          p.setValueAtKey(OFF+0,100,true);
          p.addKey(OFF+(NF-1)/30);  p.setValueAtKey(OFF+(NF-1)/30,115,true);
        }
        break;
      }
    }
    if(n==="Lumetri カラー"){
      for(var r=0;r<cp.properties.numItems;r++){
        var p=cp.properties[r];
        if(p.displayName==="彩度"){ try{ if(Number(p.getValue())===100){ p.setValue(106,true); break; } }catch(e){} }
      }
    }
  }
}
log("--- 検算（★名前は固定=trueで「スケール」に変わる。両方を見る）---");
var ng=0;
for(var k=0;k<V1.clips.numItems;k++){
  var cl=V1.clips[k];
  var sf=Math.round(Number(cl.start.ticks)/TPF), ef=Math.round(Number(cl.end.ticks)/TPF);
  var OFF=cl.inPoint.seconds, NF=ef-sf;
  var lock="?", keys="なし", sat="?", mscale="?", bad=[];
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q], n=cp.displayName;
    if(n==="モーション") for(var r=0;r<cp.properties.numItems;r++) if(cp.properties[r].displayName==="スケール") mscale=cp.properties[r].getValue();
    if(n==="トランスフォーム"){
      for(var r=0;r<cp.properties.numItems;r++){
        var p=cp.properties[r], pn=p.displayName;
        if(pn==="縦横比を固定") lock=String(p.getValue());
        if(pn==="スケール"||pn==="スケール (高さ)"){
          var tv=false; try{ tv=p.isTimeVarying(); }catch(e){}
          if(!tv) continue;
          var ks=p.getKeys(), arr=[];
          for(var z=0;z<ks.length;z++) arr.push(Math.round((ks[z].seconds-OFF)*30)+"F:"+p.getValueAtKey(ks[z]));
          keys=arr.join("/");
          if(Math.abs(ks[0].seconds-OFF)>0.01) bad.push("★頭ズレ");
          if(Math.round((ks[ks.length-1].seconds-OFF)*30)>NF-1) bad.push("★尺超過");
        }
      }
    }
    if(n==="Lumetri カラー") for(var r=0;r<cp.properties.numItems;r++) if(cp.properties[r].displayName==="彩度"){ sat=cp.properties[r].getValue(); break; }
  }
  if(lock!=="true") bad.push("★縦横比未固定");
  if(keys==="なし") bad.push("★キーなし");
  if(String(sat)!=="106") bad.push("★彩度"+sat);
  if(Math.abs(Number(mscale)-88.889)>0.01) bad.push("★スケール"+mscale);
  if(bad.length) ng++;
  log("  ["+k+"] "+NF+"F 固定="+lock+" 彩度="+sat+" keys="+keys+(bad.length?("  "+bad.join(" ")):"  OK"));
}
log("不備のあるショット="+ng+"（0が正常）");
proj.save(); log("save");
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
