var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v35.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
function tune(trackIdx, ypos, posx, label){
  var cl=seq.videoTracks[trackIdx].clips[0];
  var m=cl.getMGTComponent();
  if(m){ for(var q=0;q<m.properties.numItems;q++) if(m.properties[q].displayName==="縦位置") m.properties[q].setValue(ypos,true); }
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q];
    if(cp.displayName!=="モーション") continue;
    for(var r=0;r<cp.properties.numItems;r++) if(cp.properties[r].displayName==="位置") cp.properties[r].setValue([posx,0.5],true);
  }
  log(label+"  縦位置="+ypos+" 位置x="+posx);
}
tune(3, 81.71, 0.4704, "V4 1行目");   // 上端 -4px / 左端 -11px の補正
tune(4, 83.76, 0.3787, "V5 2行目");   // 上端 -3px / 左端 -5px の補正
// 👇 を全角スペースの中心へ（実測 x=369.5, y=1591）＋2行目の移動分を反映
var e=seq.videoTracks[5].clips[0];
var EX=(369.5+5)/1080, EY=(1591+3)/1920;
for(var q=0;q<e.components.numItems;q++){
  var cp=e.components[q];
  if(cp.displayName!=="モーション") continue;
  for(var r=0;r<cp.properties.numItems;r++){
    var p=cp.properties[r];
    if(p.displayName==="スケール") p.setValue(49.2573776245117,true);
    if(p.displayName==="位置")     p.setValue([EX,EY],true);
  }
}
log("V6 👇  位置=("+EX.toFixed(4)+","+EY.toFixed(4)+")  スケール49.257");
proj.save(); log("save");
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
