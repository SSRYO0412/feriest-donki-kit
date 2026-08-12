var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/b03.txt";
var TPF=8467200000;
var S="@@FERIEST_ROOT@@/00_source_drive/20260807_新素材_8月掲載分/ド情熱逆さで使える消臭スプレー&速乾防水スプレー/";
// name, file, tin(sec), startF, endF, baseScale, zoomKeys(フレーム:文法値)
var SH=[
 ["c01","IMG_8708.MOV",4.30,0,20,100,[[0,100],[4,120],[6,110]]],
 ["c02","IMG_8710.MOV",1.20,20,36,100,[[0,100],[16,112]]],
 ["c03","IMG_8703.MOV",9.50,36,56,100,[[0,100],[20,112]]],
 ["c04","20260803_honma_a0783.MP4",0.50,56,82,50,[[0,100],[26,115]]],
 ["c05","20260803_honma_a0782.MP4",12.90,82,108,50,[[0,100],[26,115]]],
 ["c06","20260803_honma_a0781.MP4",4.00,108,160,50,[[0,100],[52,115]]],
 ["c07","20260803_honma_a0785.MP4",3.60,160,174,50,[[0,100],[14,112]]],
 ["c08","20260803_honma_a0786.MP4",4.60,174,188,50,[[0,100],[14,112]]],
 ["c09","20260803_honma_a0787.MP4",14.20,188,202,50,[[0,100],[14,112]]],
 ["c10","20260803_honma_a0804.MP4",37.60,202,232,50,[[0,100],[30,112]]],
 ["c11","20260803_honma_a0803.MP4",1.80,232,246,89,[[0,100],[14,106]]],
 ["c12","20260803_honma_a0802.MP4",2.00,246,274,50,[[0,100],[28,112]]],
 ["c13","20260803_honma_a0798.MP4",17.50,274,316,50,[[0,100],[42,112]]]];
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++)
  if(app.projects[i].path && app.projects[i].path.indexOf("FERIEST_0802_spray_v1")>=0) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++)
  if(proj.sequences[s].name==="0802_spray") seq=proj.sequences[s];
proj.openSequence(seq.sequenceID);
function findByPath(p,bin){
  for(var i=0;i<bin.children.numItems;i++){ var it=bin.children[i];
    if(it.type===ProjectItemType.BIN){ var r=findByPath(p,it); if(r) return r; }
    else { var mp=""; try{ mp=it.getMediaPath(); }catch(e){} if(mp===p) return it; } }
  return null; }
var V1=seq.videoTracks[0];
for(var k=V1.clips.numItems-1;k>=0;k--) V1.clips[k].remove(false,false);
V1=seq.videoTracks[0];
for(var k=0;k<SH.length;k++){
  var sh=SH[k];
  var item=findByPath(S+sh[1],proj.rootItem);
  if(!item){ log("★item無し "+sh[1]); continue; }
  var durF=sh[4]-sh[3];
  var ia=new Time(); ia.seconds=sh[2];              item.setInPoint(ia,4);
  var ib=new Time(); ib.seconds=sh[2]+durF/30+0.4;  item.setOutPoint(ib,4);
  V1.overwriteClip(item, T(sh[3]*TPF));
  V1=seq.videoTracks[0];
  var cl=V1.clips[V1.clips.numItems-1];
  cl.end=T(sh[4]*TPF);
  // モーション: スケールキー(inPoint基準)・c11は位置も
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q];
    if(cp.displayName!=="モーション") continue;
    var OFF=cl.inPoint.seconds;
    for(var r=0;r<cp.properties.numItems;r++){
      var pr=cp.properties[r], n=pr.displayName;
      if(n==="スケール"||n==="スケール (高さ)"||n==="スケール (幅)"){
        try{ pr.setTimeVarying(true); }catch(e){}
        for(var z=0;z<sh[6].length;z++){
          var tt=OFF+sh[6][z][0]/30;
          var val=sh[5]*sh[6][z][1]/100;
          try{ pr.addKey(tt); pr.setValueAtKey(tt,val,true); }catch(e){ log("★key例外 "+sh[0]+" "+n+":"+e); }
        }
      }
      if(sh[0]==="c11" && n==="位置"){
        try{ pr.setValue([0.85,0.5],true); }catch(e){ log("★c11位置例外:"+e); }
      }
    }
  }
}
V1=seq.videoTracks[0];
log("V1 clips="+V1.clips.numItems);
// 検算: 隙間・終端・キー頭(inPoint一致)
var bad=0, prevEnd=0;
for(var k=0;k<V1.clips.numItems;k++){
  var c=V1.clips[k];
  var st=Math.round(Number(c.start.ticks)/TPF), en=Math.round(Number(c.end.ticks)/TPF);
  if(st!==prevEnd){ log("★隙間/重なり at clip"+k+" start="+st+" prevEnd="+prevEnd); bad++; }
  prevEnd=en;
}
log("終端="+prevEnd+"F(期待316) 隙間検出="+bad);
// キー検算(分岐の外でカウント)
var noKey=0;
for(var k=0;k<V1.clips.numItems;k++){
  var c=V1.clips[k], found=0;
  for(var q=0;q<c.components.numItems;q++){
    var cp=c.components[q];
    if(cp.displayName!=="モーション") continue;
    for(var r=0;r<cp.properties.numItems;r++){
      var pr=cp.properties[r], n=pr.displayName;
      if(n==="スケール"||n==="スケール (高さ)"){
        var ks=null; try{ ks=pr.getKeys(); }catch(e){}
        if(ks && ks.length>=2 && Math.abs(ks[0].seconds-c.inPoint.seconds)<0.01) found=1;
      }
    }
  }
  if(!found){ noKey++; log("★キー無し/頭ズレ clip"+k); }
}
log("キー検算 NG="+noKey);
proj.save();
var f2=new File(OUT); f2.open("w"); f2.write(L.join("\n")); f2.close();
return "done";
