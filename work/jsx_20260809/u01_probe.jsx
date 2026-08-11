var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/u01.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
if(!proj){ log("★対象プロジェクトが開いていない"); }
else{
  log("proj="+proj.name+"  seqs="+proj.sequences.numSequences);
  var seq=null;
  for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
  log("seq="+(seq?seq.name:"なし"));
  if(seq){
    log("exportFramePNG="+(typeof seq.exportFramePNG));
    log("exportAsMediaDirect="+(typeof seq.exportAsMediaDirect));
    log("videoTracks="+seq.videoTracks.numTracks);
    // V3(上段) と V7(下段) の 縦位置 を読む
    var names=["V1","V2","V3","V4","V5","V6","V7"];
    for(var v=2;v<seq.videoTracks.numTracks;v++){
      var tr=seq.videoTracks[v];
      for(var k=0;k<tr.clips.numItems;k++){
        var m=null; try{m=tr.clips[k].getMGTComponent();}catch(e){}
        if(!m) continue;
        var txt="",vp="",fs="";
        for(var q=0;q<m.properties.numItems;q++){
          var p=m.properties[q],n=p.displayName;
          if(n==="本文"){var b=p.getValue();var a1=b.match(/"textEditValue":"([^"]*)"/);txt=a1?a1[1]:"?";
            var a3=b.match(/"fontSizeEditValue":\[([^\]]*)\]/);fs=a3?a3[1]:"?";}
          if(n==="縦位置") vp=p.getValue();
        }
        log("  V"+(v+1)+"["+k+"] 「"+txt+"」 size="+fs+" 縦位置="+vp);
        break;
      }
    }
  }
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
