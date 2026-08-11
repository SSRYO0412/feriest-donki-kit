var L=[]; function log(s){L.push(String(s));}
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var TPF=8467200000;
var Y=[93.7,91.4,9.8];        // #EFE919
var EPR="@@AME_PRESET@@";
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var m=seq.videoTracks[2].clips[0].getMGTComponent();
var set={"文字色R":Y[0],"文字色G":Y[1],"文字色B":Y[2],
         "出現の型":0,"出現の尺":0.5,                 // 参考は完全静止なので出現アニメは戻す
         "強調の出方":0,                               // なし＝静的に効く（1だと1フレームの跳ねだけ）
         "強調1開始":5,"強調1終わり":7,                // 「大集合」
         "強調1の大きさ":45,"強調1の遅れ":0,"強調1の縦オフセット":0,
         "強調1色R":Y[0],"強調1色G":Y[1],"強調1色B":Y[2],
         "強調1の縁の太さ":11,"強調1縁色R":24,"強調1縁色G":22,"強調1縁色B":20};
for(var q=0;q<m.properties.numItems;q++){
  var p=m.properties[q];
  if(set.hasOwnProperty(p.displayName)) p.setValue(set[p.displayName],true);
}
proj.save();
seq.setInPoint(T(0)); seq.setOutPoint(T(28*TPF));
log("書き出し= "+seq.exportAsMediaDirect("@@FERIEST_ROOT@@/02_work/premiere/verify_20260809/c01_final",EPR,1));
var f=new File("@@BRIDGE_DIR@@/y05.txt"); f.encoding="UTF-8"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
