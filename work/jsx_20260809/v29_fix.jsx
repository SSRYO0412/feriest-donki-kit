var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v29.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
// 1) 全クリップを有効に戻す
var re=0;
for(var v=0;v<seq.videoTracks.numTracks;v++){
  var tr=seq.videoTracks[v];
  for(var k=0;k<tr.clips.numItems;k++){ if(tr.clips[k].disabled){ tr.clips[k].disabled=false; re++; } }
}
log("有効に戻したクリップ="+re);
function setText(cl,txt,font,size,ypos,strokeW){
  var m=cl.getMGTComponent(); if(!m) return "MGT無し";
  var esc=txt.replace(/\n/g,"\\n");
  var n=txt.length;
  for(var q=0;q<m.properties.numItems;q++){
    var p=m.properties[q];
    if(p.displayName==="本文"){
      var v=p.getValue();
      p.setValue(v.replace(/"textEditValue":"[^"]*"/,'"textEditValue":"'+esc+'"')
                  .replace(/"fontTextRunLength":\[[^\]]*\]/,'"fontTextRunLength":['+n+']')
                  .replace(/"fontEditValue":\["[^"]*"\]/,'"fontEditValue":["'+font+'"]')
                  .replace(/"fontSizeEditValue":\[[^\]]*\]/,'"fontSizeEditValue":['+size+']'), true);
    }
    if(p.displayName==="縦位置") p.setValue(ypos,true);
    if(strokeW!==null && p.displayName==="縁の太さ") p.setValue(strokeW,true);
  }
  // 検算
  var b=""; for(var q=0;q<m.properties.numItems;q++) if(m.properties[q].displayName==="本文") b=m.properties[q].getValue();
  var a=b.match(/"fontTextRunLength":\[([^\]]*)\]/);
  return (a && Number(a[1])===n) ? "OK" : "★run長不一致";
}
// 2) c04 のテロップを2行に割る（コンテの空白位置＝文節の切れ目）
var t4=seq.videoTracks[2].clips[3];
log("c04 2行化: "+setText(t4,"海老ドーン\n贅沢ぷりぷり海老マヨピザ","mplus-1p-heavy",68.948,47.5,null));
// 3) ロックアップを2行に戻し、参考の実測へ寄せる
var lk=seq.videoTracks[3].clips[0];
log("ロックアップ: "+setText(lk,"海老ドーン 贅沢ぷりぷり海老マヨピザ\n※詳細は　をチェック！","Makinas-4-Square",31,82.8,6));
// 左寄せ: モーション位置で左へ寄せる
for(var q=0;q<lk.components.numItems;q++){
  var cp=lk.components[q];
  if(cp.displayName!=="モーション") continue;
  for(var r=0;r<cp.properties.numItems;r++){
    var p=cp.properties[r];
    if(p.displayName==="位置") p.setValue([0.4639,0.5],true);
  }
}
log("ロックアップ位置x=0.4639（左端をx=221に寄せる想定・書き出して実測する）");
proj.save(); log("save");
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
