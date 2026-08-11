var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ref_map.txt";
var REF="6822d0d1-041a-46a0-a5ff-735087200a01";
var TPF=8467200000;
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===REF) proj=app.projects[i];
if(!proj){ log("★中断: うどん未オープン"); }
else{
  var seq=null;
  for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0.7人前うどん") seq=proj.sequences[s];
  for(var v=0;v<seq.videoTracks.numTracks;v++){
    var tr=seq.videoTracks[v];
    if(tr.clips.numItems===0) continue;
    log("=== V"+v+"  clips="+tr.clips.numItems);
    for(var k=0;k<tr.clips.numItems;k++){
      var cl=tr.clips[k];
      var mp=""; try{ if(cl.projectItem) mp=cl.projectItem.getMediaPath(); }catch(e){}
      var kind = mp? "media" : (cl.projectItem? "item" : "Graphic");
      var sf=Math.round(Number(cl.start.ticks)/TPF), ef=Math.round(Number(cl.end.ticks)/TPF);
      var comps=[];
      for(var q=0;q<cl.components.numItems;q++) comps.push(cl.components[q].displayName);
      log("  ["+k+"] "+kind+" "+sf+"-"+ef+"F  "+cl.name+"  comps="+comps.join("|"));
    }
  }
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
