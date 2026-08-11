var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/u05.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var REF="6822d0d1-041a-46a0-a5ff-735087200a01";
var MG="@@KIT_ROOT@@/skill/donki-feriest/assets/telop_3slot_v22.mogrt";
var TPF=8467200000, F0=162, F1=227;
var STROKE=[24,22,20];        // 参考のフチ #3C3934
var EBI=[83,70,49];           // 海老の実測色 #D4B27D
// 参考(から揚げタルタル)の実測: 上段 y853-917 / 下段 y935-1030 / 行間18px / 群中心 941.5px
// 3行に積み替え: 上段68.948(高65) + 18 + 下段141(高118) + 18 + 下段141(高118) = 337px、群中心を941.5に合わせる
// → 上段下端838(43.65%) / 下段1下端974(50.73%) / 下段2下端1110(57.81%)
var UP  =["海老ドーン",      "mplus-1p-heavy", 68.948, 43.65, [100,100,100], 11];
var LO1 =["贅沢ぷりぷり",    "mplus-1p-heavy",141.0,  50.73, EBI,           11];
var LO2 =["海老マヨピザ",    "mplus-1p-heavy",141.0,  57.81, EBI,           11];
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
if(!proj || proj.documentID===REF){ log("★中断: 対象不正"); }
else{
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
proj.openSequence(seq.sequenceID);
if(seq.videoTracks.numTracks<8){
  try{ qe.project.getActiveSequence().addTracks(8-seq.videoTracks.numTracks, seq.videoTracks.numTracks,0,0,0,0); }catch(e){ log("addTracks例外:"+e); }
}
log("videoTracks="+seq.videoTracks.numTracks);
function setAll(cl,d){
  var m=cl.getMGTComponent(); if(!m) return "MGT無し";
  var txt=d[0],font=d[1],size=d[2],ypos=d[3],col=d[4],stw=d[5];
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
function place(trackIdx,d){
  var tr=seq.videoTracks[trackIdx];
  for(var k=tr.clips.numItems-1;k>=0;k--){
    var sf=Math.round(Number(tr.clips[k].start.ticks)/TPF);
    if(sf===F0) tr.clips[k].remove(false,false);
  }
  seq.importMGT(MG, String(F0*TPF), trackIdx, -1);
  tr=seq.videoTracks[trackIdx];
  var cl=null;
  for(var k=0;k<tr.clips.numItems;k++) if(Math.round(Number(tr.clips[k].start.ticks)/TPF)===F0) cl=tr.clips[k];
  if(!cl) return "★置けていない";
  cl.end=T(F1*TPF);
  return setAll(cl,d);
}
// 上段は V3 の c04 クリップ（既存）を書き換えるだけ
var V3=seq.videoTracks[2], up=null;
for(var k=0;k<V3.clips.numItems;k++) if(Math.round(Number(V3.clips[k].start.ticks)/TPF)===F0) up=V3.clips[k];
log("上段 V3 「"+UP[0]+"」 "+UP[2]+" 縦位置"+UP[3]+" : "+(up?setAll(up,UP):"★c04クリップなし"));
log("下段1 V7 「"+LO1[0]+"」 "+LO1[2]+" 縦位置"+LO1[3]+" 色"+LO1[4].join(",")+" : "+place(6,LO1));
log("下段2 V8 「"+LO2[0]+"」 "+LO2[2]+" 縦位置"+LO2[3]+" 色"+LO2[4].join(",")+" : "+place(7,LO2));
proj.save(); log("save");
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
