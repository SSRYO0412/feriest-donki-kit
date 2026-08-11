var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v04.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var REF="6822d0d1-041a-46a0-a5ff-735087200a01";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
if(!proj){ log("★中断: 対象なし"); }
else if(proj.documentID===REF){ log("★★★中断: 参考と同一ID"); }
else{
  var seq=null;
  for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
  if(!seq){ log("★中断: seqなし"); }
  else{
    var st=seq.getSettings();
    log("before "+st.videoFrameWidth+"x"+st.videoFrameHeight+" ticks="+st.videoFrameRate.ticks);
    st.videoFrameWidth=1080;
    st.videoFrameHeight=1920;
    var t=new Time(); t.ticks="8467200000"; st.videoFrameRate=t;
    st.videoPixelAspectRatio="1:1";
    st.editingMode="795454d9-d3c2-429d-9474-923ab13b7018";
    st.videoFieldType=0;
    seq.setSettings(st);
    var st2=seq.getSettings();
    log("after  "+st2.videoFrameWidth+"x"+st2.videoFrameHeight+" ticks="+st2.videoFrameRate.ticks+" par="+st2.videoPixelAspectRatio);
    log("editingMode="+st2.editingMode+" fieldType="+st2.videoFieldType);
    log("判定: "+((st2.videoFrameWidth==1080 && st2.videoFrameHeight==1920 && String(st2.videoFrameRate.ticks)=="8467200000")?"OK 一致":"★不一致"));
    proj.save();
    log("save 実行");
  }
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
