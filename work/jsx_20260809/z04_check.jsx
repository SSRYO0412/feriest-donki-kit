var L=[]; function log(s){L.push(String(s));}
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39"; var TPF=8467200000;
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var V1=seq.videoTracks[0];
for(var k=0;k<V1.clips.numItems;k++){
  var cl=V1.clips[k];
  var mp=""; try{ mp=cl.projectItem.getMediaPath(); }catch(e){}
  log("["+k+"] "+Math.round(Number(cl.start.ticks)/TPF)+"-"+Math.round(Number(cl.end.ticks)/TPF)+"F tin="+cl.inPoint.seconds.toFixed(3)+"  "+mp.split("/").pop());
}
var f=new File("@@BRIDGE_DIR@@/z04.txt"); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
