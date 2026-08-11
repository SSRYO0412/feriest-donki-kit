var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v05.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
if(!proj){ log("★中断: 対象なし"); } else {
var FILES=[
  "@@FERIEST_ROOT@@/00_source_drive/20260807_新素材_8月掲載分/海老ドーン贅沢ぷりぷり海老マヨピザ/20260803_honma_a0920.MP4",
  "@@FERIEST_ROOT@@/00_source_drive/20260807_新素材_8月掲載分/海老ドーン贅沢ぷりぷり海老マヨピザ/20260803_honma_a0931.MP4",
  "@@FERIEST_ROOT@@/00_source_drive/20260807_新素材_8月掲載分/海老ドーン贅沢ぷりぷり海老マヨピザ/20260803_honma_a0933.MP4",
  "@@FERIEST_ROOT@@/00_source_drive/20260807_新素材_8月掲載分/海老ドーン贅沢ぷりぷり海老マヨピザ/IMG_2848.MOV",
  "@@FERIEST_ROOT@@/00_source_drive/20260807_新素材_8月掲載分/海老ドーン贅沢ぷりぷり海老マヨピザ/IMG_2852.MOV",
  "@@FERIEST_ROOT@@/00_source_drive/20260807_新素材_8月掲載分/海老ドーン贅沢ぷりぷり海老マヨピザ/IMG_2856.MOV",
  "@@KIT_ROOT@@/data/reference/月乗りドンペン.jpg",
  "@@KIT_ROOT@@/skill/donki-feriest/assets/1f447.png",
];

var missing=0;
for(var k=0;k<FILES.length;k++){ var ff=new File(FILES[k]); if(!ff.exists){ log("★存在しない: "+FILES[k]); missing++; } }
log("投入予定="+FILES.length+" 欠落="+missing);
if(missing===0){
  proj.importFiles(FILES, true, proj.rootItem, false);
  log("importFiles 実行（非同期なのでこの実行では列挙しない）");
} else { log("★中断: 欠落があるため取り込まない"); }
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
