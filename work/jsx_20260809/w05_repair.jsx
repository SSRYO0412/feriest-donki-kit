var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/w05.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var MG="@@KIT_ROOT@@/skill/donki-feriest/assets/telop_3slot_v22.mogrt";
var TPF=8467200000, TOTAL=337;
var STROKE=[24,22,20];
// スロット境界（コンテ確定・変更不可）
var TEL=[[0,28,"海老好き大集合","mplus-1p-heavy",68.948,47.5,[100,100,100],11],
         [28,86,"主役は海老","mplus-1p-heavy",68.948,47.5,[100,100,100],11],
         [86,162,"ぷりぷり♡トロトロ♡","HeiseiMinStd-W9",109.0,47.5,[100,100,100],11],
         [162,227,"海老ドーン","mplus-1p-heavy",68.948,43.65,[100,100,100],11],
         [227,282,"お盆はドンキのピザに決まり!","mplus-1p-heavy",68.948,47.5,[100,100,100],11],
         [282,337,"海老、海老、海老...","mplus-1p-heavy",68.948,47.5,[100,100,100],11]];
var LOCK=[["海老ドーン 贅沢ぷりぷり海老マヨピザ","Makinas-4-Square",35,81.71],
          ["※詳細は　をチェック！","Makinas-4-Square",35,83.76]];
var TILES=[[0,150],[150,300],[300,337]];   // MOGRTの素材長150Fを超えない
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
proj.openSequence(seq.sequenceID);
function setAll(cl,txt,font,size,ypos,col,stw){
  var m=cl.getMGTComponent(); if(!m) return "MGT無し";
  for(var q=0;q<m.properties.numItems;q++){
    var p=m.properties[q], n=p.displayName;
    if(n==="本文"){
      var v=p.getValue();
      p.setValue(v.replace(/"textEditValue":"[^"]*"/,'"textEditValue":"'+txt+'"')
                  .replace(/"fontTextRunLength":\[[^\]]*\]/,'"fontTextRunLength":['+txt.length+']')
                  .replace(/"fontEditValue":\["[^"]*"\]/,'"fontEditValue":["'+font+'"]')
                  .replace(/"fontSizeEditValue":\[[^\]]*\]/,'"fontSizeEditValue":['+size+']'), true);
    }
    else if(n==="縦位置")   p.setValue(ypos,true);
    else if(n==="縁の太さ") p.setValue(stw,true);
    else if(n==="文字色R")  p.setValue(col[0],true);
    else if(n==="文字色G")  p.setValue(col[1],true);
    else if(n==="文字色B")  p.setValue(col[2],true);
    else if(n==="縁色R")    p.setValue(STROKE[0],true);
    else if(n==="縁色G")    p.setValue(STROKE[1],true);
    else if(n==="縁色B")    p.setValue(STROKE[2],true);
  }
  var b=""; for(var q=0;q<m.properties.numItems;q++) if(m.properties[q].displayName==="本文") b=m.properties[q].getValue();
  var a=b.match(/"fontTextRunLength":\[([^\]]*)\]/);
  return (a&&Number(a[1])===txt.length)?"OK":"★run長不一致";
}
// V2 ロゴ / V6 👇 は末尾を337Fへ戻す
var EXT=[1,5];
for(var ei=0; ei<EXT.length; ei++){
  var v=EXT[ei];
  var tr=seq.videoTracks[v];
  if(tr.clips.numItems){
    var cl=tr.clips[tr.clips.numItems-1];
    var before=Math.round(Number(cl.end.ticks)/TPF);
    cl.end=T(TOTAL*TPF);
    log("V"+(v+1)+" 末尾 "+before+"F -> "+Math.round(Number(tr.clips[tr.clips.numItems-1].end.ticks)/TPF)+"F");
  }
}
// V3 テロップを敷き直し
var V3=seq.videoTracks[2];
for(var k=V3.clips.numItems-1;k>=0;k--) V3.clips[k].remove(false,false);
for(var c=0;c<TEL.length;c++){
  var t=TEL[c];
  seq.importMGT(MG, String(t[0]*TPF), 2, -1);
  var tr=seq.videoTracks[2], cl=null;
  for(var k=0;k<tr.clips.numItems;k++) if(Math.round(Number(tr.clips[k].start.ticks)/TPF)===t[0]) cl=tr.clips[k];
  if(!cl){ log("★V3 c0"+(c+1)+" 置けていない"); continue; }
  cl.end=T(t[1]*TPF);
  log("V3 c0"+(c+1)+" "+t[0]+"-"+t[1]+"F 「"+t[2]+"」 : "+setAll(cl,t[2],t[3],t[4],t[5],t[6],t[7]));
}
// V4 / V5 ロックアップを3枚で敷き直し
for(var li=0; li<2; li++){
  var vi=3+li, tr=seq.videoTracks[vi];
  for(var k=tr.clips.numItems-1;k>=0;k--) tr.clips[k].remove(false,false);
  for(var ti=0; ti<TILES.length; ti++){
    seq.importMGT(MG, String(TILES[ti][0]*TPF), vi, -1);
    tr=seq.videoTracks[vi];
    var cl=null;
    for(var k=0;k<tr.clips.numItems;k++) if(Math.round(Number(tr.clips[k].start.ticks)/TPF)===TILES[ti][0]) cl=tr.clips[k];
    if(!cl){ log("★V"+(vi+1)+" tile"+ti+" 置けていない"); continue; }
    cl.end=T(TILES[ti][1]*TPF);
    log("V"+(vi+1)+" tile "+TILES[ti][0]+"-"+TILES[ti][1]+"F : "+setAll(cl,LOCK[li][0],LOCK[li][1],LOCK[li][2],LOCK[li][3],[100,100,100],10));
  }
}
proj.save(); log("save");
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
