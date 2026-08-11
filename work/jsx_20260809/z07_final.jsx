var L=[]; function log(s){L.push(String(s));}
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39"; var TPF=8467200000, TOTAL=337;
var EXP={0:337,1:337,2:337,3:337,4:337,5:337,6:227,7:227,8:28};
var EPR="@@AME_PRESET@@";
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var ec=seq.videoTracks[8].clips[0];
for(var q=0;q<ec.components.numItems;q++){
  var cp=ec.components[q];
  if(cp.displayName!=="モーション") continue;
  for(var r=0;r<cp.properties.numItems;r++)
    if(cp.properties[r].displayName==="位置") cp.properties[r].setValue([989/1080.0,869.5/1920.0],true);
}
log("🍤 位置=px(989, 870)  左端935 右端1043（本文の最大右端915から20px空く）");
// 全数検算
var gaps=0,dup=0,runbad=0,endbad=0,used={};
for(var v=0;v<seq.videoTracks.numTracks;v++){
  var tr=seq.videoTracks[v]; if(!tr.clips.numItems) continue;
  var prev=0;
  for(var k=0;k<tr.clips.numItems;k++){
    var cl=tr.clips[k];
    var sf=Math.round(Number(cl.start.ticks)/TPF), ef=Math.round(Number(cl.end.ticks)/TPF);
    if(v===0){ if(sf!==prev) gaps++; prev=ef;
      var key=cl.name+"@"+cl.inPoint.seconds.toFixed(2);
      if(used[key]) dup++; else used[key]=1; }
    var m=null; try{ m=cl.getMGTComponent(); }catch(e){}
    if(m){ var txt="",rl="";
      for(var q=0;q<m.properties.numItems;q++){ var p=m.properties[q];
        if(p.displayName==="本文"){ var b=p.getValue();
          txt=(b.match(/"textEditValue":"([^"]*)"/)||["",""])[1];
          rl=(b.match(/"fontTextRunLength":\[([^\]]*)\]/)||["",""])[1]; } }
      if(String(txt.length)!==String(rl)) runbad++; }
  }
  var e=Math.round(Number(tr.clips[tr.clips.numItems-1].end.ticks)/TPF);
  if(e!==EXP[v]){ endbad++; log("★V"+(v+1)+" 終端="+e+"F 期待"+EXP[v]+"F"); }
}
log("隙間/重なり="+gaps+"  重複="+dup+"  run長不一致="+runbad+"  終端ずれ="+endbad+"（全て0が正常）");
proj.save();
seq.setInPoint(T(0)); seq.setOutPoint(T(TOTAL*TPF));
log("書き出し= "+seq.exportAsMediaDirect("@@FERIEST_ROOT@@/02_work/premiere/verify_20260809/v8",EPR,1));
var f=new File("@@BRIDGE_DIR@@/z07.txt"); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
