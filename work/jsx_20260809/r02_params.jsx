var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ref_params.txt";
var REF="6822d0d1-041a-46a0-a5ff-735087200a01";
var TPF=8467200000;
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===REF) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0.7人前うどん") seq=proj.sequences[s];
function dumpClip(v,k,label){
  var cl=seq.videoTracks[v].clips[k];
  var OFF=cl.inPoint.seconds;
  var sf=Math.round(Number(cl.start.ticks)/TPF), ef=Math.round(Number(cl.end.ticks)/TPF);
  log("######## "+label+"  "+sf+"-"+ef+"F  inPoint="+OFF.toFixed(3));
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q];
    log("  --- "+cp.displayName+" ("+cp.properties.numItems+"項目)");
    for(var r=0;r<cp.properties.numItems;r++){
      var p=cp.properties[r];
      var val="";
      try{ val=String(p.getValue()); }catch(e){ val="(取得不可)"; }
      if(val.length>90) val=val.substring(0,90)+"…";
      var tv=false; try{ tv=p.isTimeVarying(); }catch(e){}
      var kf="";
      if(tv){
        try{
          var ks=p.getKeys();
          if(ks && ks.length){
            var arr=[];
            for(var z=0;z<ks.length && z<20;z++){
              var rel=ks[z].seconds-OFF;
              var vv=""; try{ vv=String(p.getValueAtKey(ks[z])); }catch(e){}
              arr.push(rel.toFixed(3)+"s="+vv);
            }
            kf="  KF["+ks.length+"]: "+arr.join(" , ");
          }
        }catch(e){ kf="  KF取得不可"; }
      }
      log("      "+p.displayName+" = "+val+(tv?"  ★可変":"")+kf);
    }
  }
}
dumpClip(3,0,"V3 テロップ[0]");
dumpClip(3,3,"V3 テロップ[3]");
dumpClip(1,0,"V1 調整レイヤー[0] トランスフォーム");
dumpClip(1,4,"V1 調整レイヤー[4] Lumetri");
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
