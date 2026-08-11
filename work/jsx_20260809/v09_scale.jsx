var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v09.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
if(!proj){ log("★中断: 対象なし"); }
else{
  var seq=null;
  for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
  var V1=seq.videoTracks[0];
  // まず1本目のコンポーネント/プロパティを全列挙
  var cl0=V1.clips[0];
  log("=== clip[0] のコンポーネント列挙 ===");
  for(var q=0;q<cl0.components.numItems;q++){
    var cp=cl0.components[q];
    var ps=[];
    for(var r=0;r<cp.properties.numItems;r++) ps.push(cp.properties[r].displayName);
    log("  ["+q+"] "+cp.displayName+" : "+ps.join(" / "));
  }
  // スケール設定
  var okc=0, fails=[];
  for(var k=0;k<V1.clips.numItems;k++){
    var cl=V1.clips[k], done=false;
    for(var q=0;q<cl.components.numItems && !done;q++){
      var cp=cl.components[q];
      if(cp.displayName!=="モーション") continue;
      for(var r=0;r<cp.properties.numItems;r++){
        var pr=cp.properties[r];
        if(pr.displayName==="スケール"){
          pr.setValue(88.889,true);
          done=true; break;
        }
      }
    }
    if(done) okc++; else fails.push(k);
  }
  log("=== スケール設定 ok="+okc+"/"+V1.clips.numItems+(fails.length?("  失敗="+fails.join(",")):""));
  log("=== 読み戻し（★これは検算ではない。最終判定は書き出した画素） ===");
  for(var k=0;k<V1.clips.numItems;k++){
    var cl=V1.clips[k];
    for(var q=0;q<cl.components.numItems;q++){
      var cp=cl.components[q];
      if(cp.displayName!=="モーション") continue;
      for(var r=0;r<cp.properties.numItems;r++){
        var pr=cp.properties[r];
        if(pr.displayName==="スケール") log("  ["+k+"] "+cl.name+" スケール="+pr.getValue());
        if(pr.displayName==="位置") log("        位置="+pr.getValue());
      }
    }
  }
  proj.save(); log("save 実行");
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
