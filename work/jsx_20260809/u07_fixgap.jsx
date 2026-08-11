var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/u07.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var TPF=8467200000;
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var V1=seq.videoTracks[0];
var cl=V1.clips[4];
log("c05 修正前: "+Math.round(Number(cl.start.ticks)/TPF)+"F-"+Math.round(Number(cl.end.ticks)/TPF)+"F  inPoint="+cl.inPoint.seconds.toFixed(3));
cl.start = T(227*TPF);
cl = V1.clips[4];
var OFF = cl.inPoint.seconds;
log("c05 修正後: "+Math.round(Number(cl.start.ticks)/TPF)+"F-"+Math.round(Number(cl.end.ticks)/TPF)+"F  inPoint="+OFF.toFixed(3));
// 頭が2F伸びたのでズームのキーフレームを inPoint 基準で打ち直す
var NF = Math.round(Number(cl.end.ticks)/TPF) - Math.round(Number(cl.start.ticks)/TPF);
for(var q=0;q<cl.components.numItems;q++){
  var cp=cl.components[q];
  if(cp.displayName!=="トランスフォーム") continue;
  for(var r=0;r<cp.properties.numItems;r++){
    var p=cp.properties[r];
    if(p.displayName!=="スケール (高さ)") continue;
    var ks=p.getKeys();
    for(var z=ks.length-1;z>=0;z--) p.removeKey(ks[z]);
    p.setTimeVarying(true);
    p.addKey(OFF+0);          p.setValueAtKey(OFF+0,100,true);
    p.addKey(OFF+(NF-1)/30);  p.setValueAtKey(OFF+(NF-1)/30,115,true);
    var k2=p.getKeys(); var arr=[];
    for(var z=0;z<k2.length;z++) arr.push(Math.round((k2[z].seconds-OFF)*30)+"F:"+p.getValueAtKey(k2[z]));
    log("  c05 ズーム打ち直し keys="+arr.join(" / ")+"  尺"+NF+"F  先頭キーとinPointの差="+Math.abs(k2[0].seconds-OFF).toFixed(4)+"秒");
  }
}
// 全数検算
log("--- V1 全数 ---");
var prev=0,gaps=0;
for(var k=0;k<V1.clips.numItems;k++){
  var c=V1.clips[k];
  var sf=Math.round(Number(c.start.ticks)/TPF), ef=Math.round(Number(c.end.ticks)/TPF);
  if(sf!==prev){ gaps++; log("  ★隙間/重なり 期待"+prev+"F → "+sf+"F"); }
  prev=ef;
  log("  ["+k+"] "+sf+"-"+ef+"F ("+(ef-sf)+"F) "+c.name);
}
log("隙間/重なり="+gaps+"（0が正常）  終端="+prev+"F");
var endbad=0;
for(var v=0;v<seq.videoTracks.numTracks;v++){
  var tr=seq.videoTracks[v]; if(!tr.clips.numItems) continue;
  var e=Math.round(Number(tr.clips[tr.clips.numItems-1].end.ticks)/TPF);
  var exp=(v>=6)?227:337;
  if(e!==exp){ endbad++; log("★V"+(v+1)+" 終端="+e+"F 期待"+exp+"F"); }
}
log("終端ずれ="+endbad+"（0が正常）");
proj.save(); log("save");
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
