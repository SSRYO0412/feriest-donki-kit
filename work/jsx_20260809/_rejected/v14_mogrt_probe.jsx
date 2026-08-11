// ★★★ 却下版・実行禁止 ★★★
// このスクリプトは MOGRT telop_3slot_v20 を参照する。正本は v22。
// v20 は色がカラーピッカー方式でスクリプトから触れない（TELOP-SPEC.md L94 / SETUP.md 4節）。
// 履歴として残すが実行してはならない。後続の t/u/w/x 系列が v22 で同じ役割を果たしている。
return "★中断: v20 参照の却下版です。実行禁止（正本は v22 系列）";
var L=[]; function log(s){L.push(String(s));}
var OUT="@@BRIDGE_DIR@@/ebi_v14.txt";
var DOC="3ea1839d-a639-48ba-acae-e0d506adfd39";
var MG="@@KIT_ROOT@@/skill/donki-feriest/assets/telop_3slot_v20.mogrt";
var TPS=254016000000, TPF=8467200000;
var proj=null;
for(var i=0;i<app.projects.numProjects;i++) if(app.projects[i].documentID===DOC) proj=app.projects[i];
if(!proj){ log("★中断: 対象なし"); }
else{
  var f0=new File(MG); log("mogrt exists="+f0.exists);
  var seq=null;
  for(var s=0;s<proj.sequences.numSequences;s++) if(proj.sequences[s].name==="0801_ebi") seq=proj.sequences[s];
  // V3 に1枚だけ置く（3トラック目 index=2）
  var V3=seq.videoTracks[2];
  for(var k=V3.clips.numItems-1;k>=0;k--) V3.clips[k].remove(false,false);
  var clip = seq.importMGT(MG, String(0), 2, -1);   // ★ticksは文字列
  log("importMGT 戻り="+(clip? "TrackItem":"null"));
  V3 = seq.videoTracks[2];
  log("V3 clips="+V3.clips.numItems);
  if(V3.clips.numItems>0){
    var cl=V3.clips[0];
    var m=null; try{ m=cl.getMGTComponent(); }catch(e){}
    log("getMGTComponent="+(m? "OK(AE製)":"★null(Premiere製→使えない)"));
    if(m){
      log("=== パラメータ一覧 ("+m.properties.numItems+"件) ===");
      for(var k=0;k<m.properties.numItems;k++){
        var p=m.properties[k];
        var v="";
        try{ v=String(p.getValue()); }catch(e){ v="(取得不可)"; }
        if(v.length>160) v=v.substring(0,160)+"…";
        log("  ["+k+"] "+p.displayName+" = "+v);
      }
    }
  }
}
var f=new File(OUT); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
