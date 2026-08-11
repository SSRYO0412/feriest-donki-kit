var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v03.txt";
var REF="6822d0d1-041a-46a0-a5ff-735087200a01";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===REF) proj=app.projects[i];
if(!proj){ log("★中断: うどんが開いていない"); }
else{
  log("REF proj="+proj.name);
  for(var s=0;s<proj.sequences.numSequences;s++){
    var q=proj.sequences[s];
    var st=q.getSettings();
    log("--- SEQ["+s+"] "+q.name);
    log("    "+st.videoFrameWidth+"x"+st.videoFrameHeight+"  par="+st.videoPixelAspectRatio);
    log("    frameRate.ticks="+st.videoFrameRate.ticks+"  seconds="+st.videoFrameRate.seconds);
    log("    editingMode="+st.editingMode+"  fieldType="+st.videoFieldType);
    log("    V="+q.videoTracks.numTracks+" A="+q.audioTracks.numTracks);
    log("    end="+q.end);
  }
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
