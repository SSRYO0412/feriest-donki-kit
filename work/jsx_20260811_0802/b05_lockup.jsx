var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/b05.txt";
var TPF=8467200000, TOTAL=316;
var MG="@@KIT_ROOT@@/skill/donki-feriest/assets/telop_3slot_v22.mogrt";
var LOGO="@@KIT_ROOT@@/data/reference/月乗りドンペン.jpg";
var E447="@@KIT_ROOT@@/skill/donki-feriest/assets/1f447.png";
var E602="@@FERIEST_ROOT@@/02_work/premiere/assets_emoji/1f602.png";
var STROKE=[24,22,20];
var TILES=[[0,150],[150,300],[300,316]];
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++)
  if(app.projects[i].path && app.projects[i].path.indexOf("FERIEST_0802_spray_v1")>=0) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++)
  if(proj.sequences[s].name==="0802_spray") seq=proj.sequences[s];
proj.openSequence(seq.sequenceID);
function findByPath(p,bin){
  for(var i=0;i<bin.children.numItems;i++){ var it=bin.children[i];
    if(it.type===ProjectItemType.BIN){ var r=findByPath(p,it); if(r) return r; }
    else { var mp=""; try{ mp=it.getMediaPath(); }catch(e){} if(mp===p) return it; } }
  return null; }
function clean(idx){ var V=seq.videoTracks[idx];
  for(var k=V.clips.numItems-1;k>=0;k--) V.clips[k].remove(false,false); }
function placeStill(idx,path,startF,endF,scale,pos){
  var it=findByPath(path,proj.rootItem);
  if(!it){ log("★still無し "+path); return; }
  var V=seq.videoTracks[idx];
  V.overwriteClip(it, T(startF*TPF));
  V=seq.videoTracks[idx];
  var cl=V.clips[V.clips.numItems-1];
  cl.end=T(endF*TPF);
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q];
    if(cp.displayName!=="モーション") continue;
    for(var r=0;r<cp.properties.numItems;r++){
      var pr=cp.properties[r], n=pr.displayName;
      if(n==="スケール"||n==="スケール (高さ)"||n==="スケール (幅)") pr.setValue(scale,true);
      if(n==="位置") pr.setValue(pos,true);
    }
  }
}
function tile(idx,txt,size,vpos,xpos){
  for(var t=0;t<TILES.length;t++){
    var cl=null;
    try{ cl=seq.importMGT(MG, T(TILES[t][0]*TPF), idx, 0); }catch(e){ log("★MGT例外:"+e); return; }
    cl.end=T(TILES[t][1]*TPF);
    var m=cl.getMGTComponent(); if(!m) continue;
    for(var q=0;q<m.properties.numItems;q++){
      var p=m.properties[q], n=p.displayName;
      if(n==="本文"){
        var v=p.getValue();
        p.setValue(v.replace(/"textEditValue":"[^"]*"/,'"textEditValue":"'+txt+'"')
                    .replace(/"fontTextRunLength":\[[^\]]*\]/,'"fontTextRunLength":['+txt.length+']')
                    .replace(/"fontEditValue":\["[^"]*"\]/,'"fontEditValue":["Makinas-4-Square"]')
                    .replace(/"fontSizeEditValue":\[[^\]]*\]/,'"fontSizeEditValue":['+size+']'), true);
      }
      else if(n==="縦位置") p.setValue(vpos,true);
      else if(n==="縁の太さ") p.setValue(6,true);
      else if(n==="文字色R") p.setValue(100,true);
      else if(n==="文字色G") p.setValue(100,true);
      else if(n==="文字色B") p.setValue(100,true);
      else if(n==="縁色R") p.setValue(STROKE[0],true);
      else if(n==="縁色G") p.setValue(STROKE[1],true);
      else if(n==="縁色B") p.setValue(STROKE[2],true);
    }
    // 位置x
    for(var q=0;q<cl.components.numItems;q++){
      var cp=cl.components[q];
      if(cp.displayName!=="モーション") continue;
      for(var r=0;r<cp.properties.numItems;r++)
        if(cp.properties[r].displayName==="位置") cp.properties[r].setValue([xpos,0.5],true);
    }
  }
}
clean(1); clean(3); clean(4); clean(5); clean(7);
placeStill(1,LOGO,0,TOTAL,17,[0.115971,0.801562]);
tile(3,"ド情熱 逆さで使える消臭スプレー&速乾防水スプレー",35,81.71,0.546);
tile(4,"※詳細は　をチェック！",35,83.76,0.3787);
placeStill(5,E447,0,TOTAL,49.2574,[0.35463,0.83073]);
placeStill(7,E602,274,TOTAL,95.76,[0.768,0.457]);
var names=["V1","V2","V3","V4","V5","V6","V7","V8"];
for(var v=0;v<8;v++){
  var V=seq.videoTracks[v];
  var last=V.clips.numItems? Math.round(Number(V.clips[V.clips.numItems-1].end.ticks)/TPF):0;
  log(names[v]+" clips="+V.clips.numItems+" end="+last);
}
proj.save();
var f2=new File(OUT); f2.encoding="UTF8"; f2.open("w"); f2.write(L.join("\n")); f2.close();
return "done";
