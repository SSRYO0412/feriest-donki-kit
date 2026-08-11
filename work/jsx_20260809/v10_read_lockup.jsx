var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v10.txt";
var REF="6822d0d1-041a-46a0-a5ff-735087200a01";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===REF) proj=app.projects[i];
if(!proj){ log("★中断: うどん未オープン"); }
else{
  var seq=null;
  for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0.7人前うどん") seq=proj.sequences[s];
  if(!seq){ log("★中断: 本編seqなし"); }
  else{
    log("REF seq="+seq.name+"  V="+seq.videoTracks.numTracks);
    for(var v=0;v<seq.videoTracks.numTracks;v++){
      var tr=seq.videoTracks[v];
      if(tr.clips.numItems===0) continue;
      log("--- V"+v+"  clips="+tr.clips.numItems);
      for(var k=0;k<tr.clips.numItems;k++){
        var cl=tr.clips[k];
        var mp=""; try{ mp=cl.projectItem?cl.projectItem.getMediaPath():""; }catch(e){}
        var isLogo = (mp.indexOf("ドンペン")>=0) || (mp.indexOf("1f447")>=0);
        if(!isLogo && k>2) continue;
        var sc="", po="";
        for(var q=0;q<cl.components.numItems;q++){
          var cp=cl.components[q];
          if(cp.displayName!=="モーション") continue;
          for(var r=0;r<cp.properties.numItems;r++){
            var pr=cp.properties[r];
            if(pr.displayName==="スケール") sc=pr.getValue();
            if(pr.displayName==="位置") po=pr.getValue();
          }
        }
        log("  ["+k+"] "+cl.name+(isLogo?"  ★ロゴ素材":"")+"  start="+cl.start.seconds.toFixed(2)+" end="+cl.end.seconds.toFixed(2));
        if(mp) log("       path="+mp);
        if(sc!=="") log("       スケール="+sc+"  位置="+po+"  disabled="+cl.disabled);
      }
    }
  }
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
