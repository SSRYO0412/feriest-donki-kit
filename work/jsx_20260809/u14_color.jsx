var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/u14.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var TPF=8467200000;
var COL=[94.9,43.9,31.0];   // #F2704F 海老のコーラル
var EPR="@@AME_PRESET@@";
function T(t){ var x=new Time(); x.ticks=String(t); return x; }
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
var seq=null;
for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
for(var v=6;v<=7;v++){
  var tr=seq.videoTracks[v];
  for(var k=0;k<tr.clips.numItems;k++){
    var m=null; try{ m=tr.clips[k].getMGTComponent(); }catch(e){}
    if(!m) continue;
    var txt="";
    for(var q=0;q<m.properties.numItems;q++){
      var p=m.properties[q], n=p.displayName;
      if(n==="本文"){ var b=p.getValue(); var a1=b.match(/"textEditValue":"([^"]*)"/); txt=a1?a1[1]:"?"; }
      else if(n==="文字色R") p.setValue(COL[0],true);
      else if(n==="文字色G") p.setValue(COL[1],true);
      else if(n==="文字色B") p.setValue(COL[2],true);
    }
    var chk=[];
    for(var q=0;q<m.properties.numItems;q++){
      var p=m.properties[q], n=p.displayName;
      if(n==="文字色R"||n==="文字色G"||n==="文字色B") chk.push(n+"="+p.getValue());
    }
    log("V"+(v+1)+" 「"+txt+"」 "+chk.join(" "));
  }
}
proj.save();
seq.setInPoint(T(162*TPF)); seq.setOutPoint(T(227*TPF));
log("書き出し= "+seq.exportAsMediaDirect("@@FERIEST_ROOT@@/02_work/premiere/verify_20260809/c04_color",EPR,1));
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
