var L=[]; function log(s){L.push(String(s));}
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var REF="6822d0d1-041a-46a0-a5ff-735087200a01";
var TPF=8467200000;
var B="@@FERIEST_ROOT@@/00_source_drive/20260807_新素材_8月掲載分/海老ドーン贅沢ぷりぷり海老マヨピザ/";
var NEW=B+"20260803_honma_a0924.MP4";
var TIN=1.500, F0=162, F1=227, NF=65;
var Y=[93.7,91.4,9.8];
var EPR="@@AME_PRESET@@";
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
if(!proj || proj.documentID===REF){ log("★中断"); }
else{
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
proj.openSequence(seq.sequenceID);
function findByPath(p,bin){
  for(var i=0;i<bin.children.numItems;i++){
    var it=bin.children[i];
    if(it.type===ProjectItemType.BIN){ var r=findByPath(p,it); if(r) return r; }
    else { var mp=""; try{ mp=it.getMediaPath(); }catch(e){} if(mp===p) return it; }
  }
  return null;
}
// ===== c04: a0926 → a0924（ピザが中心に入る）。ズームは横で切れない110%止まり =====
var item=findByPath(NEW,proj.rootItem);
if(!item){ log("★中断: a0924 が見つからない"); }
else{
  var V1=seq.videoTracks[0], idx=-1;
  for(var k=0;k<V1.clips.numItems;k++) if(Math.round(Number(V1.clips[k].start.ticks)/TPF)===F0) idx=k;
  log("差し替え前 c04 = "+V1.clips[idx].name);
  V1.clips[idx].remove(false,false);
  var a=new Time(); a.seconds=TIN;               item.setInPoint(a,4);
  var b=new Time(); b.seconds=TIN+(NF+2)/30.0;   item.setOutPoint(b,4);
  V1.overwriteClip(item, T(F0*TPF));
  var ni=-1;
  for(var k=0;k<V1.clips.numItems;k++) if(Math.round(Number(V1.clips[k].start.ticks)/TPF)===F0) ni=k;
  V1.clips[ni].end=T(F1*TPF);
  // 隣を侵していないか
  var nx=V1.clips[ni+1];
  if(nx && Math.round(Number(nx.start.ticks)/TPF)!==F1){ nx.start=T(F1*TPF); log("★c05の頭を"+F1+"Fへ戻した"); }
  var cl=V1.clips[ni];
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q];
    if(cp.displayName==="モーション")
      for(var r=0;r<cp.properties.numItems;r++) if(cp.properties[r].displayName==="スケール") cp.properties[r].setValue(88.889,true);
  }
  var qp=qe.project, qs=qp.getActiveSequence(), qt=qs.getVideoTrackAt(0);
  var qc=null,cnt=-1;
  for(var z=0;z<qt.numItems;z++){ var it2=qt.getItemAt(z); if(it2.type!=="Clip") continue; cnt++; if(cnt===ni){ qc=it2; break; } }
  if(qc){ qc.addVideoEffect(qp.getVideoEffectByName("トランスフォーム")); qc.addVideoEffect(qp.getVideoEffectByName("Lumetri カラー")); }
  cl=seq.videoTracks[0].clips[ni];
  var OFF=cl.inPoint.seconds;
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q], n=cp.displayName;
    if(n==="トランスフォーム"){
      for(var r=0;r<cp.properties.numItems;r++) if(cp.properties[r].displayName==="縦横比を固定") cp.properties[r].setValue(true,true);
      for(var r=0;r<cp.properties.numItems;r++){
        var p=cp.properties[r], pn=p.displayName;
        if(pn!=="スケール" && pn!=="スケール (高さ)") continue;
        var tv=false; try{ tv=p.isTimeVarying(); }catch(e){}
        if(tv) p.setTimeVarying(false);
        p.setValue(100,true); p.setTimeVarying(true);
        p.addKey(OFF+0);         p.setValueAtKey(OFF+0,100,true);
        p.addKey(OFF+(NF-1)/30); p.setValueAtKey(OFF+(NF-1)/30,110,true);   // ★110止まり（115だとピザが横で切れる）
        break;
      }
    }
    if(n==="Lumetri カラー")
      for(var r=0;r<cp.properties.numItems;r++){ var p=cp.properties[r];
        if(p.displayName==="彩度"){ try{ if(Number(p.getValue())===100){ p.setValue(106,true); break; } }catch(e){} } }
  }
  log("c04 差し替え後 = "+cl.name+"  tin="+OFF.toFixed(3)+"  ズーム100→110");
}
// ===== c01: 強調をアニメーションさせる =====
var m=seq.videoTracks[2].clips[0].getMGTComponent();
var set={"文字色R":Y[0],"文字色G":Y[1],"文字色B":Y[2],
         "出現の型":1,"出現の尺":0.15,          // ★なしにすると強調が発火しない
         "強調の出方":1,                         // 後から跳ねる（色は黄のまま）
         "強調1開始":5,"強調1終わり":7,
         "強調1の大きさ":60,"強調1の遅れ":0.10,"強調1の縦オフセット":6,
         "強調1色R":Y[0],"強調1色G":Y[1],"強調1色B":Y[2]};
for(var q=0;q<m.properties.numItems;q++){ var p=m.properties[q];
  if(set.hasOwnProperty(p.displayName)) p.setValue(set[p.displayName],true); }
log("c01 強調: 出方=1(後から跳ねる) 大きさ60 遅れ0.10 出現=フェード0.15");
// 🍤 は静的拡大が無くなるので元の位置へ
var ec=seq.videoTracks[8].clips[0];
for(var q=0;q<ec.components.numItems;q++){ var cp=ec.components[q];
  if(cp.displayName!=="モーション") continue;
  for(var r=0;r<cp.properties.numItems;r++) if(cp.properties[r].displayName==="位置") cp.properties[r].setValue([926/1080.0,869.5/1920.0],true); }
log("🍤 位置を px(926, 870) へ戻した");
proj.save();
seq.setInPoint(T(0)); seq.setOutPoint(T(337*TPF));
log("書き出し= "+seq.exportAsMediaDirect("@@FERIEST_ROOT@@/02_work/premiere/verify_20260809/v7",EPR,1));
}
var f=new File("@@BRIDGE_DIR@@/z01.txt"); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
