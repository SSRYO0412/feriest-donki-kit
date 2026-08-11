var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v06.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
if(!proj){ log("★中断: 対象なし"); }
else{
  var n=0;
  function walk(bin,d){
    for(var i=0;i<bin.children.numItems;i++){
      var it=bin.children[i];
      if(it.type===ProjectItemType.BIN){ walk(it,d+1); }
      else{
        var mp=""; try{ mp=it.getMediaPath(); }catch(e){ mp="(取得不可)"; }
        n++;
        log(n+". name="+it.name);
        log("     path="+mp);
      }
    }
  }
  walk(proj.rootItem,0);
  log("=== 項目数="+n);
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
