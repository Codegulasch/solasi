const {JSDOM}=require("jsdom");const fs=require("fs");const path=require("path");const APP=path.join(__dirname,"..","..","app");
const html=fs.readFileSync(path.join(APP,"static","index.html"),"utf8");
const cfg=JSON.parse(require("child_process").execSync(`python3 -c "import json,controller;print(json.dumps(controller.DEFAULT_CONFIG))"`,{cwd:APP,env:{...process.env,SOLASI_DATA:require("os").tmpdir()}}).toString());
cfg.grid.entity="";const saved=[];
const status={pv_w:3000,bat_w:-1100,house_w:1380,connected:true,enabled:true,dry_run:true,surplus_enabled:true,surplus_dry_run:true,meter_ok:true,grid_w:400,net_balance:400,net_dis:400,t_target:390,eco_active:false,avg_soc:60,blocked_w:0,want:"Entladen",surplus_w:1620,
 units:[{name:"Speicher A",soc:80,set:0,real:0,plan:280,force:false,available:false,mode:"self_consumption",dir:"discharge"},{name:"Speicher B",soc:40,set:0,real:0,plan:110,force:true,available:true,mode:"third_party_control",dir:"discharge"}],
 slots:[{name:"Wallbox",ent:"switch.wb",num:"number.wb",state:"on",own_w:1380,num_v:6}],
 events:[{ts:"12:00:01",level:"test",msg:"Test: Speicher A: 0 W → 280 W"},{ts:"12:00:00",level:"error",msg:"<b>x</b>"}]};
const ents=[{id:"sensor.grid",name:"Netz",domain:"sensor"},{id:"number.a",name:"A",domain:"number"},{id:"switch.wb",name:"WB",domain:"switch"},{id:"select.m",name:"M",domain:"select"}];
const errors=[];
const dom=new JSDOM(html,{runScripts:"dangerously",pretendToBeVisual:true,url:"http://localhost/",
 beforeParse(w){
  w.fetch=async(u,o)=>{const j=o&&o.method==="POST"?(saved.push(JSON.parse(o.body)),{ok:true}):u==="api/config"?cfg:u==="api/status"?status:ents;return{json:async()=>j}};
  w.confirm=()=>true;
  w.addEventListener("error",e=>errors.push(e.message));
 }});
const w=dom.window,d=w.document;
(async()=>{
 await new Promise(r=>setTimeout(r,400));
 const ok=(c,m)=>{if(!c){console.log("FAIL:",m);process.exitCode=1}else console.log("ok  :",m)};
 ok(d.querySelector(".welcome")!==null&&d.querySelector(".welcome").textContent.includes("Willkommen bei SOLASI"),"Willkommensseite ohne Zähler");
 d.querySelector(".welcome button").click();
 ok(d.getElementById("p-units").classList.contains("act"),"Button führt zur Einrichtung");
 ok(d.title==="SOLASI"&&d.querySelector(".brand b").textContent==="SOLASI","Name SOLASI");
 process.exit(process.exitCode||0);
})();
