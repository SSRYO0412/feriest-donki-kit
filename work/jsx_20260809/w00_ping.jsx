var f=new File("@@BRIDGE_DIR@@/ping.txt"); f.encoding="UTF-8"; f.open("w");
f.write("projects="+app.projects.numProjects+"\nversion="+app.version);
f.close();
return "pong";
