var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/u10.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var TPF=8467200000;
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var V1=seq.videoTracks[0];
for(var k=0;k<V1.clips.numItems;k++){
  var cl=V1.clips[k];
  log("=== c0"+(k+1)+" "+cl.name+"  components="+cl.components.numItems);
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q];
    var ps=[];
    for(var r=0;r<cp.properties.numItems;r++){
      var p=cp.properties[r];
      var tv=""; try{ tv=p.isTimeVarying()?"[可変"+p.getKeys().length+"]":""; }catch(e){ tv="[?]"; }
      ps.push(p.displayName+tv);
    }
    log("   ["+q+"] "+cp.displayName+" ("+cp.properties.numItems+"): "+ps.join(" / "));
  }
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
