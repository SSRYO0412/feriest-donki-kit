var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/u08.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var TPF=8467200000;
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var V1=seq.videoTracks[0];
for(var k=0;k<V1.clips.numItems;k++){
  var cl=V1.clips[k];
  var sf=Math.round(Number(cl.start.ticks)/TPF), ef=Math.round(Number(cl.end.ticks)/TPF);
  var OFF=cl.inPoint.seconds, NF=ef-sf;
  var comps=[];
  for(var q=0;q<cl.components.numItems;q++) comps.push(cl.components[q].displayName);
  var line="c0"+(k+1)+" "+sf+"-"+ef+"F ("+NF+"F) inPoint="+OFF.toFixed(3)+"  comps=["+comps.join("|")+"]";
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q];
    if(cp.displayName!=="トランスフォーム") continue;
    for(var r=0;r<cp.properties.numItems;r++){
      var p=cp.properties[r];
      if(p.displayName==="縦横比を固定") line+="  固定="+p.getValue();
      if(p.displayName==="スケール (高さ)"){
        var ks=p.getKeys(); var arr=[];
        for(var z=0;z<ks.length;z++) arr.push(Math.round((ks[z].seconds-OFF)*30)+"F:"+p.getValueAtKey(ks[z]));
        line+="  keys="+(arr.length?arr.join("/"):"なし")+"  頭ズレ="+(ks.length?Math.abs(ks[0].seconds-OFF).toFixed(4):"-");
      }
    }
  }
  log(line);
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
