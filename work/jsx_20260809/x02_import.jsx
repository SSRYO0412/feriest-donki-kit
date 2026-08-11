var L=[]; function log(s){L.push(String(s));}
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var REF="6822d0d1-041a-46a0-a5ff-735087200a01";
var P="@@FERIEST_ROOT@@/02_work/premiere/assets_emoji/1f364.png";
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
  if(findByPath(P,proj.rootItem)) log("済: 1f364.png");
  else { var f=new File(P); log("存在="+f.exists); proj.importFiles([P],true,proj.rootItem,false); log("importFiles 呼び出し（非同期）"); }
}
var fo=new File("@@BRIDGE_DIR@@/x02.txt"); fo.encoding="UTF-8"; fo.open("w"); fo.write(L.join("\n")); fo.close();
return "ok";
