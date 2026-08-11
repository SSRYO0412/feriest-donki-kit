var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/verify.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var TPF=8467200000;
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var NAMES=["V1 カット","V2 ロゴ","V3 テロップ","V4 ロックアップ1行目","V5 ロックアップ2行目","V6 👇","V7 c04下段"];
var bad=0;
for(var v=0;v<seq.videoTracks.numTracks;v++){
  var tr=seq.videoTracks[v];
  log("=== "+(NAMES[v]||("V"+(v+1)))+"  clips="+tr.clips.numItems);
  for(var k=0;k<tr.clips.numItems;k++){
    var cl=tr.clips[k];
    var sf=Math.round(Number(cl.start.ticks)/TPF), ef=Math.round(Number(cl.end.ticks)/TPF);
    var m=null; try{ m=cl.getMGTComponent(); }catch(e){}
    var info="";
    if(m){
      var txt="",fnt="",sz="",rl="",col=[],stw="";
      for(var q=0;q<m.properties.numItems;q++){
        var p=m.properties[q], n=p.displayName;
        if(n==="本文"){ var b=p.getValue();
          var a1=b.match(/"textEditValue":"([^"]*)"/); txt=a1?a1[1]:"?";
          var a2=b.match(/"fontEditValue":\["([^"]*)"\]/); fnt=a2?a2[1]:"?";
          var a3=b.match(/"fontSizeEditValue":\[([^\]]*)\]/); sz=a3?a3[1]:"?";
          var a4=b.match(/"fontTextRunLength":\[([^\]]*)\]/); rl=a4?a4[1]:"?";
        }
        if(n==="文字色R"||n==="文字色G"||n==="文字色B") col.push(p.getValue());
        if(n==="縁の太さ") stw=p.getValue();
      }
      var okLen=(String(txt.length)===String(rl));
      if(!okLen) bad++;
      info="  「"+txt+"」 "+fnt+" "+sz+" 色["+col.join(",")+"] 縁"+stw+(okLen?"":"  ★run長不一致");
    }
    log("  ["+k+"] "+sf+"-"+ef+"F"+info);
  }
}
log("");
log("★run長の不一致="+bad+"（0が正常。1件でもあるとUIで落ちる）");
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
