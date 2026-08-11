var L=[]; function log(s){L.push(String(s));}
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var REF="6822d0d1-041a-46a0-a5ff-735087200a01";
var P="@@KIT_ROOT@@/skill/donki-feriest/assets/1f364.png";
var MG="@@KIT_ROOT@@/skill/donki-feriest/assets/telop_3slot_v22.mogrt";
var TPF=8467200000;
var STROKE=[24,22,20];
// c01 を「感嘆・言い切り」書式へ。末尾に全角スペースを1つ入れ、その上に🍤を重ねる（参考の👇と同じ作り）
var TXT="海老好き大集合　", FONT="HeiseiMinStd-W9", SIZE=109.0, YPOS=47.5;
var EMOJI_SCALE=109.0/72.0*100.0;      // 描画高さ＝フォントサイズ（参考の規則）
var EMOJI_X=0.8285, EMOJI_Y=0.4513;    // 初期推定。書き出して画素で測り直す
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
if(!proj || proj.documentID===REF){ log("★中断"); }
else{
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
proj.openSequence(seq.sequenceID);
function findByPath(p,bin){
  for(var i=0;i<bin.children.numItems;i++){
    var it=bin.children[i];
    if(it.type===ProjectItemType.BIN){ var r=findByPath(p,it); if(r) return r; }
    else { var mp=""; try{ mp=it.getMediaPath(); }catch(e){} if(mp===p) return it; }
  }
  return null;
}
var item=findByPath(P,proj.rootItem);
if(!item){ log("★中断: 1f364.png が見つからない（import未完）"); }
else{
  // c01 テロップを書き換え
  var V3=seq.videoTracks[2], cl=null;
  for(var k=0;k<V3.clips.numItems;k++) if(Math.round(Number(V3.clips[k].start.ticks)/TPF)===0) cl=V3.clips[k];
  var m=cl.getMGTComponent();
  for(var q=0;q<m.properties.numItems;q++){
    var p=m.properties[q], n=p.displayName;
    if(n==="本文"){
      var v=p.getValue();
      p.setValue(v.replace(/"textEditValue":"[^"]*"/,'"textEditValue":"'+TXT+'"')
                  .replace(/"fontTextRunLength":\[[^\]]*\]/,'"fontTextRunLength":['+TXT.length+']')
                  .replace(/"fontEditValue":\["[^"]*"\]/,'"fontEditValue":["'+FONT+'"]')
                  .replace(/"fontSizeEditValue":\[[^\]]*\]/,'"fontSizeEditValue":['+SIZE+']'), true);
    }
    else if(n==="縦位置")   p.setValue(YPOS,true);
    else if(n==="縁の太さ") p.setValue(11,true);
    else if(n==="文字色R"||n==="文字色G"||n==="文字色B") p.setValue(100,true);
    else if(n==="縁色R") p.setValue(STROKE[0],true);
    else if(n==="縁色G") p.setValue(STROKE[1],true);
    else if(n==="縁色B") p.setValue(STROKE[2],true);
  }
  var b=""; for(var q=0;q<m.properties.numItems;q++) if(m.properties[q].displayName==="本文") b=m.properties[q].getValue();
  var a=b.match(/"fontTextRunLength":\[([^\]]*)\]/);
  log("c01本文 「"+TXT+"」("+TXT.length+"文字) "+FONT+" "+SIZE+" : "+((a&&Number(a[1])===TXT.length)?"OK":"★run長不一致"));
  // V9 を作って🍤を置く
  if(seq.videoTracks.numTracks<9){
    try{ qe.project.getActiveSequence().addTracks(9-seq.videoTracks.numTracks, seq.videoTracks.numTracks,0,0,0,0); }catch(e){ log("addTracks例外:"+e); }
  }
  log("videoTracks="+seq.videoTracks.numTracks);
  var V9=seq.videoTracks[8];
  for(var k=V9.clips.numItems-1;k>=0;k--) V9.clips[k].remove(false,false);
  var ia=new Time(); ia.seconds=0;      item.setInPoint(ia,4);
  var ib=new Time(); ib.seconds=2.0;    item.setOutPoint(ib,4);
  V9.overwriteClip(item, T(0));
  V9=seq.videoTracks[8];
  var ec=V9.clips[0];
  ec.end=T(28*TPF);
  for(var q=0;q<ec.components.numItems;q++){
    var cp=ec.components[q];
    if(cp.displayName!=="モーション") continue;
    for(var r=0;r<cp.properties.numItems;r++){
      var p=cp.properties[r];
      if(p.displayName==="スケール") p.setValue(EMOJI_SCALE,true);
      if(p.displayName==="位置")     p.setValue([EMOJI_X,EMOJI_Y],true);
    }
  }
  var sc="?",po="?";
  for(var q=0;q<ec.components.numItems;q++){
    var cp=ec.components[q];
    if(cp.displayName!=="モーション") continue;
    for(var r=0;r<cp.properties.numItems;r++){
      var p=cp.properties[r];
      if(p.displayName==="スケール") sc=p.getValue();
      if(p.displayName==="位置")     po=String(p.getValue());
    }
  }
  log("V9 🍤 "+Math.round(Number(ec.start.ticks)/TPF)+"-"+Math.round(Number(ec.end.ticks)/TPF)+"F  スケール="+sc+"  位置="+po);
  proj.save(); log("save");
}
}
var fo=new File("@@BRIDGE_DIR@@/x03.txt"); fo.encoding="UTF-8"; fo.lineFeed="Unix"; fo.open("w"); fo.write(L.join("\n")); fo.close();
return "ok";
