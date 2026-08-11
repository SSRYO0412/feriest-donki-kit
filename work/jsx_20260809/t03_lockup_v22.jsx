var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/lockup22.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var MG="@@KIT_ROOT@@/skill/donki-feriest/assets/telop_3slot_v22.mogrt";
var TPF=8467200000, TOTAL=337;
var STROKE=[24,22,20];
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
function setAll(cl,txt,font,size,ypos,posx,stw){
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
    else if(n==="文字色R"||n==="文字色G"||n==="文字色B") p.setValue(100,true);
    else if(n==="縁色R") p.setValue(STROKE[0],true);
    else if(n==="縁色G") p.setValue(STROKE[1],true);
    else if(n==="縁色B") p.setValue(STROKE[2],true);
  }
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q];
    if(cp.displayName!=="モーション") continue;
    for(var r=0;r<cp.properties.numItems;r++) if(cp.properties[r].displayName==="位置") cp.properties[r].setValue([posx,0.5],true);
  }
  return "OK";
}
function tile(idx,txt,size,ypos,posx,label){
  var tr=seq.videoTracks[idx];
  for(var k=tr.clips.numItems-1;k>=0;k--) tr.clips[k].remove(false,false);
  seq.importMGT(MG,String(0),idx,-1);
  tr=seq.videoTracks[idx];
  var nat=Math.round(Number(tr.clips[0].end.ticks)/TPF);
  var at=nat;
  while(at<TOTAL){ seq.importMGT(MG,String(at*TPF),idx,-1); at+=nat; }
  tr=seq.videoTracks[idx];
  for(var k=0;k<tr.clips.numItems;k++){
    var cl=tr.clips[k];
    if(Math.round(Number(cl.end.ticks)/TPF)>TOTAL) cl.end=T(TOTAL*TPF);
    setAll(cl,txt,"Makinas-4-Square",size,ypos,posx,10);
  }
  var prev=0,gaps=0;
  for(var k=0;k<tr.clips.numItems;k++){
    var sf=Math.round(Number(tr.clips[k].start.ticks)/TPF), ef=Math.round(Number(tr.clips[k].end.ticks)/TPF);
    if(sf!==prev) gaps++; prev=ef;
  }
  log(label+" 枚数="+tr.clips.numItems+" 隙間="+gaps+" 終端="+prev+"F");
}
tile(3,"海老ドーン 贅沢ぷりぷり海老マヨピザ",35,81.71,0.4704,"V4 1行目");
tile(4,"※詳細は　をチェック！",35,83.76,0.3787,"V5 2行目");
proj.save(); log("save");
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
