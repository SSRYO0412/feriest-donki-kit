var L=[]; function log(s){L.push(String(s));}
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
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q];
    if(cp.displayName!=="トランスフォーム") continue;
    for(var r=0;r<cp.properties.numItems;r++){
      var p=cp.properties[r], pn=p.displayName;
      if(pn!=="スケール" && pn!=="スケール (高さ)") continue;
      var tv=false; try{ tv=p.isTimeVarying(); }catch(e){}
      if(!tv) continue;
      var ks=p.getKeys();
      if(Math.abs(ks[0].seconds-OFF)<=0.01) break;   // ずれていないものは触らない
      var top = (k===6) ? 110 : 115;                  // c04(162-227F)だけ110
      p.setTimeVarying(false); p.setValue(100,true); p.setTimeVarying(true);
      p.addKey(OFF+0);         p.setValueAtKey(OFF+0,100,true);
      p.addKey(OFF+(NF-1)/30); p.setValueAtKey(OFF+(NF-1)/30,top,true);
      var k2=p.getKeys(), arr=[];
      for(var z=0;z<k2.length;z++) arr.push(Math.round((k2[z].seconds-OFF)*30)+"F:"+p.getValueAtKey(k2[z]));
      log("["+k+"] "+sf+"-"+ef+"F 打ち直し keys="+arr.join("/"));
      break;
    }
  }
}
proj.save(); log("save");
var f=new File("@@BRIDGE_DIR@@/z02.txt"); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
