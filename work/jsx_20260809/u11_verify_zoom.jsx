var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/u11.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var TPF=8467200000;
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
var V1=seq.videoTracks[0];
var ng=0;
for(var k=0;k<V1.clips.numItems;k++){
  var cl=V1.clips[k];
  var sf=Math.round(Number(cl.start.ticks)/TPF), ef=Math.round(Number(cl.end.ticks)/TPF);
  var OFF=cl.inPoint.seconds, NF=ef-sf;
  var lock="?", keys=null, pname="";
  for(var q=0;q<cl.components.numItems;q++){
    var cp=cl.components[q];
    if(cp.displayName!=="トランスフォーム") continue;
    for(var r=0;r<cp.properties.numItems;r++){
      var p=cp.properties[r], n=p.displayName;
      if(n==="縦横比を固定") lock=String(p.getValue());
      // ★固定=trueだと名前が「スケール」、falseだと「スケール (高さ)」になる
      if(n==="スケール"||n==="スケール (高さ)"){
        var tv=false; try{ tv=p.isTimeVarying(); }catch(e){}
        if(tv){ keys=p.getKeys(); pname=n;
          var arr=[]; for(var z=0;z<keys.length;z++) arr.push(Math.round((keys[z].seconds-OFF)*30)+"F:"+p.getValueAtKey(keys[z]));
          keys={n:keys.length, s:arr.join("/"), head:Math.abs(keys[0].seconds-OFF), last:Math.round((keys[keys.length-1].seconds-OFF)*30)};
        }
      }
    }
  }
  var bad=[];
  if(lock!=="true") bad.push("縦横比未固定");
  if(!keys) bad.push("★キーなし");
  else{
    if(keys.head>0.01) bad.push("★頭ズレ"+keys.head.toFixed(3)+"秒");
    if(keys.last>NF-1) bad.push("★最終キー"+keys.last+"Fがクリップ尺"+NF+"Fを超過");
  }
  if(bad.length) ng++;
  log("c0"+(k+1)+" "+sf+"-"+ef+"F("+NF+"F) 固定="+lock+" 名="+pname+" keys="+(keys?keys.s:"なし")+(bad.length?("   "+bad.join(" / ")):"   OK"));
}
log("");
log("不備のあるカット="+ng+"（0が正常）");
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
