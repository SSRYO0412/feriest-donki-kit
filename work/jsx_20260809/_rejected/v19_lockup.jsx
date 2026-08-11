// ★★★ 却下版・実行禁止 ★★★
// このスクリプトは MOGRT telop_3slot_v20 を参照する。正本は v22。
// v20 は色がカラーピッカー方式でスクリプトから触れない（TELOP-SPEC.md L94 / SETUP.md 4節）。
// 履歴として残すが実行してはならない。後続の t/u/w/x 系列が v22 で同じ役割を果たしている。
return "★中断: v20 参照の却下版です。実行禁止（正本は v22 系列）";
var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v19.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var MG="@@KIT_ROOT@@/skill/donki-feriest/assets/telop_3slot_v20.mogrt";
var EMO="@@FERIEST_ROOT@@/01_assets/0.7人前うどん/0.7人前うどん/0.7人前うどん/1f447.png";
var TPF=8467200000, TOTAL=337;
var TXT="海老ドーン 贅沢ぷりぷり海老マヨピザ\n※詳細は　をチェック！";
var FONT="Makinas-4-Square", SIZE=40, YPOS=81;
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
// --- V4: ロックアップ文字
var V4=seq.videoTracks[3];
for(var k=V4.clips.numItems-1;k>=0;k--) V4.clips[k].remove(false,false);
seq.importMGT(MG, String(0), 3, -1);
V4=seq.videoTracks[3];
if(V4.clips.numItems===0){ log("★中断: ロックアップMOGRTが置けていない"); }
else{
  var cl=V4.clips[0];
  cl.end=T(TOTAL*TPF);
  var m=cl.getMGTComponent();
  var esc=TXT.replace(/\n/g,"\\n");
  var plain=TXT.replace(/\n/g,"");
  for(var q=0;q<m.properties.numItems;q++){
    var p=m.properties[q];
    if(p.displayName==="本文"){
      var v=p.getValue();
      p.setValue(v.replace(/"textEditValue":"[^"]*"/,'"textEditValue":"'+esc+'"')
                  .replace(/"fontTextRunLength":\[[^\]]*\]/,'"fontTextRunLength":['+(plain.length+1)+']')
                  .replace(/"fontEditValue":\["[^"]*"\]/,'"fontEditValue":["'+FONT+'"]')
                  .replace(/"fontSizeEditValue":\[[^\]]*\]/,'"fontSizeEditValue":['+SIZE+']'), true);
    }
    if(p.displayName==="縦位置") p.setValue(YPOS,true);
    if(p.displayName==="縁の太さ") p.setValue(4,true);
  }
  var back=""; for(var q=0;q<m.properties.numItems;q++) if(m.properties[q].displayName==="本文") back=m.properties[q].getValue();
  var t=back.match(/"textEditValue":"([^"]*)"/), rl=back.match(/"fontTextRunLength":\[([^\]]*)\]/);
  log("ロックアップ本文="+(t?t[1]:"?"));
  log("  run長="+(rl?rl[1]:"?")+"  （改行込みの文字数="+(plain.length+1)+"）");
}
// --- V5: 👇
var V5=seq.videoTracks[4];
for(var k=V5.clips.numItems-1;k>=0;k--) V5.clips[k].remove(false,false);
function findByPath(path,bin){
  for(var i=0;i<bin.children.numItems;i++){
    var it=bin.children[i];
    if(it.type===ProjectItemType.BIN){ var r=findByPath(path,it); if(r) return r; }
    else { var mp=""; try{ mp=it.getMediaPath(); }catch(e){} if(mp===path) return it; }
  }
  return null;
}
var emo=findByPath(EMO,proj.rootItem);
if(!emo){ log("★👇素材なし"); }
else{
  var a=new Time(); a.seconds=0; emo.setInPoint(a,4);
  var b=new Time(); b.seconds=TOTAL/30.0+1; emo.setOutPoint(b,4);
  V5.overwriteClip(emo,T(0));
  V5=seq.videoTracks[4];
  V5.clips[0].end=T(TOTAL*TPF);
  var e=V5.clips[0];
  for(var q=0;q<e.components.numItems;q++){
    var cp=e.components[q];
    if(cp.displayName!=="モーション") continue;
    for(var r=0;r<cp.properties.numItems;r++){
      var pr=cp.properties[r];
      if(pr.displayName==="スケール") pr.setValue(49.2573776245117,true);
      if(pr.displayName==="位置")     pr.setValue([0.33703702688217,0.85694444179535],true);
    }
  }
  log("👇 配置 スケール49.257 位置(0.337,0.857)");
}
log("Vトラック構成: V1=カット V2=ロゴ V3=テロップ V4=ロックアップ文字 V5=👇");
proj.save(); log("save 実行");
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
