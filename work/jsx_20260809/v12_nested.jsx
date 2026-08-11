var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v12.txt";
var REF="6822d0d1-041a-46a0-a5ff-735087200a01";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===REF) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0.7用下サイド") seq=proj.sequences[s];
if(!seq){ log("★中断: 下サイドseqなし"); }
else{
  var st=seq.getSettings();
  log("下サイド "+st.videoFrameWidth+"x"+st.videoFrameHeight+"  V="+seq.videoTracks.numTracks+"  end="+seq.end);
  for(var v=0;v<seq.videoTracks.numTracks;v++){
    var tr=seq.videoTracks[v];
    if(tr.clips.numItems===0){ log("=== V"+v+" (空)"); continue; }
    log("=== V"+v+"  clips="+tr.clips.numItems);
    for(var k=0;k<tr.clips.numItems;k++){
      var cl=tr.clips[k];
      var mp=""; try{ if(cl.projectItem) mp=cl.projectItem.getMediaPath(); }catch(e){}
      var kind = mp? "media" : (cl.projectItem? "item" : "★Graphic(ネイティブテキスト)");
      var sc="",po="";
      for(var q=0;q<cl.components.numItems;q++){
        var cp=cl.components[q];
        if(cp.displayName!=="モーション") continue;
        for(var r=0;r<cp.properties.numItems;r++){
          if(cp.properties[r].displayName==="スケール") sc=cp.properties[r].getValue();
          if(cp.properties[r].displayName==="位置") po=cp.properties[r].getValue();
        }
      }
      log("  ["+k+"] "+cl.name+"  "+cl.start.seconds.toFixed(2)+"-"+cl.end.seconds.toFixed(2)+"  "+kind);
      if(mp) log("       path="+mp);
      if(sc!=="") log("       スケール="+sc+" 位置="+po);
    }
  }
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
