// ★★★ 却下版・実行禁止 ★★★
// このスクリプトは MOGRT telop_3slot_v20 を参照する。正本は v22。
// v20 は色がカラーピッカー方式でスクリプトから触れない（TELOP-SPEC.md L94 / SETUP.md 4節）。
// 履歴として残すが実行してはならない。後続の t/u/w/x 系列が v22 で同じ役割を果たしている。
return "★中断: v20 参照の却下版です。実行禁止（正本は v22 系列）";
var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v18.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var MG="@@KIT_ROOT@@/skill/donki-feriest/assets/telop_3slot_v20.mogrt";
var TPF=8467200000, FONT="mplus-1p-heavy", SIZE=68.948, YPOS=47.5;
// [開始F, 終了F, 本文]
var TEL=[
 [  0, 28, "海老好き大集合"],
 [ 28, 86, "主役は海老"],
 [ 86,162, "ぷりぷり♡トロトロ♡"],
 [162,227, "海老ドーン 贅沢ぷりぷり海老マヨピザ"],
 [227,282, "お盆はドンキのピザに決まり!"],
 [282,337, "海老、海老、海老..."]
];
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
if(!proj){ log("★中断: 対象なし"); }
else{
  var seq=null;
  for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
  proj.openSequence(seq.sequenceID);
  log("Vトラック(前)="+seq.videoTracks.numTracks);
  if(seq.videoTracks.numTracks<5){
    try{ var qs=qe.project.getActiveSequence(); qs.addTracks(5-seq.videoTracks.numTracks,seq.videoTracks.numTracks,0,0,0,0); }catch(e){ log("addTracks例外:"+String(e)); }
  }
  log("Vトラック(後)="+seq.videoTracks.numTracks);
  var V3=seq.videoTracks[2];
  for(var k=V3.clips.numItems-1;k>=0;k--) V3.clips[k].remove(false,false);
  log("V3クリア clips="+V3.clips.numItems);
  var ok=0;
  for(var c=0;c<TEL.length;c++){
    var f0=TEL[c][0], f1=TEL[c][1], txt=TEL[c][2];
    seq.importMGT(MG, String(f0*TPF), 2, -1);
    var V=seq.videoTracks[2];
    var cl=null;
    for(var k=0;k<V.clips.numItems;k++){
      var sf=Math.round(Number(V.clips[k].start.ticks)/TPF);
      if(sf===f0) cl=V.clips[k];
    }
    if(!cl){ log("★"+c+" 置けていない f0="+f0); continue; }
    cl.end = T(f1*TPF);
    var m=cl.getMGTComponent();
    if(!m){ log("★"+c+" MGTコンポーネント無し"); continue; }
    for(var q=0;q<m.properties.numItems;q++){
      var p=m.properties[q];
      if(p.displayName==="本文"){
        var v=p.getValue();
        p.setValue(v.replace(/"textEditValue":"[^"]*"/,'"textEditValue":"'+txt+'"')
                    .replace(/"fontTextRunLength":\[[^\]]*\]/,'"fontTextRunLength":['+txt.length+']')
                    .replace(/"fontEditValue":\["[^"]*"\]/,'"fontEditValue":["'+FONT+'"]')
                    .replace(/"fontSizeEditValue":\[[^\]]*\]/,'"fontSizeEditValue":['+SIZE+']'), true);
      }
      if(p.displayName==="縦位置") p.setValue(YPOS,true);
    }
    ok++;
  }
  log("テロップ設置 ok="+ok+"/"+TEL.length);
  var V=seq.videoTracks[2];
  var bad=0;
  for(var k=0;k<V.clips.numItems;k++){
    var cl=V.clips[k];
    var sf=Math.round(Number(cl.start.ticks)/TPF), ef=Math.round(Number(cl.end.ticks)/TPF);
    var m=cl.getMGTComponent(); var t="",rl="";
    for(var q=0;q<m.properties.numItems;q++){
      var p=m.properties[q];
      if(p.displayName==="本文"){ var bv=p.getValue();
        var a=bv.match(/"textEditValue":"([^"]*)"/); t=a?a[1]:"?";
        var b=bv.match(/"fontTextRunLength":\[([^\]]*)\]/); rl=b?b[1]:"?"; }
    }
    var okLen = (String(t.length)===String(rl));
    if(!okLen) bad++;
    log("  ["+k+"] "+sf+"F-"+ef+"F  「"+t+"」 文字数"+t.length+"/run"+rl+(okLen?"":"  ★不一致"));
  }
  log("配列長の不一致="+bad+"（0が正常。1件でもあるとUIで落ちる）");
  proj.save(); log("save 実行");
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
