var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ref_adj.txt";
var REF="6822d0d1-041a-46a0-a5ff-735087200a01";
var TPF=8467200000;
var WANT=["強度","色温度","色かぶり補正","彩度","露光量","コントラスト","ハイライト","シャドウ","白レベル","黒レベル","自然な彩度"];
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===REF) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0.7人前うどん") seq=proj.sequences[s];
function has(a,x){ for(var i=0;i<a.length;i++) if(a[i]===x) return true; return false; }
for(var v=1;v<=2;v++){
  var tr=seq.videoTracks[v];
  log("======== V"+v+"  "+tr.clips.numItems+"枚");
  for(var k=0;k<tr.clips.numItems;k++){
    var cl=tr.clips[k];
    var OFF=cl.inPoint.seconds;
    var sf=Math.round(Number(cl.start.ticks)/TPF), ef=Math.round(Number(cl.end.ticks)/TPF);
    var line="  ["+k+"] "+sf+"-"+ef+"F";
    var tf="", lum=[];
    for(var q=0;q<cl.components.numItems;q++){
      var cp=cl.components[q];
      if(cp.displayName==="トランスフォーム"){
        for(var r=0;r<cp.properties.numItems;r++){
          var p=cp.properties[r];
          var tv=false; try{ tv=p.isTimeVarying(); }catch(e){}
          if(!tv) continue;
          try{
            var ks=p.getKeys(); var arr=[];
            for(var z=0;z<ks.length;z++){
              var rel=ks[z].seconds-OFF;
              arr.push(Math.round(rel*30)+"F:"+p.getValueAtKey(ks[z]));
            }
            tf+=" ["+p.displayName+" "+arr.join(" → ")+"]";
          }catch(e){}
        }
      }
      if(cp.displayName==="Lumetri カラー"){
        for(var r=0;r<cp.properties.numItems;r++){
          var p=cp.properties[r];
          if(!has(WANT,p.displayName)) continue;
          var vv=""; try{ vv=String(p.getValue()); }catch(e){ continue; }
          if(vv.length>14) continue;
          lum.push(p.displayName+"="+vv);
        }
      }
    }
    if(tf) line+="  TF:"+tf;
    if(lum.length) line+="  LUM: "+lum.join(" / ");
    log(line);
  }
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
