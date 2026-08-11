// ★★★ 却下版・実行禁止 ★★★
// このスクリプトは MOGRT telop_3slot_v20 を参照する。正本は v22。
// v20 は色がカラーピッカー方式でスクリプトから触れない（TELOP-SPEC.md L94 / SETUP.md 4節）。
// 履歴として残すが実行してはならない。後続の t/u/w/x 系列が v22 で同じ役割を果たしている。
return "★中断: v20 参照の却下版です。実行禁止（正本は v22 系列）";
var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v37.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var MG="@@KIT_ROOT@@/skill/donki-feriest/assets/telop_3slot_v20.mogrt";
var TPF=8467200000, TOTAL=337;
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
function setP(cl,txt,size,ypos,posx,strokeW){
  var m=cl.getMGTComponent(); if(!m) return "MGT無し";
  for(var q=0;q<m.properties.numItems;q++){
    var p=m.properties[q];
    if(p.displayName==="本文"){
      var v=p.getValue();
      p.setValue(v.replace(/"textEditValue":"[^"]*"/,'"textEditValue":"'+txt+'"')
                  .replace(/"fontTextRunLength":\[[^\]]*\]/,'"fontTextRunLength":['+txt.length+']')
                  .replace(/"fontEditValue":\["[^"]*"\]/,'"fontEditValue":["Makinas-4-Square"]')
                  .replace(/"fontSizeEditValue":\[[^\]]*\]/,'"fontSizeEditValue":['+size+']'), true);
    }
    if(p.displayName==="縦位置") p.setValue(ypos,true);
    if(p.displayName==="縁の太さ") p.setValue(strokeW,true);
  }
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q];
    if(cp.displayName!=="モーション") continue;
    for(var r=0;r<cp.properties.numItems;r++) if(cp.properties[r].displayName==="位置") cp.properties[r].setValue([posx,0.5],true);
  }
  return "OK";
}
function tile(trackIdx, txt, size, ypos, posx, strokeW, label){
  var tr=seq.videoTracks[trackIdx];
  for(var k=tr.clips.numItems-1;k>=0;k--) tr.clips[k].remove(false,false);
  // 1枚目を置いて素材長を実測
  seq.importMGT(MG, String(0), trackIdx, -1);
  tr=seq.videoTracks[trackIdx];
  var nat=Math.round(Number(tr.clips[0].end.ticks)/TPF);
  log(label+" MOGRT素材長="+nat+"F ("+(nat/30).toFixed(3)+"秒)");
  var at=nat;
  while(at<TOTAL){
    seq.importMGT(MG, String(at*TPF), trackIdx, -1);
    at+=nat;
  }
  tr=seq.videoTracks[trackIdx];
  // 末尾を337Fで切る＋全枚にパラメータ
  for(var k=0;k<tr.clips.numItems;k++){
    var cl=tr.clips[k];
    var ef=Math.round(Number(cl.end.ticks)/TPF);
    if(ef>TOTAL) cl.end=T(TOTAL*TPF);
    setP(cl,txt,size,ypos,posx,strokeW);
  }
  // 検算
  var prev=0,gaps=0,det=[];
  for(var k=0;k<tr.clips.numItems;k++){
    var cl=tr.clips[k];
    var sf=Math.round(Number(cl.start.ticks)/TPF), ef2=Math.round(Number(cl.end.ticks)/TPF);
    if(sf!==prev) gaps++;
    prev=ef2; det.push(sf+"-"+ef2);
  }
  log("  "+label+" 枚数="+tr.clips.numItems+"  区間="+det.join(", ")+"  隙間="+gaps+"  終端="+prev+"F");
}
tile(3,"海老ドーン 贅沢ぷりぷり海老マヨピザ",35,81.71,0.4704,6,"V4 1行目");
tile(4,"※詳細は　をチェック！",35,83.76,0.3787,6,"V5 2行目");
proj.save(); log("save");
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
