var L=[]; function log(s){L.push(String(s));}
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var TPF=8467200000;
var EPR="@@AME_PRESET@@";
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var m=seq.videoTracks[2].clips[0].getMGTComponent();
// 診断: 絶対に見えるはずの条件にする（赤・特大・全文字・出現アニメも入れる）
var set={"強調の出方":3,"強調1開始":1,"強調1終わり":8,
         "強調1色R":100,"強調1色G":0,"強調1色B":0,
         "強調1の大きさ":60,"強調1の遅れ":0.20,"強調1の縦オフセット":30,
         "出現の型":2,"出現の尺":0.30};
for(var q=0;q<m.properties.numItems;q++){
  var p=m.properties[q];
  if(set.hasOwnProperty(p.displayName)) p.setValue(set[p.displayName],true);
}
for(var q=0;q<m.properties.numItems;q++){
  var p=m.properties[q], n=p.displayName;
  if(set.hasOwnProperty(n)) log("  "+n+"="+p.getValue());
}
proj.save();
seq.setInPoint(T(0)); seq.setOutPoint(T(28*TPF));
log("書き出し= "+seq.exportAsMediaDirect("@@FERIEST_ROOT@@/02_work/premiere/verify_20260809/c01_diag",EPR,1));
var f=new File("@@BRIDGE_DIR@@/y02.txt"); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
