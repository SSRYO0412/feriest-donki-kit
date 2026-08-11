// ★★★ 却下版・実行禁止 ★★★
// このスクリプトは MOGRT telop_3slot_v20 を参照する。正本は v22。
// v20 は色がカラーピッカー方式でスクリプトから触れない（TELOP-SPEC.md L94 / SETUP.md 4節）。
// 履歴として残すが実行してはならない。後続の t/u/w/x 系列が v22 で同じ役割を果たしている。
return "★中断: v20 参照の却下版です。実行禁止（正本は v22 系列）";
var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v33.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var MG="@@KIT_ROOT@@/skill/donki-feriest/assets/telop_3slot_v20.mogrt";
var EMO="@@FERIEST_ROOT@@/01_assets/0.7人前うどん/0.7人前うどん/0.7人前うどん/1f447.png";
var TPF=8467200000, TOTAL=337;
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
proj.openSequence(seq.sequenceID);
if(seq.videoTracks.numTracks<6){
  try{ qe.project.getActiveSequence().addTracks(6-seq.videoTracks.numTracks, seq.videoTracks.numTracks,0,0,0,0); }catch(e){ log("addTracks例外:"+String(e)); }
}
log("Vトラック="+seq.videoTracks.numTracks);
// V4,V5,V6 をクリア
for(var v=3;v<=5 && v<seq.videoTracks.numTracks;v++){
  var tr=seq.videoTracks[v];
  for(var k=tr.clips.numItems-1;k>=0;k--) tr.clips[k].remove(false,false);
}
function place(trackIdx, txt, size, ypos, posx, strokeW){
  seq.importMGT(MG, String(0), trackIdx, -1);
  var tr=seq.videoTracks[trackIdx];
  var cl=tr.clips[tr.clips.numItems-1];
  cl.end=T(TOTAL*TPF);
  var m=cl.getMGTComponent();
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
  var b=""; for(var q=0;q<m.properties.numItems;q++) if(m.properties[q].displayName==="本文") b=m.properties[q].getValue();
  var a=b.match(/"fontTextRunLength":\[([^\]]*)\]/);
  return (a && Number(a[1])===txt.length)?"OK":"★run長不一致";
}
log("V4 1行目: "+place(3,"海老ドーン 贅沢ぷりぷり海老マヨピザ",35,81.5,0.4602,6));
log("V5 2行目: "+place(4,"※詳細は　をチェック！",35,83.6,0.3741,6));
// V6: 👇
function findByPath(path,bin){
  for(var i=0;i<bin.children.numItems;i++){
    var it=bin.children[i];
    if(it.type===ProjectItemType.BIN){ var r=findByPath(path,it); if(r) return r; }
    else { var mp=""; try{ mp=it.getMediaPath(); }catch(e){} if(mp===path) return it; }
  }
  return null;
}
var emo=findByPath(EMO,proj.rootItem);
if(emo){
  var a2=new Time(); a2.seconds=0; emo.setInPoint(a2,4);
  var b2=new Time(); b2.seconds=TOTAL/30.0+1; emo.setOutPoint(b2,4);
  seq.videoTracks[5].overwriteClip(emo,T(0));
  var e=seq.videoTracks[5].clips[0];
  e.end=T(TOTAL*TPF);
  for(var q=0;q<e.components.numItems;q++){
    var cp=e.components[q];
    if(cp.displayName!=="モーション") continue;
    for(var r=0;r<cp.properties.numItems;r++){
      var p=cp.properties[r];
      if(p.displayName==="スケール") p.setValue(49.2573776245117,true);
      if(p.displayName==="位置")     p.setValue([0.42,0.8322],true);   // 2行目の空白位置（暫定・書き出して実測）
    }
  }
  log("V6 👇 配置");
}
proj.save(); log("save");
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
