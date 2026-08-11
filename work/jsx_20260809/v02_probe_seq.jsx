var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v02.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
if(!proj){ log("★中断: 対象なし"); }
else{
  log("proj="+proj.name+" path="+proj.path);
  var seq=null;
  for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
  if(!seq){ log("★中断: seqなし"); }
  else{
    log("seq="+seq.name+" id="+seq.sequenceID);
    var st=seq.getSettings();
    var keys=[];
    for(var k in st) keys.push(k);
    log("settings keys("+keys.length+"): "+keys.join(","));
    log("videoFrameWidth="+st.videoFrameWidth);
    log("videoFrameHeight="+st.videoFrameHeight);
    log("videoFrameRate="+st.videoFrameRate);
    log("videoPixelAspectRatio="+st.videoPixelAspectRatio);
    log("typeof seq.setSettings="+(typeof seq.setSettings));
    log("V tracks="+seq.videoTracks.numTracks+" A tracks="+seq.audioTracks.numTracks);
  }
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok "+L.length;
