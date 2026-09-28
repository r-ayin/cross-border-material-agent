const https=require('https'),http=require('http'),fs=require('fs');
// ECS pitch-pub proxy (hardened 2026-09-28): token-gated TLS 3083 -> loopback 13082 (VM reverse tunnel)
// abort-safe: client abort destroys upstream; upstream error ends response once; uncaught guards keep service alive.
const TOKEN=fs.readFileSync('/root/pitch-pub-token','utf8').trim();
const OPTS={key:fs.readFileSync('/root/dsh-ecs-relay.key'),cert:fs.readFileSync('/root/dsh-ecs-relay.crt')};
process.on('uncaughtException',e=>{console.error('uncaught:',e.message);});
process.on('unhandledRejection',e=>{console.error('unhandled:',(e&&e.message)||e);});
https.createServer(OPTS,(req,res)=>{
  let p; try{p=decodeURIComponent(req.url);}catch(e){p=req.url;}
  const pre='/'+TOKEN;
  if(p!==pre&&!p.startsWith(pre+'/')){res.writeHead(404,{'content-type':'text/plain'});res.end('not found');return;}
  const sub=p.slice(pre.length)||'/';
  const h={...req.headers}; h.host='127.0.0.1:13082';
  const pr=http.request({host:'127.0.0.1',port:13082,path:sub,method:req.method,headers:h},(u)=>{
    if(res.destroyed||res.writableEnded){u.resume();return;}
    try{res.writeHead(u.statusCode,u.headers);}catch(e){u.resume();return;}
    u.on('error',()=>{res.destroy();});
    u.pipe(res);
  });
  pr.on('error',e=>{
    if(!res.headersSent){try{res.writeHead(502,{'content-type':'text/plain'});}catch(_){}}
    if(!res.writableEnded){try{res.end('upstream: '+e.message);}catch(_){}}
  });
  res.on('close',()=>{pr.destroy();});
  res.on('error',()=>{pr.destroy();});
  req.on('error',()=>{pr.destroy();});
  req.pipe(pr);
}).listen(3083,'0.0.0.0',()=>console.log('pitch-pub listening 3083 (hardened)'));
