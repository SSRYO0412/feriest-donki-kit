var L=[]; function log(s){log_(s);} function log_(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v22.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var cl=seq.videoTracks[3].clips[0];
var m=cl.getMGTComponent();
var TXT="海老ドーン 贅沢ぷりぷり海老マヨピザ";   // ★改行なしの1行にする
for(var q=0;q<m.properties.numItems;q++){
  var p=m.properties[q];
  if(p.displayName==="本文"){
    var v=p.getValue();
    p.setValue(v.replace(/"textEditValue":"[^"]*"/,'"textEditValue":"'+TXT+'"')
                .replace(/"fontTextRunLength":\[[^\]]*\]/,'"fontTextRunLength":['+TXT.length+']')
                .replace(/"fontEditValue":\["[^"]*"\]/,'"fontEditValue":["Makinas-4-Square"]')
                .replace(/"fontSizeEditValue":\[[^\]]*\]/,'"fontSizeEditValue":[40]'), true);
  }
  if(p.displayName==="縦位置") p.setValue(80,true);
  if(p.displayName==="縁の太さ") p.setValue(10,true);   // 太めにして視認性を上げる
}
var b=""; for(var q=0;q<m.properties.numItems;q++) if(m.properties[q].displayName==="本文") b=m.properties[q].getValue();
log(b.substring(0,300));
proj.save(); log("save");
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
