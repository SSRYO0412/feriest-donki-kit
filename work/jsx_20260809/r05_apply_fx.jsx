var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/apply_fx.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var REF="6822d0d1-041a-46a0-a5ff-735087200a01";
var TPF=8467200000;
// カット尺(F): 参考の文法＝カット頭のパンチ(c01)＋他はゆっくりズームイン 100→115
var CUT=[[0,28],[28,86],[86,162],[162,227],[227,282],[282,337]];
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
if(!proj || proj.documentID===REF){ log("★中断"); }
else{
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
proj.openSequence(seq.sequenceID);
var qp=qe.project;
if(qp.name.indexOf("FERIEST_0801_ebi")!==0){ log("★中断: qeが別プロジェクトを指している ("+qp.name+")"); }
else{
  var qseq=qp.getActiveSequence();
  var efTF=qp.getVideoEffectByName("トランスフォーム");
  var efLU=qp.getVideoEffectByName("Lumetri カラー");
  log("効果取得: TF="+(efTF?"OK":"NG")+"  LUM="+(efLU?"OK":"NG"));
  var qtr=qseq.getVideoTrackAt(0);
  // QEは空きも数えるので Clip だけ集める
  var qclips=[];
  for(var i=0;i<qtr.numItems;i++){ var it=qtr.getItemAt(i); if(String(it.type)==="Clip") qclips.push(it); }
  log("V1 実クリップ数(QE)="+qclips.length);
  for(var c=0;c<qclips.length && c<6;c++){
    qclips[c].addVideoEffect(efTF);
    qclips[c].addVideoEffect(efLU);
  }
  log("エフェクト追加完了");
  // DOM側でパラメータとキーフレームを設定
  var V1=seq.videoTracks[0];
  for(var c=0;c<V1.clips.numItems && c<6;c++){
    var cl=V1.clips[c];
    var OFF=cl.inPoint.seconds;
    var nf=CUT[c][1]-CUT[c][0];
    for(var q=0;q<cl.components.numItems;q++){
      var cp=cl.components[q];
      if(cp.displayName==="トランスフォーム"){
        for(var r=0;r<cp.properties.numItems;r++){
          var p=cp.properties[r];
          if(p.displayName!=="スケール (高さ)") continue;
          p.setTimeVarying(true);
          if(c===0){   // 参考[0]と同じパンチ 0F:100 → 4F:120 → 6F:110
            p.addKey(OFF+0);      p.setValueAtKey(OFF+0,100,true);
            p.addKey(OFF+4/30);   p.setValueAtKey(OFF+4/30,120,true);
            p.addKey(OFF+6/30);   p.setValueAtKey(OFF+6/30,110,true);
          } else {      // ゆっくりズームイン 100 → 115（カット尺いっぱい）
            p.addKey(OFF+0);            p.setValueAtKey(OFF+0,100,true);
            p.addKey(OFF+(nf-1)/30);    p.setValueAtKey(OFF+(nf-1)/30,115,true);
          }
        }
      }
      if(cp.displayName==="Lumetri カラー"){
        for(var r=0;r<cp.properties.numItems;r++){
          var p=cp.properties[r];
          if(p.displayName==="彩度"){ try{ if(Number(p.getValue())===100){ p.setValue(106,true); break; } }catch(e){} }
        }
      }
    }
  }
  // 検算: キーフレームが可視範囲（inPoint〜outPoint）に入っているか
  var bad=0;
  for(var c=0;c<V1.clips.numItems && c<6;c++){
    var cl=V1.clips[c]; var OFF=cl.inPoint.seconds;
    for(var q=0;q<cl.components.numItems;q++){
      var cp=cl.components[q];
      if(cp.displayName!=="トランスフォーム") continue;
      for(var r=0;r<cp.properties.numItems;r++){
        var p=cp.properties[r];
        if(p.displayName!=="スケール (高さ)") continue;
        var tv=false; try{ tv=p.isTimeVarying(); }catch(e){}
        if(!tv){ log("  c0"+(c+1)+" ★可変になっていない"); bad++; continue; }
        var ks=p.getKeys(); var arr=[];
        for(var z=0;z<ks.length;z++) arr.push(Math.round((ks[z].seconds-OFF)*30)+"F:"+p.getValueAtKey(ks[z]));
        var d=Math.abs(ks[0].seconds-cl.inPoint.seconds);
        if(d>0.01){ log("  c0"+(c+1)+" ★先頭キーがinPointから "+d.toFixed(3)+"秒ずれ"); bad++; }
        log("  c0"+(c+1)+" TF: "+arr.join(" → "));
      }
    }
  }
  log("キーフレーム基準の不整合="+bad+"（0が正常）");
  proj.save(); log("save");
}
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
