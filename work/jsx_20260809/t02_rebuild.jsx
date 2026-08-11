var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/rebuild.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var REF="6822d0d1-041a-46a0-a5ff-735087200a01";
var MG="@@KIT_ROOT@@/skill/donki-feriest/assets/telop_3slot_v22.mogrt";
var TPF=8467200000;
// 参考の文法: 通常=mplus 68.948 白 / 感嘆=明朝109 白 / 商品名2行=上段小白+下段大色
// [開始F,終了F,本文,書体,サイズ,縦位置,文字色RGB(0-100),縁の太さ]
var TEL=[
 [  0, 28,"海老好き大集合",              "mplus-1p-heavy",  68.948, 47.5, [100,100,100], 11],
 [ 28, 86,"主役は海老",                  "mplus-1p-heavy",  68.948, 47.5, [100,100,100], 11],
 [ 86,162,"ぷりぷり♡トロトロ♡",          "HeiseiMinStd-W9",109.0,  47.5, [100,100,100], 11],
 [162,227,"海老ドーン",                  "mplus-1p-heavy",  68.948, 43.0, [100,100,100], 11],
 [227,282,"お盆はドンキのピザに決まり!",  "mplus-1p-heavy",  68.948, 47.5, [100,100,100], 11],
 [282,337,"海老、海老、海老...",          "mplus-1p-heavy",  68.948, 47.5, [100,100,100], 11]
];
// c04下段（商品名の大きい行・海老の色）
var SUB=[162,227,"贅沢ぷりぷり海老マヨピザ","mplus-1p-heavy",88.0,50.5,[83,70,49],11];
var STROKE=[24,22,20];   // 参考のフチ色 #3C3934
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
if(!proj || proj.documentID===REF){ log("★中断"); }
else{
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
proj.openSequence(seq.sequenceID);
if(seq.videoTracks.numTracks<7){ try{ qe.project.getActiveSequence().addTracks(7-seq.videoTracks.numTracks,seq.videoTracks.numTracks,0,0,0,0);}catch(e){} }
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
// V3 を敷き直し
var V3=seq.videoTracks[2];
for(var k=V3.clips.numItems-1;k>=0;k--) V3.clips[k].remove(false,false);
for(var c=0;c<TEL.length;c++){
  var t=TEL[c];
  seq.importMGT(MG, String(t[0]*TPF), 2, -1);
  var tr=seq.videoTracks[2]; var cl=null;
  for(var k=0;k<tr.clips.numItems;k++) if(Math.round(Number(tr.clips[k].start.ticks)/TPF)===t[0]) cl=tr.clips[k];
  if(!cl){ log("★c0"+(c+1)+" 置けていない"); continue; }
  cl.end=T(t[1]*TPF);
  log("c0"+(c+1)+" 「"+t[2]+"」 "+t[3]+" "+t[4]+" 色"+t[6].join(",")+" : "+setAll(cl,t[2],t[3],t[4],t[5],t[6],t[7]));
}
// V7 に c04下段
var V7=seq.videoTracks[6];
for(var k=V7.clips.numItems-1;k>=0;k--) V7.clips[k].remove(false,false);
seq.importMGT(MG, String(SUB[0]*TPF), 6, -1);
V7=seq.videoTracks[6];
if(V7.clips.numItems>0){
  var cl2=V7.clips[V7.clips.numItems-1];
  cl2.end=T(SUB[1]*TPF);
  log("c04下段 「"+SUB[2]+"」 "+SUB[3]+" "+SUB[4]+" 色"+SUB[6].join(",")+" : "+setAll(cl2,SUB[2],SUB[3],SUB[4],SUB[5],SUB[6],SUB[7]));
}
proj.save(); log("save");
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
