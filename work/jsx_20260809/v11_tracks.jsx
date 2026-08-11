var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v11.txt";
var REF="6822d0d1-041a-46a0-a5ff-735087200a01";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===REF) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0.7人前うどん") seq=proj.sequences[s];
for(var v=0;v<seq.videoTracks.numTracks;v++){
  var tr=seq.videoTracks[v];
  log("=== V"+v+"  clips="+tr.clips.numItems);
  for(var k=0;k<tr.clips.numItems;k++){
    var cl=tr.clips[k];
    var mp="", isSeq="";
    try{ if(cl.projectItem){ mp=cl.projectItem.getMediaPath(); isSeq=cl.projectItem.isSequence()?" [ネスト]":""; } }catch(e){}
    var mg=""; try{ mg = cl.getMGTComponent()? "MOGRT":""; }catch(e){}
    var kind = mp? "media" : (cl.projectItem? "item(パスなし)" : "★Graphic(ネイティブ)");
    log("  ["+k+"] "+cl.name+"  "+cl.start.seconds.toFixed(2)+"-"+cl.end.seconds.toFixed(2)+"  "+kind+isSeq+" "+mg);
  }
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
