var L=[]; function log(s){L.push(String(s));}
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var TPF=8467200000;
var Y=[93.7,91.4,9.8];        // #EFE919 参考「から揚げタルタル」の黄
var EPR="@@AME_PRESET@@";
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var m=seq.videoTracks[2].clips[0].getMGTComponent();
// c01=28F(0.933秒)。出現0.20秒 → 遅れ0.15秒 → 0.35秒(F10.5)で跳ね、残り0.58秒で収まる
var set={"文字色R":Y[0],"文字色G":Y[1],"文字色B":Y[2],
         "出現の型":2,"出現の尺":0.20,             // ★なしにすると強調が発火しない
         "強調の出方":1,                            // 後から跳ねる（色は黄のまま）
         "強調1開始":5,"強調1終わり":7,              // 「大集合」（添字は1始まり・診断で確認）
         "強調1の大きさ":25,"強調1の遅れ":0.15,"強調1の縦オフセット":6,
         "強調1色R":Y[0],"強調1色G":Y[1],"強調1色B":Y[2]};
for(var q=0;q<m.properties.numItems;q++){
  var p=m.properties[q];
  if(set.hasOwnProperty(p.displayName)) p.setValue(set[p.displayName],true);
}
for(var q=0;q<m.properties.numItems;q++){
  var p=m.properties[q], n=p.displayName;
  if(set.hasOwnProperty(n)||n==="縁の太さ"||n.indexOf("縁色")===0) log("  "+n+"="+p.getValue());
}
proj.save();
seq.setInPoint(T(0)); seq.setOutPoint(T(28*TPF));
log("書き出し= "+seq.exportAsMediaDirect("@@FERIEST_ROOT@@/02_work/premiere/verify_20260809/c01_yellow_v2",EPR,1));
var f=new File("@@BRIDGE_DIR@@/y03.txt"); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
