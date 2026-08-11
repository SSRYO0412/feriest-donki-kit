var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/u02.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var REF="6822d0d1-041a-46a0-a5ff-735087200a01";
var BASE="@@FERIEST_ROOT@@/00_source_drive/20260807_新素材_8月掲載分/海老ドーン贅沢ぷりぷり海老マヨピザ/";
var NEW=BASE+"20260803_honma_a0924.MP4";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
if(!proj){ log("★中断: 対象プロジェクトなし"); }
else if(proj.documentID===REF){ log("★★★中断: 参考と同一ID"); }
else{
  log("proj="+proj.name+" seqs="+proj.sequences.numSequences);
  function findByPath(path,bin){
    for(var i=0;i<bin.children.numItems;i++){
      var it=bin.children[i];
      if(it.type===ProjectItemType.BIN){ var r=findByPath(path,it); if(r) return r; }
      else { var mp=""; try{ mp=it.getMediaPath(); }catch(e){} if(mp===path) return it; }
    }
    return null;
  }
  var ex=findByPath(NEW,proj.rootItem);
  if(ex){ log("既に読み込み済み: "+ex.name); }
  else{
    var f=new File(NEW);
    log("ファイル存在="+f.exists);
    proj.importFiles([NEW],true,proj.rootItem,false);
    log("importFiles 呼び出し（非同期）。次のスクリプトで確認する");
  }
}
var fo=new File(OUT); fo.encoding="UTF-8"; fo.lineFeed="Unix"; fo.open("w"); fo.write(L.join("\n")); fo.close();
return "ok";
