var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/w08.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var TPF=8467200000, TOTAL=337;
var EPR="@@AME_PRESET@@";
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var NAMES=["V1 カット","V2 ロゴ","V3 テロップ上段","V4 ロックアップ1","V5 ロックアップ2","V6 👇","V7 c04下段1","V8 c04下段2"];
var used={}, dup=0, runbad=0, gaps=0, endbad=0, prev=0;
for(var v=0;v<seq.videoTracks.numTracks;v++){
  var tr=seq.videoTracks[v];
  log("=== "+(NAMES[v]||("V"+(v+1)))+"  clips="+tr.clips.numItems);
  prev=0;
  for(var k=0;k<tr.clips.numItems;k++){
    var cl=tr.clips[k];
    var sf=Math.round(Number(cl.start.ticks)/TPF), ef=Math.round(Number(cl.end.ticks)/TPF);
    if(v===0){
      if(sf!==prev){ gaps++; log("  ★隙間/重なり 期待"+prev+"F → "+sf+"F"); }
      prev=ef;
      var key=cl.name+"@"+cl.inPoint.seconds.toFixed(2);
      if(used[key]){ dup++; log("  ★同一素材・同一区間の重複: "+key); } else used[key]=1;
    }
    var m=null; try{ m=cl.getMGTComponent(); }catch(e){}
    var info="";
    if(m){
      var txt="",fnt="",sz="",rl="",vp="";
      for(var q=0;q<m.properties.numItems;q++){
        var p=m.properties[q], n=p.displayName;
        if(n==="本文"){ var b=p.getValue();
          var a1=b.match(/"textEditValue":"([^"]*)"/); txt=a1?a1[1]:"?";
          var a2=b.match(/"fontEditValue":\["([^"]*)"\]/); fnt=a2?a2[1]:"?";
          var a3=b.match(/"fontSizeEditValue":\[([^\]]*)\]/); sz=a3?a3[1]:"?";
          var a4=b.match(/"fontTextRunLength":\[([^\]]*)\]/); rl=a4?a4[1]:"?"; }
        if(n==="縦位置") vp=p.getValue();
      }
      if(String(txt.length)!==String(rl)){ runbad++; }
      info="  「"+txt+"」 "+fnt+" "+sz+" 縦位置"+vp;
    } else if(v===0) info="  "+cl.name+"  tin="+cl.inPoint.seconds.toFixed(3);
    log("  ["+k+"] "+sf+"-"+ef+"F"+info);
  }
  if(tr.clips.numItems){
    var e=Math.round(Number(tr.clips[tr.clips.numItems-1].end.ticks)/TPF);
    var exp=(v>=6)?227:TOTAL;
    if(e!==exp){ endbad++; log("  ★終端="+e+"F 期待"+exp+"F"); }
  }
}
log("");
log("V1 隙間/重なり="+gaps+"  同一素材同一区間の重複="+dup+"  run長不一致="+runbad+"  終端ずれ="+endbad+"  （全て0が正常）");
// ショット尺の統計
var V1=seq.videoTracks[0], d=[];
for(var k=0;k<V1.clips.numItems;k++){
  var cl=V1.clips[k];
  d.push(Math.round(Number(cl.end.ticks)/TPF)-Math.round(Number(cl.start.ticks)/TPF));
}
d.sort(function(a,b){return a-b;});
var med = d.length%2 ? d[(d.length-1)/2] : (d[d.length/2-1]+d[d.length/2])/2;
log("ショット数="+d.length+"  尺(F)="+d.join(",")+"  中央値="+med+"F="+(med/30).toFixed(2)+"秒  cuts/分="+(d.length/(TOTAL/30)*60).toFixed(1));
log("参考: 23ショット / 中央値24F=0.80秒 / cuts分69.1 / 1テロップあたり1.77ショット");
log("本作: "+d.length+"ショット / 1テロップあたり"+(d.length/6).toFixed(2)+"ショット");
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
