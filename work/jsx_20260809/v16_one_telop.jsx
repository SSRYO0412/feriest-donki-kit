var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v16.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var TPF=8467200000;
var TXT="ぷりぷり♡トロトロ♡";
var FONT="mplus-1p-heavy", SIZE=68.948;
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var V3=seq.videoTracks[2];
if(V3.clips.numItems===0){ log("★中断: MOGRTが無い"); }
else{
  var cl=V3.clips[0];
  // c03 の区間 86F-162F に合わせる
  cl.start = (function(){var t=new Time(); t.ticks=String(86*TPF); return t;})();
  cl.end   = (function(){var t=new Time(); t.ticks=String(162*TPF); return t;})();
  var m=cl.getMGTComponent();
  var pText=null, pY=null;
  for(var k=0;k<m.properties.numItems;k++){
    var p=m.properties[k];
    if(p.displayName==="本文") pText=p;
    if(p.displayName==="縦位置") pY=p;
  }
  var v=pText.getValue();
  var nv = v.replace(/"textEditValue":"[^"]*"/, '"textEditValue":"'+TXT+'"')
            .replace(/"fontTextRunLength":\[[^\]]*\]/, '"fontTextRunLength":['+TXT.length+']')
            .replace(/"fontEditValue":\["[^"]*"\]/, '"fontEditValue":["'+FONT+'"]')
            .replace(/"fontSizeEditValue":\[[^\]]*\]/, '"fontSizeEditValue":['+SIZE+']');
  pText.setValue(nv, true);
  if(pY) pY.setValue(46, true);   // 参考の本文中心 y≈0.46
  // 読み戻して配列長を検算（これは"落ちない"確認であって効いた証明ではない）
  var back=pText.getValue();
  var mm=back.match(/"fontTextRunLength":\[([^\]]*)\]/);
  var tt=back.match(/"textEditValue":"([^"]*)"/);
  var ff=back.match(/"fontEditValue":\["([^"]*)"\]/);
  var ss=back.match(/"fontSizeEditValue":\[([^\]]*)\]/);
  log("本文="+(tt?tt[1]:"?")+"  文字数="+TXT.length+"  runLength="+(mm?mm[1]:"?")+"  → "+((mm&&Number(mm[1])===TXT.length)?"一致OK":"★不一致(UIで落ちる)"));
  log("書体="+(ff?ff[1]:"?")+"  サイズ="+(ss?ss[1]:"?"));
  log("縦位置="+(pY?pY.getValue():"?"));
  var sf=Math.round(Number(cl.start.ticks)/TPF), ef=Math.round(Number(cl.end.ticks)/TPF);
  log("区間 "+sf+"F-"+ef+"F");
  proj.save(); log("save 実行");
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
