var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v08.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var REF="6822d0d1-041a-46a0-a5ff-735087200a01";
var TPF=8467200000;  // 1フレーム(30fps)のticks
var BASE="@@FERIEST_ROOT@@/00_source_drive/20260807_新素材_8月掲載分/海老ドーン贅沢ぷりぷり海老マヨピザ/";
// cut_key, path, 素材tin秒, 開始F, 終了F
var CUTS=[
 ["0801_c01", BASE+"IMG_2856.MOV",              7.533,   0,  28],
 ["0801_c02", BASE+"IMG_2852.MOV",              1.700,  28,  86],
 ["0801_c03", BASE+"20260803_honma_a0931.MP4",  3.370,  86, 162],
 ["0801_c04", BASE+"20260803_honma_a0920.MP4",  8.110, 162, 227],
 ["0801_c05", BASE+"20260803_honma_a0933.MP4", 43.800, 227, 282],
 ["0801_c06", BASE+"IMG_2848.MOV",              2.300, 282, 337]
];
function T(ticks){ var t=new Time(); t.ticks=String(ticks); return t; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
if(!proj){ log("★中断: 対象なし"); }
else if(proj.documentID===REF){ log("★★★中断: 参考と同一ID"); }
else{
  var seq=null;
  for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
  if(!seq){ log("★中断: seqなし"); }
  else{
    function findByPath(path,bin){
      for(var i=0;i<bin.children.numItems;i++){
        var it=bin.children[i];
        if(it.type===ProjectItemType.BIN){ var r=findByPath(path,it); if(r) return r; }
        else { var mp=""; try{ mp=it.getMediaPath(); }catch(e){} if(mp===path) return it; }
      }
      return null;
    }
    var V1=seq.videoTracks[0];
    for(var k=V1.clips.numItems-1;k>=0;k--) V1.clips[k].remove(false,false);
    log("V1クリア clips="+V1.clips.numItems);
    for(var c=0;c<CUTS.length;c++){
      var key=CUTS[c][0], path=CUTS[c][1], tin=CUTS[c][2], f0=CUTS[c][3], f1=CUTS[c][4];
      var item=findByPath(path,proj.rootItem);
      if(!item){ log("★"+key+" 素材なし"); continue; }
      var nf=f1-f0;
      var a=new Time(); a.seconds=tin;                item.setInPoint(a,4);
      var b=new Time(); b.seconds=tin+(nf+2)/30.0;    item.setOutPoint(b,4);  // 余裕2F
      V1.overwriteClip(item, T(f0*TPF));
    }
    // フレーム格子へ厳密に詰める
    for(var k=0;k<V1.clips.numItems && k<CUTS.length;k++){
      V1.clips[k].end = T(CUTS[k][4]*TPF);
    }
    log("--- 実測（frame単位） ---");
    var gaps=0, prev=0;
    for(var k=0;k<V1.clips.numItems;k++){
      var cl=V1.clips[k];
      var sf=Math.round(Number(cl.start.ticks)/TPF), ef=Math.round(Number(cl.end.ticks)/TPF);
      if(sf!==prev){ gaps++; log("  ★隙間/重なり: 期待"+prev+"F だが start="+sf+"F"); }
      prev=ef;
      log("  ["+k+"] "+cl.name+"  "+sf+"F - "+ef+"F  尺"+(ef-sf)+"F  ("+(sf/30).toFixed(4)+"-"+(ef/30).toFixed(4)+"s)");
    }
    log("隙間/重なり件数="+gaps+"  （0が正常）");
    log("総フレーム="+prev+"F = "+(prev/30).toFixed(4)+"秒");
    proj.save();
    log("save 実行");
  }
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
