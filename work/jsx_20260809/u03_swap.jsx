var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/u03.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var REF="6822d0d1-041a-46a0-a5ff-735087200a01";
var TPF=8467200000;
var BASE="@@FERIEST_ROOT@@/00_source_drive/20260807_新素材_8月掲載分/海老ドーン贅沢ぷりぷり海老マヨピザ/";
var NEW=BASE+"20260803_honma_a0924.MP4";
var TIN=0.60, F0=162, F1=227, NF=65;
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
if(!proj){ log("★中断: 対象なし"); }
else if(proj.documentID===REF){ log("★★★中断: 参考と同一ID"); }
else{
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
if(!seq){ log("★中断: seqなし"); } else {
function findByPath(path,bin){
  for(var i=0;i<bin.children.numItems;i++){
    var it=bin.children[i];
    if(it.type===ProjectItemType.BIN){ var r=findByPath(path,it); if(r) return r; }
    else { var mp=""; try{ mp=it.getMediaPath(); }catch(e){} if(mp===path) return it; }
  }
  return null;
}
var item=findByPath(NEW,proj.rootItem);
if(!item){ log("★中断: a0924 が見つからない（import未完）"); }
else{
  log("素材OK: "+item.name);
  var V1=seq.videoTracks[0];
  // 対象は 162F から始まるクリップ
  var idx=-1;
  for(var k=0;k<V1.clips.numItems;k++){
    if(Math.round(Number(V1.clips[k].start.ticks)/TPF)===F0){ idx=k; break; }
  }
  if(idx<0){ log("★中断: 162Fのクリップが見つからない"); }
  else{
    log("差し替え対象 V1["+idx+"] "+V1.clips[idx].name);
    V1.clips[idx].remove(false,false);
    var a=new Time(); a.seconds=TIN;                 item.setInPoint(a,4);
    var b=new Time(); b.seconds=TIN+(NF+2)/30.0;     item.setOutPoint(b,4);
    V1.overwriteClip(item, T(F0*TPF));
    // 位置を確定してからフレーム格子へ
    var ni=-1;
    for(var k=0;k<V1.clips.numItems;k++){
      if(Math.round(Number(V1.clips[k].start.ticks)/TPF)===F0){ ni=k; break; }
    }
    V1.clips[ni].end = T(F1*TPF);
    var cl=V1.clips[ni];
    log("配置後: "+cl.name+"  "+Math.round(Number(cl.start.ticks)/TPF)+"F-"+Math.round(Number(cl.end.ticks)/TPF)+"F");
    // モーションのスケール
    for(var q=0;q<cl.components.numItems;q++){
      var cp=cl.components[q];
      if(cp.displayName==="モーション"){
        for(var r=0;r<cp.properties.numItems;r++)
          if(cp.properties[r].displayName==="スケール") cp.properties[r].setValue(88.889,true);
      }
    }
    log("スケール88.889 設定");
    // トランスフォーム/Lumetri を QE で付与（アクティブ化が要る）
    proj.openSequence(seq.sequenceID);
    var qp=qe.project;
    log("qe.project="+qp.name+"（対象と一致するか要確認）");
    var qs=qp.getActiveSequence();
    var qt=qs.getVideoTrackAt(0);
    var cnt=-1, qc=null;
    for(var z=0;z<qt.numItems;z++){
      var it2=qt.getItemAt(z);
      if(it2.type!=="Clip") continue;
      cnt++;
      if(cnt===ni){ qc=it2; break; }
    }
    if(qc){
      qc.addVideoEffect(qp.getVideoEffectByName("トランスフォーム"));
      qc.addVideoEffect(qp.getVideoEffectByName("Lumetri カラー"));
      log("エフェクト付与（トランスフォーム / Lumetri カラー）");
    } else log("★QEでクリップを特定できず");
    // キーフレーム（inPoint基準）と彩度
    cl=seq.videoTracks[0].clips[ni];
    var OFF=cl.inPoint.seconds;
    log("inPoint="+OFF.toFixed(3)+"秒");
    for(var q=0;q<cl.components.numItems;q++){
      var cp=cl.components[q];
      if(cp.displayName==="トランスフォーム"){
        for(var r=0;r<cp.properties.numItems;r++){
          var p=cp.properties[r];
          if(p.displayName==="縦横比を固定") p.setValue(true,true);
        }
        for(var r=0;r<cp.properties.numItems;r++){
          var p=cp.properties[r];
          if(p.displayName==="スケール (高さ)"){
            p.setTimeVarying(true);
            p.addKey(OFF+0);           p.setValueAtKey(OFF+0,100,true);
            p.addKey(OFF+(NF-1)/30);   p.setValueAtKey(OFF+(NF-1)/30,115,true);
          }
        }
      }
      if(cp.displayName==="Lumetri カラー"){
        for(var r=0;r<cp.properties.numItems;r++){
          var p=cp.properties[r];
          if(p.displayName==="彩度"){ try{ if(Number(p.getValue())===100) p.setValue(106,true); }catch(e){} }
        }
      }
    }
    // 読み戻し
    for(var q=0;q<cl.components.numItems;q++){
      var cp=cl.components[q];
      if(cp.displayName==="トランスフォーム"){
        for(var r=0;r<cp.properties.numItems;r++){
          var p=cp.properties[r];
          if(p.displayName==="縦横比を固定") log("  縦横比を固定="+p.getValue());
          if(p.displayName==="スケール (高さ)"){
            var ks=p.getKeys(); var arr=[];
            for(var z=0;z<ks.length;z++) arr.push(Math.round((ks[z].seconds-OFF)*30)+"F:"+p.getValueAtKey(ks[z]));
            log("  スケール(高さ) keys="+arr.join(" / ")+"  ★先頭キーとinPointの差="+Math.abs(ks[0].seconds-OFF).toFixed(4)+"秒");
          }
        }
      }
      if(cp.displayName==="Lumetri カラー"){
        for(var r=0;r<cp.properties.numItems;r++)
          if(cp.properties[r].displayName==="彩度") log("  彩度="+cp.properties[r].getValue());
      }
    }
    proj.save(); log("save");
  }
}
}}
var fo=new File(OUT); fo.encoding="UTF-8"; fo.lineFeed="Unix"; fo.open("w"); fo.write(L.join("\n")); fo.close();
return "ok";
