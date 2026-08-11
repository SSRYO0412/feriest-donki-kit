var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v31.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var lk=seq.videoTracks[3].clips[0];
var m=lk.getMGTComponent();
var TXT="海老ドーン 贅沢ぷりぷり海老マヨピザ\n※詳細は　をチェック！";
var esc=TXT.replace(/\n/g,"\\n");
for(var q=0;q<m.properties.numItems;q++){
  var p=m.properties[q];
  if(p.displayName==="本文"){
    var v=p.getValue();
    p.setValue(v.replace(/"textEditValue":"[^"]*"/,'"textEditValue":"'+esc+'"')
                .replace(/"fontTextRunLength":\[[^\]]*\]/,'"fontTextRunLength":['+TXT.length+']')
                .replace(/"fontEditValue":\["[^"]*"\]/,'"fontEditValue":["Makinas-4-Square"]')
                .replace(/"fontSizeEditValue":\[[^\]]*\]/,'"fontSizeEditValue":[35]'), true);
  }
  if(p.displayName==="縦位置") p.setValue(81.69,true);
}
for(var q=0;q<lk.components.numItems;q++){
  var cp=lk.components[q];
  if(cp.displayName!=="モーション") continue;
  for(var r=0;r<cp.properties.numItems;r++) if(cp.properties[r].displayName==="位置") cp.properties[r].setValue([0.4500,0.5],true);
}
log("サイズ35 / 縦位置81.69 / 位置x0.4500 を適用");
proj.save(); log("save");
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
