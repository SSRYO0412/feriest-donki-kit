var L=[]; function log(s){L.push(String(s));}
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39"; var REF="6822d0d1-041a-46a0-a5ff-735087200a01";
var TPF=8467200000;
var B="@@FERIEST_ROOT@@/00_source_drive/20260807_新素材_8月掲載分/海老ドーン贅沢ぷりぷり海老マヨピザ/";
var NEW=B+"20260803_honma_a0928.MP4";
var C5TIN=3.700, C5F0=227, C5F1=282, C5NF=55;
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
var V1=seq.videoTracks[0];
// ===== c05: a0933(静止) → a0928(表面パン。実測の動き 0.56→8.18) =====
var item=findByPath(NEW,proj.rootItem);
if(!item){ var f0=new File(NEW); log("a0928 未読込 存在="+f0.exists); proj.importFiles([NEW],true,proj.rootItem,false); log("importFiles（次で配置）"); }
else{
  var idx=-1;
  for(var k=0;k<V1.clips.numItems;k++) if(Math.round(Number(V1.clips[k].start.ticks)/TPF)===C5F0) idx=k;
  log("c05 差し替え前 = "+V1.clips[idx].name);
  V1.clips[idx].remove(false,false);
  var a=new Time(); a.seconds=C5TIN;                  item.setInPoint(a,4);
  var b=new Time(); b.seconds=C5TIN+(C5NF+2)/30.0;    item.setOutPoint(b,4);
  V1.overwriteClip(item, T(C5F0*TPF));
  var ni=-1;
  for(var k=0;k<V1.clips.numItems;k++) if(Math.round(Number(V1.clips[k].start.ticks)/TPF)===C5F0) ni=k;
  V1.clips[ni].end=T(C5F1*TPF);
  var nx=V1.clips[ni+1];
  if(nx && Math.round(Number(nx.start.ticks)/TPF)!==C5F1){ nx.start=T(C5F1*TPF); log("★次のクリップの頭を"+C5F1+"Fへ戻した"); }
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
  log("c05 差し替え後 = a0928 tin="+seq.videoTracks[0].clips[ni].inPoint.seconds.toFixed(3));
}
// ===== c04: もっと寄る（ズーム 100→110 を 115→135 へ）=====
// ===== 全ショットのズームを inPoint 基準で打ち直す（差し替えの副作用対策）=====
var TOP={0:[100,120,110]};   // c01はパンチ
for(var k=0;k<V1.clips.numItems;k++){
  var cl=V1.clips[k];
  var sf=Math.round(Number(cl.start.ticks)/TPF), ef=Math.round(Number(cl.end.ticks)/TPF);
  var OFF=cl.inPoint.seconds, NF=ef-sf;
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q];
    if(cp.displayName!=="トランスフォーム") continue;
    for(var r=0;r<cp.properties.numItems;r++) if(cp.properties[r].displayName==="縦横比を固定") cp.properties[r].setValue(true,true);
    for(var r=0;r<cp.properties.numItems;r++){
      var p=cp.properties[r], pn=p.displayName;
      if(pn!=="スケール" && pn!=="スケール (高さ)") continue;
      var tv=false; try{ tv=p.isTimeVarying(); }catch(e){}
      if(tv) p.setTimeVarying(false);
      p.setValue(100,true); p.setTimeVarying(true);
      if(k===0){
        p.addKey(OFF+0);    p.setValueAtKey(OFF+0,100,true);
        p.addKey(OFF+4/30); p.setValueAtKey(OFF+4/30,120,true);
        p.addKey(OFF+6/30); p.setValueAtKey(OFF+6/30,110,true);
      } else if(k===6){                      // c04 もっと寄る
        p.addKey(OFF+0);         p.setValueAtKey(OFF+0,115,true);
        p.addKey(OFF+(NF-1)/30); p.setValueAtKey(OFF+(NF-1)/30,135,true);
      } else {
        p.addKey(OFF+0);         p.setValueAtKey(OFF+0,100,true);
        p.addKey(OFF+(NF-1)/30); p.setValueAtKey(OFF+(NF-1)/30,115,true);
      }
      break;
    }
    for(var r=0;r<cp.properties.numItems;r++){}
  }
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q];
    if(cp.displayName!=="Lumetri カラー") continue;
    for(var r=0;r<cp.properties.numItems;r++){ var p=cp.properties[r];
      if(p.displayName==="彩度"){ try{ if(Number(p.getValue())===100){ p.setValue(106,true); break; } }catch(e){} } }
  }
}
log("--- 全ショットのズームを打ち直した ---");
var ng=0, prev=0, gaps=0;
for(var k=0;k<V1.clips.numItems;k++){
  var cl=V1.clips[k];
  var sf=Math.round(Number(cl.start.ticks)/TPF), ef=Math.round(Number(cl.end.ticks)/TPF);
  if(sf!==prev) gaps++;
  prev=ef;
  var OFF=cl.inPoint.seconds, NF=ef-sf, keys="なし";
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q];
    if(cp.displayName!=="トランスフォーム") continue;
    for(var r=0;r<cp.properties.numItems;r++){
      var p=cp.properties[r], pn=p.displayName;
      if(pn!=="スケール" && pn!=="スケール (高さ)") continue;
      var tv=false; try{ tv=p.isTimeVarying(); }catch(e){}
      if(!tv) continue;
      var ks=p.getKeys(), arr=[];
      for(var z=0;z<ks.length;z++) arr.push(Math.round((ks[z].seconds-OFF)*30)+"F:"+p.getValueAtKey(ks[z]));
      keys=arr.join("/");
      if(Math.abs(ks[0].seconds-OFF)>0.01) ng++;
    }
  }
  log("  ["+k+"] "+sf+"-"+ef+"F "+cl.name.substring(0,26)+"  "+keys);
}
log("隙間/重なり="+gaps+"  キーの頭ズレ="+ng+"（0が正常）");
proj.save();
seq.setInPoint(T(0)); seq.setOutPoint(T(337*TPF));
log("書き出し= "+seq.exportAsMediaDirect("@@FERIEST_ROOT@@/02_work/premiere/verify_20260809/v9",EPR,1));
}
var f=new File("@@BRIDGE_DIR@@/z08.txt"); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
