var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/b09.txt";
var TPF=8467200000;
var proj=null;
for(var i=0;i<app.projects.numProjects;i++)
  if(app.projects[i].path && app.projects[i].path.indexOf("FERIEST_0802_spray_v1")>=0) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++)
  if(proj.sequences[s].name==="0802_spray") seq=proj.sequences[s];
proj.openSequence(seq.sequenceID);
var V1=seq.videoTracks[0];
// c11 = start 232F のクリップ(a0803)を除去し、c12(a0802)を 232-274 に敷き直す
var t232=232*TPF;
for(var k=V1.clips.numItems-1;k>=0;k--){
  var c=V1.clips[k];
  if(Math.round(Number(c.start.ticks)/TPF)===232){ c.remove(false,false); log("c11除去"); }
}
V1=seq.videoTracks[0];
// c12 を前へ伸ばす: start=232, 元 in 点も 14F 手前へ(ソース連続)
for(var k=0;k<V1.clips.numItems;k++){
  var c=V1.clips[k];
  if(Math.round(Number(c.start.ticks)/TPF)===246){
    var newIn=c.inPoint.seconds-14/30;
    var ip=new Time(); ip.seconds=newIn;
    c.inPoint=ip;
    var st=new Time(); st.ticks=String(232*TPF);
    c.start=st;
    log("c12: start=232F in="+newIn.toFixed(3));
    // ズームキーを打ち直し(inPoint基準・42F)
    for(var q=0;q<c.components.numItems;q++){
      var cp=c.components[q];
      if(cp.displayName!=="モーション") continue;
      for(var r=0;r<cp.properties.numItems;r++){
        var pr=cp.properties[r], n=pr.displayName;
        if(n==="スケール"||n==="スケール (高さ)"||n==="スケール (幅)"){
          var ks=null; try{ ks=pr.getKeys(); }catch(e){}
          if(ks) for(var z=ks.length-1;z>=0;z--){ try{ pr.removeKey(ks[z]); }catch(e){} }
          var OFF=c.inPoint.seconds;
          try{ pr.setTimeVarying(true); pr.addKey(OFF); pr.setValueAtKey(OFF,50,true);
               pr.addKey(OFF+42/30); pr.setValueAtKey(OFF+42/30,56,true); }catch(e){ log("★key:"+e); }
        }
      }
    }
  }
}
// 検算
V1=seq.videoTracks[0];
var prevEnd=0,bad=0;
for(var k=0;k<V1.clips.numItems;k++){
  var c=V1.clips[k];
  var st=Math.round(Number(c.start.ticks)/TPF), en=Math.round(Number(c.end.ticks)/TPF);
  if(st!==prevEnd){ log("★隙間 clip"+k+" st="+st+" prev="+prevEnd); bad++; }
  prevEnd=en;
}
log("clips="+V1.clips.numItems+" 終端="+prevEnd+" 隙間="+bad);
proj.save();
var f2=new File(OUT); f2.encoding="UTF8"; f2.open("w"); f2.write(L.join("\n")); f2.close();
return "done";
