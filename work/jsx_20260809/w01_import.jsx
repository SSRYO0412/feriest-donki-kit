var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/w01.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var REF="6822d0d1-041a-46a0-a5ff-735087200a01";
var B="@@FERIEST_ROOT@@/00_source_drive/20260807_新素材_8月掲載分/海老ドーン贅沢ぷりぷり海老マヨピザ/";
var NEED=["IMG_2855.MOV","20260803_honma_a0925.MP4","20260803_honma_a0929.MP4","IMG_2857.MOV","20260803_honma_a0926.MP4"];
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
if(!proj || proj.documentID===REF){ log("★中断"); }
else{
  function findByPath(p,bin){
    for(var i=0;i<bin.children.numItems;i++){
      var it=bin.children[i];
      if(it.type===ProjectItemType.BIN){ var r=findByPath(p,it); if(r) return r; }
      else { var mp=""; try{ mp=it.getMediaPath(); }catch(e){} if(mp===p) return it; }
    }
    return null;
  }
  var add=[];
  for(var k=0;k<NEED.length;k++){
    var p=B+NEED[k];
    if(findByPath(p,proj.rootItem)) log("済: "+NEED[k]);
    else { var f=new File(p); log("要import: "+NEED[k]+" 存在="+f.exists); add.push(p); }
  }
  if(add.length){ proj.importFiles(add,true,proj.rootItem,false); log("importFiles "+add.length+"件（非同期）"); }
  else log("追加不要");
}
var fo=new File(OUT); fo.encoding="UTF-8"; fo.lineFeed="Unix"; fo.open("w"); fo.write(L.join("\n")); fo.close();
return "ok";
