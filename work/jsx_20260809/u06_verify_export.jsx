var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/u06.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var TPF=8467200000, TOTAL=337;
var EPR="@@AME_PRESET@@";
var DST="@@FERIEST_ROOT@@/02_work/premiere/verify_20260809/c04_check";
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var NAMES=["V1 カット","V2 ロゴ","V3 テロップ上段","V4 ロックアップ1","V5 ロックアップ2","V6 👇","V7 c04下段1","V8 c04下段2"];
var bad=0, gaps=0;
for(var v=0;v<seq.videoTracks.numTracks;v++){
  var tr=seq.videoTracks[v];
  log("=== "+(NAMES[v]||("V"+(v+1)))+"  clips="+tr.clips.numItems);
  var prev=null;
  for(var k=0;k<tr.clips.numItems;k++){
    var cl=tr.clips[k];
    var sf=Math.round(Number(cl.start.ticks)/TPF), ef=Math.round(Number(cl.end.ticks)/TPF);
    if(v===0){ if(prev!==null && sf!==prev){ gaps++; log("   ★隙間/重なり 期待"+prev+"F → "+sf+"F"); } prev=ef; }
    var m=null; try{ m=cl.getMGTComponent(); }catch(e){}
    var info="";
    if(m){
      var txt="",fnt="",sz="",rl="",vp="",col=[];
      for(var q=0;q<m.properties.numItems;q++){
        var p=m.properties[q], n=p.displayName;
        if(n==="本文"){ var b=p.getValue();
          var a1=b.match(/"textEditValue":"([^"]*)"/); txt=a1?a1[1]:"?";
          var a2=b.match(/"fontEditValue":\["([^"]*)"\]/); fnt=a2?a2[1]:"?";
          var a3=b.match(/"fontSizeEditValue":\[([^\]]*)\]/); sz=a3?a3[1]:"?";
          var a4=b.match(/"fontTextRunLength":\[([^\]]*)\]/); rl=a4?a4[1]:"?"; }
        if(n==="縦位置") vp=p.getValue();
        if(n==="文字色R"||n==="文字色G"||n==="文字色B") col.push(p.getValue());
      }
      if(String(txt.length)!==String(rl)) bad++;
      info="  「"+txt+"」 "+fnt+" "+sz+" 縦位置"+vp+" 色["+col.join(",")+"]"+(String(txt.length)===String(rl)?"":" ★run長不一致");
    } else if(v===0){ info="  "+cl.name; }
    log("  ["+k+"] "+sf+"-"+ef+"F"+info);
  }
}
log("");
log("V1 隙間/重なり="+gaps+"（0が正常）  run長不一致="+bad+"（0が正常）");
var endbad=0;
for(var v=0;v<seq.videoTracks.numTracks;v++){
  var tr=seq.videoTracks[v]; if(!tr.clips.numItems) continue;
  var e=Math.round(Number(tr.clips[tr.clips.numItems-1].end.ticks)/TPF);
  var exp=(v>=6)?227:TOTAL;
  if(e!==exp){ endbad++; log("★V"+(v+1)+" 終端="+e+"F 期待"+exp+"F"); }
}
log("終端ずれ="+endbad+"（0が正常。V7/V8はc04区間なので227Fが正）");
// c04区間だけ書き出し（自分の検算用）
var d=new Folder("@@FERIEST_ROOT@@/02_work/premiere/verify_20260809"); if(!d.exists) d.create();
seq.setInPoint(T(162*TPF)); seq.setOutPoint(T(227*TPF));
var r=seq.exportAsMediaDirect(DST, EPR, 1);
log("書き出し（イン〜アウト・65F）= "+r);
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
