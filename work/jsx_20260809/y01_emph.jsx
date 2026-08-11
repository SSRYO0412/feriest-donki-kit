var L=[]; function log(s){L.push(String(s));}
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var TPF=8467200000;
// 参考「から揚げタルタル」の黄 #EFE919 → 0〜100
var Y=[93.7,91.4,9.8];
var EPR="@@AME_PRESET@@";
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var cl=seq.videoTracks[2].clips[0];
var m=cl.getMGTComponent();
var set={"文字色R":Y[0],"文字色G":Y[1],"文字色B":Y[2],
         "強調の出方":1,                 // 0=なし 1=後から跳ねる 2=後から色が乗る 3=跳ねて色も乗る
         "強調1開始":5,"強調1終わり":7,   // 「大集合」を狙う（添字の起点は書き出して確かめる）
         "強調1の大きさ":25,"強調1の遅れ":0.30,"強調1の縦オフセット":6,
         "強調1色R":Y[0],"強調1色G":Y[1],"強調1色B":Y[2]};
for(var q=0;q<m.properties.numItems;q++){
  var p=m.properties[q], n=p.displayName;
  if(set.hasOwnProperty(n)) p.setValue(set[n],true);
}
for(var q=0;q<m.properties.numItems;q++){
  var p=m.properties[q], n=p.displayName;
  if(n.indexOf("強調1")===0||n==="強調の出方"||n.indexOf("文字色")===0||n.indexOf("縁色")===0||n==="縁の太さ")
    log("  "+n+"="+p.getValue());
}
proj.save();
seq.setInPoint(T(0)); seq.setOutPoint(T(28*TPF));
log("書き出し= "+seq.exportAsMediaDirect("@@FERIEST_ROOT@@/02_work/premiere/verify_20260809/c01_yellow",EPR,1));
var f=new File("@@BRIDGE_DIR@@/y01.txt"); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
