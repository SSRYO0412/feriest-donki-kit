var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/b04.txt";
var TPF=8467200000;
var MG="@@KIT_ROOT@@/skill/donki-feriest/assets/telop_3slot_v22.mogrt";
var STROKE=[24,22,20], WHITE=[100,100,100], YEL=[93.7,91.4,9.8];
// [track(0-based), text, font, size, 縦位置, color, startF, endF, emph]
var ROWS=[
 [2,"その靴、そのまま履くの","mplus-1p-heavy",68.948,46.0,WHITE,0,56,null],
 [6,"ちょっと待って〜!!","mplus-1p-heavy",68.948,52.9,YEL,0,56,{s:1,e:9}],
 [2,"靴を持たずに逆さで","mplus-1p-heavy",68.948,46.0,WHITE,56,108,null],
 [6,"そのままシューッ!","mplus-1p-heavy",68.948,52.9,WHITE,56,108,null],
 [2,"届きにくい奥まで","mplus-1p-heavy",68.948,46.0,WHITE,108,160,null],
 [6,"しっかり消臭!","mplus-1p-heavy",68.948,52.9,WHITE,108,160,null],
 [2,"雨が降りそうなら","mplus-1p-heavy",68.948,46.0,WHITE,160,232,null],
 [6,"こっちも忘れないで!","mplus-1p-heavy",68.948,52.9,WHITE,160,232,null],
 [2,"速乾だから","mplus-1p-heavy",68.948,46.0,WHITE,232,274,null],
 [6,"出発前でも余裕〜!","mplus-1p-heavy",68.948,52.9,WHITE,232,274,null],
 [2,"これ知ったら戻れない　","mplus-1p-heavy",68.948,47.5,WHITE,274,316,null]];
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++)
  if(app.projects[i].path && app.projects[i].path.indexOf("FERIEST_0802_spray_v1")>=0) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++)
  if(proj.sequences[s].name==="0802_spray") seq=proj.sequences[s];
proj.openSequence(seq.sequenceID);
if(seq.videoTracks.numTracks<8){
  try{ qe.project.getActiveSequence().addTracks(8-seq.videoTracks.numTracks, seq.videoTracks.numTracks,0,0,0,0); }
  catch(e){ log("★addTracks例外:"+e); }
}
log("tracks="+seq.videoTracks.numTracks);
for(var tr=0;tr<ROWS.length;tr++){} // noop
// 既存を掃除(V3,V7=idx2,6)
var idxs=[2,6];
for(var x=0;x<idxs.length;x++){
  var V=seq.videoTracks[idxs[x]];
  for(var k=V.clips.numItems-1;k>=0;k--) V.clips[k].remove(false,false);
}
var placed=0, ngRun=0;
for(var r=0;r<ROWS.length;r++){
  var row=ROWS[r];
  var cl=null;
  try{ cl=seq.importMGT(MG, T(row[6]*TPF), row[0], 0); }catch(e){ log("★importMGT例外 r"+r+":"+e); continue; }
  if(!cl){ log("★importMGT null r"+r); continue; }
  cl.end=T(row[7]*TPF);
  var m=cl.getMGTComponent();
  if(!m){ log("★MGT無し r"+r); continue; }
  var txt=row[1], font=row[2], size=row[3];
  for(var q=0;q<m.properties.numItems;q++){
    var p=m.properties[q], n=p.displayName;
    if(n==="本文"){
      var v=p.getValue();
      p.setValue(v.replace(/"textEditValue":"[^"]*"/,'"textEditValue":"'+txt+'"')
                  .replace(/"fontTextRunLength":\[[^\]]*\]/,'"fontTextRunLength":['+txt.length+']')
                  .replace(/"fontEditValue":\["[^"]*"\]/,'"fontEditValue":["'+font+'"]')
                  .replace(/"fontSizeEditValue":\[[^\]]*\]/,'"fontSizeEditValue":['+size+']'), true);
    }
    else if(n==="縦位置")   p.setValue(row[4],true);
    else if(n==="縁の太さ") p.setValue(11,true);
    else if(n==="文字色R")  p.setValue(row[5][0],true);
    else if(n==="文字色G")  p.setValue(row[5][1],true);
    else if(n==="文字色B")  p.setValue(row[5][2],true);
    else if(n==="縁色R")    p.setValue(STROKE[0],true);
    else if(n==="縁色G")    p.setValue(STROKE[1],true);
    else if(n==="縁色B")    p.setValue(STROKE[2],true);
    else if(row[8] && n==="出現の型")      p.setValue(1,true);
    else if(row[8] && n==="出現の尺")      p.setValue(0.15,true);
    else if(row[8] && n==="強調の出方")    p.setValue(1,true);
    else if(row[8] && n==="強調1開始")     p.setValue(row[8].s,true);
    else if(row[8] && n==="強調1終わり")   p.setValue(row[8].e,true);
    else if(row[8] && n==="強調1の大きさ") p.setValue(40,true);
    else if(row[8] && n==="強調1の遅れ")   p.setValue(0.10,true);
    else if(row[8] && n==="強調1の縦オフセット") p.setValue(6,true);
    else if(row[8] && n==="強調1色R") p.setValue(YEL[0],true);
    else if(row[8] && n==="強調1色G") p.setValue(YEL[1],true);
    else if(row[8] && n==="強調1色B") p.setValue(YEL[2],true);
  }
  var b=""; for(var q=0;q<m.properties.numItems;q++) if(m.properties[q].displayName==="本文") b=m.properties[q].getValue();
  var a=b.match(/"fontTextRunLength":\[([^\]]*)\]/);
  if(!(a&&Number(a[1])===txt.length)){ ngRun++; log("★run長不一致 r"+r+" "+txt); }
  placed++;
}
log("placed="+placed+"/11 run長NG="+ngRun);
proj.save();
var f2=new File(OUT); f2.encoding="UTF8"; f2.open("w"); f2.write(L.join("\n")); f2.close();
return "done";
