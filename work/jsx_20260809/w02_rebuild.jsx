var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/w02.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var REF="6822d0d1-041a-46a0-a5ff-735087200a01";
var TPF=8467200000;
var B="@@FERIEST_ROOT@@/00_source_drive/20260807_新素材_8月掲載分/海老ドーン贅沢ぷりぷり海老マヨピザ/";
var CUTS=[
 ["c01  開封",             "IMG_2855.MOV",              3.730,   0,  28],
 ["c02a 海老が全面",       "20260803_honma_a0929.MP4",  3.050,  28,  57],
 ["c02b 持ち上げた具材面", "20260803_honma_a0925.MP4", 47.700,  57,  86],
 ["c03a 大粒の海老の艶",   "IMG_2852.MOV",             17.130,  86, 111],
 ["c03b チーズ伸び",       "20260803_honma_a0931.MP4",  3.370, 111, 136],
 ["c03c 切れかけ",         "IMG_2857.MOV",             17.600, 136, 162],
 ["c04  商品全景(谷)",     "20260803_honma_a0926.MP4",  4.300, 162, 227],
 ["c05  3人で取り分け",    "20260803_honma_a0933.MP4", 43.850, 227, 282],
 ["c06a 表面のパン",       "IMG_2848.MOV",              2.350, 282, 309],
 ["c06b 閉じたパッケージ", "IMG_2856.MOV",              7.533, 309, 337]
];
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
if(!proj){ log("★中断: 対象なし"); }
else if(proj.documentID===REF){ log("★★★中断: 参考と同一ID"); }
else{
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
if(!seq){ log("★中断: seqなし"); } else {
function findByPath(p,bin){
  for(var i=0;i<bin.children.numItems;i++){
    var it=bin.children[i];
    if(it.type===ProjectItemType.BIN){ var r=findByPath(p,it); if(r) return r; }
    else { var mp=""; try{ mp=it.getMediaPath(); }catch(e){} if(mp===p) return it; }
  }
  return null;
}
var miss=[];
for(var c=0;c<CUTS.length;c++) if(!findByPath(B+CUTS[c][1],proj.rootItem)) miss.push(CUTS[c][1]);
if(miss.length){ log("★中断: 素材が見つからない = "+miss.join(", ")); }
else{
  var V1=seq.videoTracks[0];
  for(var k=V1.clips.numItems-1;k>=0;k--) V1.clips[k].remove(false,false);
  log("V1クリア clips="+V1.clips.numItems);
  for(var c=0;c<CUTS.length;c++){
    var path=B+CUTS[c][1], tin=CUTS[c][2], f0=CUTS[c][3], f1=CUTS[c][4];
    var item=findByPath(path,proj.rootItem);
    var nf=f1-f0;
    var a=new Time(); a.seconds=tin;               item.setInPoint(a,4);
    var b=new Time(); b.seconds=tin+(nf+2)/30.0;   item.setOutPoint(b,4);
    V1.overwriteClip(item, T(f0*TPF));
  }
  for(var k=V1.clips.numItems-1;k>=0;k--){ if(k<CUTS.length) V1.clips[k].end = T(CUTS[k][4]*TPF); }
  var prev=0,gaps=0;
  log("--- 配置結果 ---");
  for(var k=0;k<V1.clips.numItems;k++){
    var cl=V1.clips[k];
    var sf=Math.round(Number(cl.start.ticks)/TPF), ef=Math.round(Number(cl.end.ticks)/TPF);
    if(sf!==prev){ gaps++; log("  ★隙間/重なり 期待"+prev+"F → "+sf+"F"); }
    prev=ef;
    log("  ["+k+"] "+sf+"-"+ef+"F ("+(ef-sf)+"F) "+(CUTS[k]?CUTS[k][0]:"?")+"  "+cl.name);
  }
  log("隙間/重なり="+gaps+"（0が正常）  終端="+prev+"F  ショット数="+V1.clips.numItems);
  proj.save(); log("save");
}
}}
var fo=new File(OUT); fo.encoding="UTF-8"; fo.lineFeed="Unix"; fo.open("w"); fo.write(L.join("\n")); fo.close();
return "ok";
