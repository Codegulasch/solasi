// Erster Start ohne Zähler: der Einrichtungsassistent führt durch alle Schritte.
const {JSDOM}=require("jsdom");const path=require("path");const fs=require("fs");const APP=path.join(__dirname,"..","..","app");
const html=fs.readFileSync(path.join(APP,"static","index.html"),"utf8");
const cfg=JSON.parse(require("child_process").execSync(`python3 -c "import json,controller;print(json.dumps(controller.DEFAULT_CONFIG))"`,{cwd:APP,env:{...process.env,SOLASI_DATA:require("os").tmpdir()}}).toString());
cfg.grid.entity="";const saved=[];
const status={pv_w:3000,bat_w:-1100,house_w:1380,connected:true,enabled:true,dry_run:true,surplus_enabled:false,meter_ok:true,grid_w:400,net_balance:400,net_dis:400,t_target:390,eco_active:false,avg_soc:60,blocked_w:0,want:"Entladen",
 units:[{name:"Speicher A",soc:80,set:0,real:0,plan:280,force:false,available:true,mode:"third_party_control",dir:"discharge"}],slots:[],
 events:[{ts:"12:00:01",level:"test",msg:"Test: Speicher A: 0 W → 280 W"}]};
const ents=[{id:"sensor.netzleistung",name:"Netzleistung",domain:"sensor",state:"412",unit:"W"},{id:"sensor.solar_gesamt",name:"Solar gesamt",domain:"sensor",state:"900",unit:"W"},
 {id:"sensor.temp",name:"Temperatur",domain:"sensor",state:"21",unit:"°C"},{id:"number.a",name:"A",domain:"number",state:"0",unit:""},{id:"select.dir",name:"Richtung",domain:"select",state:"discharge",unit:""},{id:"sensor.soc_a",name:"SOC",domain:"sensor",state:"80",unit:"%"}];
const errors=[];
const dom=new JSDOM(html,{runScripts:"dangerously",pretendToBeVisual:true,url:"http://localhost/",
 beforeParse(w){
  w.scrollTo=()=>{};
  w.fetch=async(u,o)=>{
    let j;
    if(o&&o.method==="POST"){const b=JSON.parse(o.body);saved.push(b);Object.assign(cfg,b);j={ok:true};}
    else if(u==="api/config")j=cfg;else if(u==="api/status")j=status;
    else if(u.startsWith("api/selfcheck"))j={summary:{ok:1,warn:1,error:0,info:0},items:[{area:"Speicher A",item:"Ladestand",status:"warn",text:"sensor.soc_a meldet keinen Wert",hint:"Sensor prüfen"},{area:"Zähler",item:"Netzleistung",status:"ok",text:"412 W",hint:""}],curtail:{}};
    else if(u.startsWith("api/stats"))j={days:[],total:{}};
    else if(u.startsWith("api/device_sensors"))j=[];
    else if(u.startsWith("api/entity_options"))j={options:[]};
    else if(u.startsWith("api/notify"))j=[];
    else j=ents;
    return{json:async()=>j}};
  w.confirm=()=>true;
  w.addEventListener("error",e=>errors.push(e.message));
 }});
const w=dom.window,d=w.document;
const wait=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 await wait(500);
 const ok=(c,m)=>{if(!c){console.log("FAIL:",m);process.exitCode=1}else console.log("ok  :",m)};
 ok(d.getElementById("p-setup").classList.contains("act")&&d.body.classList.contains("first"),"Ohne Zähler startet der Einrichtungsassistent ohne Seitenleiste");
 ok(d.querySelectorAll(".vsteps > div").length>=6&&d.querySelector(".vsteps .cur").textContent.includes("Willkommen"),"Schrittliste links, Willkommen aktiv");
 ok(d.getElementById("p-setup").textContent.includes("Willkommen bei SOLASI"),"Willkommenstext");
 d.getElementById("wz_next").click();await wait(50);
 ok(d.querySelector(".vsteps .cur").textContent.includes("Zähler")&&d.getElementById("wz_next").disabled,"Schritt Zähler: Weiter erst nach Auswahl");
 const btns=[...d.querySelectorAll("#wz_grid button")].map(b=>b.dataset.id);
 ok(btns[0]==="sensor.netzleistung"&&!btns.includes("sensor.temp"),"Vorschläge: passender Sensor zuerst, nur Leistungssensoren");
 d.querySelector('#wz_grid button').click();await wait(50);
 ok(cfg.grid.entity==="sensor.netzleistung"&&d.querySelector(".livebox").textContent.includes("412"),"Auswahl setzt den Zähler und zeigt den aktuellen Wert");
 ok(d.getElementById("wz_next").disabled===false,"Weiter ist jetzt möglich");
 d.getElementById("wz_next").click();await wait(50);
 ok(d.querySelector(".vsteps .cur").textContent.includes("Speicher")&&d.getElementById("f_units_0_num")!==null&&d.getElementById("wz_next").disabled,"Schritt Speicher: Felder da, Weiter gesperrt bis eingerichtet");
 for(const [id,v] of [["f_units_0_num","number.a"],["f_units_0_dir","select.dir"]]){const e=d.getElementById(id);e.value=v;e.dispatchEvent(new w.Event("input"));}
 await wait(50);
 ok(d.getElementById("wz_next").disabled===false,"Nach Eingabe von Leistung und Richtung geht es weiter");
 ok(d.getElementById("wz_second")!==null,"Zweiter Speicher lässt sich hinzufügen");
 d.getElementById("wz_next").click();await wait(50);
 ok(d.querySelector(".vsteps .cur").textContent.includes("Solar")&&d.getElementById("f_units_0_pv")!==null,"Schritt Solar und Haus: PV-Feld");
 d.getElementById("wz_next").click();await wait(300);
 ok(saved.length>=1&&saved.at(-1).grid.entity==="sensor.netzleistung"&&saved.at(-1).units[0].num==="number.a","Beim Prüfen werden die Einstellungen gespeichert");
 ok(d.getElementById("p-setup").textContent.includes("1 Hinweis")&&d.getElementById("p-setup").textContent.includes("Sensor prüfen"),"Prüfen zeigt Hinweise des Selbsttests");
 d.getElementById("wz_next").click();await wait(200);
 ok(saved.at(-1).enabled===true&&saved.at(-1).dry_run===true,"Testlauf schaltet Regelung ein, aber nur im Testmodus");
 ok(d.getElementById("p-setup").textContent.includes("Testlauf"),"Testlauf-Seite");
 d.getElementById("wz_next").click();await wait(100);
 ok(d.getElementById("p-status").classList.contains("act")&&!d.body.classList.contains("first"),"Fertig führt zur Übersicht, Seitenleiste wieder da");
 ok(d.title==="SOLASI"&&d.querySelector(".brand b").textContent==="SOLASI","Name SOLASI");
 ok(errors.length===0,"keine JS-Fehler "+errors.join("|"));
 process.exit(process.exitCode||0);
})();
