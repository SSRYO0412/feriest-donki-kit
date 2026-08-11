var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v07.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var REF="6822d0d1-041a-46a0-a5ff-735087200a01";
var BASE="@@FERIEST_ROOT@@/00_source_drive/20260807_新素材_8月掲載分/海老ドーン贅沢ぷりぷり海老マヨピザ/";
// cut_key, mediaPath, 素材tin, 尺, 動画内開始秒
var CUTS=[
 ["0801_c01", BASE+"IMG_2856.MOV",              7.533, 0.92, 0.00],
 ["0801_c02", BASE+"IMG_2852.MOV",              1.700, 1.95, 0.92],
 ["0801_c03", BASE+"20260803_honma_a0931.MP4",  3.370, 2.52, 2.87],
 ["0801_c04", BASE+"20260803_honma_a0920.MP4",  8.110, 2.17, 5.39],
 ["0801_c05", BASE+"20260803_honma_a0933.MP4", 43.800, 1.83, 7.56],
 ["0801_c06", BASE+"IMG_2848.MOV",              2.300, 1.83, 9.39]
];
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
    // 既存クリップを後ろから撤去（敷き直し方式）
    for(var k=V1.clips.numItems-1;k>=0;k--) V1.clips[k].remove(false,false);
    log("V1 クリア後 clips="+V1.clips.numItems);

    var ok=0;
    for(var c=0;c<CUTS.length;c++){
      var key=CUTS[c][0], path=CUTS[c][1], tin=CUTS[c][2], dur=CUTS[c][3], at=CUTS[c][4];
      var item=findByPath(path,proj.rootItem);
      if(!item){ log("★"+key+" 素材が見つからない: "+path); continue; }
      var a=new Time(); a.seconds=tin;      item.setInPoint(a,4);
      var b=new Time(); b.seconds=tin+dur;  item.setOutPoint(b,4);
      var t=new Time(); t.seconds=at;
      V1.overwriteClip(item,t);
      ok++;
    }
    log("配置 ok="+ok+" / "+CUTS.length+"  V1 clips="+V1.clips.numItems);
    // 尺を設計値へ詰める（overwriteClip は1F長く置くことがある）
    for(var k=0;k<V1.clips.numItems && k<CUTS.length;k++){
      var cl=V1.clips[k];
      var want=CUTS[k][4]+CUTS[k][3];
      var e=new Time(); e.seconds=want; cl.end=e;
    }
    log("--- 実測 ---");
    for(var k=0;k<V1.clips.numItems;k++){
      var cl=V1.clips[k];
      log("  ["+k+"] "+cl.name+"  start="+cl.start.seconds.toFixed(3)+" end="+cl.end.seconds.toFixed(3)+" dur="+(cl.end.seconds-cl.start.seconds).toFixed(3)+" inPoint="+cl.inPoint.seconds.toFixed(3));
    }
    log("seq.end="+seq.end);
    proj.save();
    log("save 実行");
  }
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
