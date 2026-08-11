var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v21.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var TPF=8467200000;
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
log("Vトラック数="+seq.videoTracks.numTracks);
for(var v=0;v<seq.videoTracks.numTracks;v++){
  var tr=seq.videoTracks[v];
  log("=== V"+(v+1)+" (index "+v+")  clips="+tr.clips.numItems+"  muted="+tr.isMuted());
  for(var k=0;k<tr.clips.numItems;k++){
    var cl=tr.clips[k];
    var sf=Math.round(Number(cl.start.ticks)/TPF), ef=Math.round(Number(cl.end.ticks)/TPF);
    var m=null; try{ m=cl.getMGTComponent(); }catch(e){}
    var extra="";
    if(m){
      for(var q=0;q<m.properties.numItems;q++){
        var p=m.properties[q];
        if(p.displayName==="本文"){ var a=p.getValue().match(/"textEditValue":"([^"]*)"/); extra+=" 本文=「"+(a?a[1]:"?")+"」"; }
        if(p.displayName==="縦位置") extra+=" 縦位置="+p.getValue();
      }
    }
    log("  ["+k+"] "+cl.name+"  "+sf+"F-"+ef+"F  disabled="+cl.disabled+extra);
  }
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
