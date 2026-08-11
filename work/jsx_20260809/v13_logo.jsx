var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v13.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var REF="6822d0d1-041a-46a0-a5ff-735087200a01";
var TPF=8467200000, TOTAL=337;
var LOGO="@@KIT_ROOT@@/data/reference/月乗りドンペン.jpg";
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
if(!proj){ log("★中断: 対象なし"); }
else if(proj.documentID===REF){ log("★★★中断: 参考と同一ID"); }
else{
  var seq=null;
  for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
  log("V tracks="+seq.videoTracks.numTracks);
  if(seq.videoTracks.numTracks<3){ log("★中断: Vトラック不足（QEでaddTracksが要る）"); }
  else{
    function findByPath(path,bin){
      for(var i=0;i<bin.children.numItems;i++){
        var it=bin.children[i];
        if(it.type===ProjectItemType.BIN){ var r=findByPath(path,it); if(r) return r; }
        else { var mp=""; try{ mp=it.getMediaPath(); }catch(e){} if(mp===path) return it; }
      }
      return null;
    }
    var item=findByPath(LOGO,proj.rootItem);
    if(!item){ log("★中断: ロゴ素材なし"); }
    else{
      var V2=seq.videoTracks[1];
      for(var k=V2.clips.numItems-1;k>=0;k--) V2.clips[k].remove(false,false);
      var a=new Time(); a.seconds=0;      item.setInPoint(a,4);
      var b=new Time(); b.seconds=TOTAL/30.0+1; item.setOutPoint(b,4);
      V2.overwriteClip(item, T(0));
      V2.clips[0].end = T(TOTAL*TPF);
      var cl=V2.clips[0];
      for(var q=0;q<cl.components.numItems;q++){
        var cp=cl.components[q];
        if(cp.displayName!=="モーション") continue;
        for(var r=0;r<cp.properties.numItems;r++){
          var pr=cp.properties[r];
          if(pr.displayName==="スケール") pr.setValue(17,true);
          if(pr.displayName==="位置")     pr.setValue([0.11597108596296,0.80156159250676],true);
        }
      }
      var sf=Math.round(Number(cl.start.ticks)/TPF), ef=Math.round(Number(cl.end.ticks)/TPF);
      log("V2 ロゴ: "+cl.name+"  "+sf+"F-"+ef+"F  ("+(sf/30).toFixed(3)+"-"+(ef/30).toFixed(3)+"s)");
      for(var q=0;q<cl.components.numItems;q++){
        var cp=cl.components[q];
        if(cp.displayName!=="モーション") continue;
        for(var r=0;r<cp.properties.numItems;r++){
          var pr=cp.properties[r];
          if(pr.displayName==="スケール") log("   スケール="+pr.getValue());
          if(pr.displayName==="位置")     log("   位置="+pr.getValue());
        }
      }
      proj.save(); log("save 実行");
    }
  }
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
