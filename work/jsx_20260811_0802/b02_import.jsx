var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/b02.txt";
var DOC=null;
for(var i=0;i<app.projects.numProjects;i++)
  if(app.projects[i].path && app.projects[i].path.indexOf("FERIEST_0802_spray_v1")>=0) DOC=app.projects[i];
if(!DOC){ log("★対象なし"); }
else{
var S="@@FERIEST_ROOT@@/00_source_drive/20260807_新素材_8月掲載分/ド情熱逆さで使える消臭スプレー&速乾防水スプレー/";
var FILES=[S+"IMG_8708.MOV",S+"IMG_8710.MOV",S+"IMG_8703.MOV",
 S+"20260803_honma_a0783.MP4",S+"20260803_honma_a0782.MP4",S+"20260803_honma_a0781.MP4",
 S+"20260803_honma_a0785.MP4",S+"20260803_honma_a0786.MP4",S+"20260803_honma_a0787.MP4",
 S+"20260803_honma_a0804.MP4",S+"20260803_honma_a0803.MP4",S+"20260803_honma_a0802.MP4",
 S+"20260803_honma_a0798.MP4",
 "@@KIT_ROOT@@/data/reference/月乗りドンペン.jpg",
 "@@KIT_ROOT@@/skill/donki-feriest/assets/1f447.png",
 "@@FERIEST_ROOT@@/02_work/premiere/assets_emoji/1f602.png"];
var miss=[];
for(var k=0;k<FILES.length;k++){ var f=new File(FILES[k]); if(!f.exists) miss.push(FILES[k]); }
if(miss.length){ log("★実体なし:"+miss.join(",")); }
else{
  DOC.importFiles(FILES,true,DOC.rootItem,false);
  function count(bin){ var n=0;
    for(var i=0;i<bin.children.numItems;i++){ var it=bin.children[i];
      if(it.type===ProjectItemType.BIN) n+=count(it); else n++; }
    return n; }
  log("import done. items="+count(DOC.rootItem));
  DOC.save();
}}
var f2=new File(OUT); f2.open("w"); f2.write(L.join("\n")); f2.close();
return "done";
