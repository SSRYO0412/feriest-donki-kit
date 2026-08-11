var L=[]; function log(s){L.push(String(s));}
for(var i=0;i<app.projects.numProjects;i++){
  var p=app.projects[i];
  var seqs=[];
  for(var s=0;s<p.sequences.numSequences;s++) seqs.push(p.sequences[s].name);
  log("["+i+"] "+p.name+"\n     documentID="+p.documentID+"\n     path="+p.path+"\n     seqs("+p.sequences.numSequences+")="+seqs.join(", "));
}
var f=new File("@@BRIDGE_DIR@@/plist.txt"); f.encoding="UTF-8"; f.lineFeed="Unix"; f.open("w"); f.write(L.join("\n")); f.close();
return "ok";
