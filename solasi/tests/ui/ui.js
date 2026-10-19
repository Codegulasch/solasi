const {JSDOM}=require("jsdom");const fs=require("fs");const path=require("path");const APP=path.join(__dirname,"..","..","app");
const html=fs.readFileSync(path.join(APP,"static","index.html"),"utf8");
const cfg=JSON.parse(require("child_process").execSync(`python3 -c "import json,controller;print(json.dumps(controller.DEFAULT_CONFIG))"`,{cwd:APP,env:{...process.env,SOLASI_DATA:require("os").tmpdir()}}).toString());
cfg.grid.entity="sensor.grid";const saved=[];let replayBody=null;const calls=[];let failDevice=false;let mqttState="verbunden";
const status={mode_id:"balanced",mode_name:"Ausgewogen",mode_icon:"⚖️",mode_effect:{head:"Gibt ab bis 26 %, lädt bis 94 %",units:[{name:"Speicher A",soc:60,state:"ok",text:"darf abgeben"}],note:""},flows:{solar_house:520,solar_battery:260,battery_house:0,grid_house:9},safety:{state:"active",reason:"",since:null},pv_w:780,bat_w:-260,house_w:529,connected:true,enabled:true,dry_run:true,surplus_enabled:true,surplus_dry_run:true,meter_ok:true,grid_w:400,net_balance:400,net_dis:400,t_target:390,eco_active:false,avg_soc:60,blocked_w:0,want:"Entladen",surplus_w:1620,
 units:[{name:"Speicher A",pv:540,soc:80,set:0,real:0,plan:280,force:false,available:false,mode:"self_consumption",dir:"discharge"},{name:"Speicher B",soc:-1,set:0,real:0,plan:110,force:true,available:true,mode:"third_party_control",dir:"discharge"}],
 slots:[{name:"Wallbox",ent:"switch.wb",num:"number.wb",state:"on",own_w:1380,num_v:6}],
 events:[{ts:"12:00:01",level:"test",msg:"Test: Speicher A: 0 W → 280 W"},{ts:"12:00:00",level:"error",msg:"<b>x</b>"}]};
{const now=Math.floor(Date.now()/1000),n=120,t=[],pv=[],house=[];for(let i=0;i<n;i++){t.push(now-(n-1-i)*300);pv.push(Math.round(Math.max(0,Math.sin(i/n*Math.PI)*1600)));house.push(300+(i%7)*20)}status.trend={t,pv,house}
status.meter_view={items:[{entity:"sensor.wh",name:"Wasserzähler Haus",value:552.62,dec:2,unit:"m³",icon:"wasser",color:"water",day:0.18},{entity:"sensor.st",name:"Zählerstand Strom",value:13141.74,dec:2,unit:"kWh",icon:"zaehler",color:"zaehl",day:null}],today:{house:8.4,pv:6.4,imp:1.2,autarky:.88},show_day:true,extra:false};;}
const ents=[{id:"sensor.grid",name:"Netz",domain:"sensor"},{id:"sensor.extra_a",name:"Irgendein Sensor A",domain:"sensor"},{id:"sensor.extra_b",name:"Irgendein Sensor B",domain:"sensor"},{id:"number.a",name:"A",domain:"number"},{id:"switch.wb",name:"WB",domain:"switch"},{id:"select.m",name:"M",domain:"select"}];
const goalsSnap={goals:{reserve:50,precision:70,care:30},derived:{"soc.min":27,"soc.max":94,"soc.hyst":4,"soc.eco_threshold":47,"control.min_gap":5,"control.offset_discharge":9},mode:null,
 modes:[{id:"balanced",name:"Ausgewogen",icon:"⚖️",text:"Nulleinspeisung",reserve:50,precision:70,care:30},{id:"autarky",name:"Max. Autarkie",icon:"🌱",text:"Netz meiden",reserve:10,precision:90,care:10}],
 table:[{path:"soc.min",label:"Mindest-Ladestand",unit:"%",current:15,derived:27,custom:true},{path:"soc.max",label:"Höchst-Ladestand",unit:"%",current:99,derived:94,custom:true}]};
const errors=[];
const dom=new JSDOM(html,{runScripts:"dangerously",pretendToBeVisual:true,url:"http://localhost/",
 beforeParse(w){
  w.fetch=async(u,o)=>{
    const post=o&&o.method==="POST";
    const routes={
      "api/config":()=>post?(saved.push(JSON.parse(o.body)),{ok:true}):cfg,
      "api/status":()=>status,
      "api/mqtt":()=>({state:mqttState,detail:mqttState==="fehler"?"Kein MQTT-Broker gefunden":"",host:"core-mosquitto",enabled:true}),
      "api/card":()=>({installed:true,target:"/homeassistant/www/solasi/solasi-card.js",resource:"registriert",url:"/local/solasi/solasi-card.js?v=1.3.0",restart_needed:false,yaml:"x"}),
      "api/selfcheck":()=>({summary:{ok:5,warn:1,error:1,info:1},curtail:{state:"fehlgeschlagen",note:"Speicher voll, trotzdem 300 W Einspeisung.",since:"04.10. 12:00",export_w:300},
        items:[{area:"Zähler",item:"Netzleistung",status:"warn",text:"sensor.g liefert kW statt W",hint:"Einheit umrechnen"},{area:"Speicher A",item:"Modus-Option",status:"error",text:"nicht vorhanden",hint:""},{area:"Verbindung",item:"Home Assistant",status:"ok",text:"verbunden",hint:""}]}),
      "api/stats":()=>({days:[{date:"2026-10-03",pv:10,house:12,imp:4,exp:2,bat_dis:3,bat_chg:4,autarky:.66,selfcons:.8},{date:"2026-10-04",pv:8,house:11,imp:5,exp:1,bat_dis:2,bat_chg:3,autarky:.55,selfcons:.9}],
        total:{pv:18,house:23,imp:9,exp:3,bat_dis:5,bat_chg:7,autarky:.61,selfcons:.83,saved_eur:4.9,battery_eur:1.75,feedin_eur:.24}}),
      "api/meter_history":()=>({ok:true,entity:"sensor.wh",unit:"m³",name:"Wasserzähler Haus",source:"statistik",days:[{date:"2026-10-14",value:0.2},{date:"2026-10-15",value:0.15},{date:"2026-10-16",value:null},{date:"2026-10-17",value:0.18}]}),
      "api/goals/preview":()=>({goals:JSON.parse(o.body),derived:{"soc.min":40,"soc.max":93,"soc.hyst":4,"soc.eco_threshold":60,"control.min_gap":4,"control.offset_discharge":6}}),
      "api/goals/mode":()=>{const id=JSON.parse(o.body).id;calls.push("mode:"+id);status.mode_id=id;goalsSnap.mode=id;return {ok:true,mode:id,...goalsSnap}},
      "api/goals/custom":()=>{if(o.method==="DELETE"){goalsSnap.modes=goalsSnap.modes.filter(m=>!m.custom);return {ok:true,...goalsSnap}}const b=JSON.parse(o.body);calls.push("custom:"+b.name);goalsSnap.modes.push({id:"mein",name:b.name,icon:"⭐",text:"Eigener Modus",custom:true,reserve:50,precision:70,care:30});return {ok:true,id:"mein",...goalsSnap}},
      "api/goals":()=>goalsSnap,
      "api/me":()=>({name:"Home Assistant",role:"owner",direct:false,roles:{owner:"Besitzer",member:"Mitbewohner",viewer:"Nur lesen"}}),
      "api/accounts":()=>({users:global.ACCTS||[],roles:{owner:"Besitzer",member:"Mitbewohner",viewer:"Nur lesen"}}),
      "api/report":()=>({title:"SOLASI Wochenbericht",text:"Verbrauch 70 kWh.",weekly:false}),
      "api/phases/discover":()=>({sensors:[{entity:"sensor.em_a_power",name:"3EM Phase A Power",kind:"power",phase:"L1",value:"120",unit:"W"},{entity:"sensor.em_b_power",name:"3EM Phase B Power",kind:"power",phase:"L2",value:"80",unit:"W"},{entity:"sensor.em_c_power",name:"3EM Phase C Power",kind:"power",phase:"L3",value:"40",unit:"W"}]}),
      "api/update":()=>({image_version:"2.3.2",running_version:"2.3.2",overlay:!!global.UPD_OV,overlay_active:false,overlay_version:global.UPD_OV?"2.3.3":"",confirmed:false,installed_at:"19.10.2026 18:40",previous_version:global.UPD_OV?"2.3.2.1":"",failure:global.UPD_FAIL?{reason:"Der lokale Stand 2.3.3 beendete sich nach 4 s mit Code 1",at:"19.10. 18:41:00"}:null,direct:false}),
      "api/locks":()=>{const b=JSON.parse(o.body);calls.push("lock:"+b.unit+":"+b.on+":"+(b.until||""));status.locks=status.locks||{};if(b.on)status.locks[b.unit]={until:0};else delete status.locks[b.unit];return {ok:true,locks:status.locks};},
      "api/charge/estimate":()=>({estimate:{kwh:2.5,hours:3.1,power_w:800,rows:[]}}),
      "api/charge/start":()=>{const b=JSON.parse(o.body);if(!(b.target>0))return {ok:false,error:"Ungültiges Ziel"};calls.push("charge:start:"+b.target+":"+b.power_w+":"+(b.units||[]).join("|"));status.charge={active:true,job:{target:b.target,power_w:b.power_w,units:b.units,hours:b.hours,started:Date.now()/1000,source:"Oberfläche",start_soc:{"Speicher A":10}},units:[{name:"Speicher A",soc:10,start:10}],alloc:{"Speicher A":800},estimate:{kwh:2.5,hours:3.1,power_w:800}};return {ok:true,...status.charge};},
      "api/charge/stop":()=>{calls.push("charge:stop");status.charge={active:false,job:null};return {ok:true,changed:true};},
      "api/phases/reset":()=>{calls.push("phases:reset");return {ok:true};},
      "api/hogs/discover":()=>({sensors:[{entity:"sensor.plug_tv_power",name:"Plug TV Power",w:"12"}]}),
      "api/hogs/curve":()=>({dev:"k",res:60,points:[{t:0,w:50},{t:3600,w:120},{t:7200,w:60}],...(/cmp=/.test(String(u))?{compare:[{t:0,w:40},{t:3600,w:90}]}:{})}),
      "api/hogs":()=>({devices:[{id:"k",name:"Kühlschrank",icon:"🧊",phase:"L1",kwh:1.2,share:12,eur_year:60,kwh_year:170,standby_w:30,avg_w:50,peak_w:120,samples:100},
        {id:"t",name:"TV",icon:"📺",phase:"",kwh:0.4,share:4,eur_year:20,kwh_year:60,standby_w:12,avg_w:20,peak_w:90,samples:100}],
        house_kwh:10,measured_kwh:1.6,rest_kwh:8.4,rest_share:84,rest_eur_year:420,minutes:2880,days:7,standby_w:42,standby_eur_year:129,
        info:{since:1700000000,minutes:2880},configured:2,profile:{k:Array(24).fill(40),t:Array(24).fill(null)}}),
      "api/discover":()=>({units:global.DISC||[],grid:[]}),
      "api/defaults":()=>({unit:{name:"Speicher",driver:"anker",state:"active",num:"",dir:"",soc:"",mode:"",capacity_kwh:5,max_dis:800,max_chg:800,can_charge:true,curtail:true}}),
      "api/kill":()=>{calls.push("kill");status.safety={state:"stopped",reason:"Von Hand gestoppt",since:"04.10. 12:00:00"};return {ok:true}},
      "api/resume":()=>{calls.push("resume");status.safety={state:"active",reason:"",since:null};return {ok:true}},
      "api/entity_options":()=>({options:["third_party_control","self_consumption"]}),
      "api/watchdog":()=>({state:"manuell",detail:"Automatisch nicht möglich (HTTP 403). Den Text unten als Automation einfügen.",json:'{"id": "solasi_waechter", "alias": "SOLASI Wächter"}',managed:false}),
      "api/device_sensors":()=>{if(failDevice)throw new Error("simuliert");return [{id:"sensor.dev_charge",name:"Batterie Ladeleistung",state:"140",unit:"W"},{id:"sensor.dev_solar",name:"Solarleistung",state:"540",unit:"W"}]},
      "api/learn":()=>({value:210,nights:[200,220,210],used:231,enabled:true}),
      "api/notify/services":()=>["persistent_notification","notify.mobile_app_pixel"],
      "api/notify/test":()=>({ok:true}),
      "api/replay":()=>{replayBody=JSON.parse(o.body);return {ok:true,hours:24,actual:{imp:8.1,exp:1.2,end_soc:55,min_soc:20,series:{grid:[300,200,-50,100],soc:[80,70,60,55]}},
        current:{imp:7.4,exp:0.1,end_soc:54,min_soc:18,bat_dis:6.2,bat_chg:3.1,curtailed:0,writes:310,eco_h:2.5,series:{grid:[10,20,5,0],soc:[80,72,65,54]}},
        alt:{imp:6.9,exp:0.1,end_soc:50,min_soc:15,bat_dis:6.9,bat_chg:3.1,curtailed:0,writes:240,eco_h:0,series:{grid:[8,15,5,0],soc:[80,70,60,50]}}}}};
    const key=Object.keys(routes).find(k=>u.startsWith(k));
    const j=key?routes[key]():ents;return{json:async()=>j};};
  w.confirm=()=>true;w.scrollTo=()=>{};
  w.addEventListener("error",e=>errors.push(e.message));
 }});
const w=dom.window,d=w.document;
(async()=>{
 await new Promise(r=>setTimeout(r,400));
 const ok=(c,m)=>{if(!c){console.log("FAIL:",m);process.exitCode=1}else console.log("ok  :",m)};
 ok(errors.length===0,"keine JS-Fehler "+errors.join("|"));
 ok(d.querySelectorAll("#p-units .f").length>10,"Anlage-Formular gerendert (einfacher Modus)");
 const simpleCount=d.querySelectorAll("#p-units .f").length;
 ok(d.querySelectorAll("#p-surplus details.fsec").length===4,"Überschuss: Quelle + 3 Verbraucher-Slots als einklappbare Gruppen");
 ok(d.querySelectorAll("#dl-sensor option").length===3&&d.querySelectorAll("#dl-switchy option").length===1,"Entitätslisten gefüllt");
 ok(d.querySelector("#p-status").textContent.includes("390 W")&&d.querySelector("#p-status").textContent.includes("Abregelung"),"Status zeigt Sollwert + Abregelung");
 ok(d.querySelector(".headline").textContent.includes("Im Test: Solar versorgt dein Haus und lädt den Speicher"),"Überschrift in Klartext");
 const fl=d.querySelector(".flow svg").textContent;
 ok(fl.includes("780 W")&&fl.includes("260 W")&&fl.includes("529 W")&&fl.includes("lädt")&&fl.includes("Bezug"),"Energiefluss zeigt Solar 780, Speicher 260 (lädt), Haus 529, Netz Bezug");
 // Linien: Solar -> Haus (520 W), Solar -> Speicher (260 W), Netz -> Haus (9 W); Speicher <-> Haus ist ruhig
 const FH=require("./flowhelp");
 const fsvg=()=>d.querySelector(".flow svg");
 let ln=FH.lines(fsvg());
 ok(ln.sh==="fwd","Solar -> Haus ist aktiv");
 ok(ln.sb==="fwd","Solar -> Speicher ist aktiv (Überschuss lädt den Speicher)");
 ok(ln.bh===null,"Speicher <-> Haus ist ruhig (Speicher wird aus der PV geladen, nicht über das Haus)");
 ok(ln.gh==="fwd","Netz -> Haus läuft Richtung Haus (Bezug)");
 const ev=FH.chips(fsvg());
 ok(ev.length===3&&ev.includes("520 W")&&ev.includes("260 W")&&ev.includes("9 W"),"Linien tragen ihre Werte: 520 W, 260 W, 9 W");
 ok(d.querySelectorAll(".trendbox").length===1&&d.querySelector(".trendbox svg")&&d.querySelector(".trendbox").textContent.includes("Uhr"),"Verlauf-Karte mit Zeitachse");
 const ur=[...d.querySelectorAll(".urow")];
 ok(ur[0].textContent.includes("Eigenverbrauch")&&ur[1].textContent.includes("Extern gesteuert")&&!ur[1].querySelector(".sub").textContent.includes("third_party"),"Speicherzeile: Klartext statt Rohwerte");
 ok(ur[1].querySelector("details")&&ur[1].querySelector("details").textContent.includes("third_party_control"),"Rohwerte unter Technische Details");
 const ps=d.querySelector("#p-status");
 ok(ps.querySelectorAll(".sfm").length===1&&ps.textContent.includes("Tagesverbrauch")&&ps.textContent.includes("8,4")&&ps.textContent.includes("Wasserzähler Haus")&&ps.textContent.includes("552,62")&&ps.textContent.includes("13.141,74"),"Übersicht: Tagesverbrauch und Zähler als eigene Reihe");
 ok(ps.textContent.includes("+180 l")&&!ps.textContent.includes("0,18 m³")&&!ps.querySelector(".sfm").textContent.includes("Zählerstand Strom +"),"Tagesverbrauch des Wasserzählers, keiner beim Stromzähler ohne Wert");
 ok(ps.querySelector(".sfm").closest(".card")&&!ps.querySelector(".sfm").closest(".hero"),"Zählerreihe getrennt vom Energiefluss");
 ok(d.getElementById("modetext").textContent==="Testmodus"&&d.getElementById("conntext").textContent==="Verbunden","Status-Pillen");
 ok(d.querySelector(".bat svg rect[fill*=ok]")!==null,"Batterie-Symbol grün bei hohem Ladestand");
 ok(d.querySelector("#p-status").textContent.includes("Wallbox"),"Überschuss-Slot im Status");
 ok(d.querySelector("#log").innerHTML.includes("&lt;b&gt;x")&&!d.querySelector("#log b"),"Protokoll maskiert HTML (kein XSS)");
 // Eingabe -> Speichern
 const inp=d.getElementById("f_grid_entity");inp.value="sensor.grid";inp.dispatchEvent(new w.Event("input"));
 const chk=d.getElementById("f_features_eco");chk.checked=false;chk.dispatchEvent(new w.Event("change"));
 ok(d.getElementById("f_control_min_gap")===null,"Experten-Feld min_gap im einfachen Modus ausgeblendet");
 const ex=d.getElementById("q_expert");ex.checked=true;ex.dispatchEvent(new w.Event("change"));await new Promise(r=>setTimeout(r,100));
 ok(d.querySelectorAll("#p-units .f").length>simpleCount&&d.querySelector(".advnote")===null,"Experten-Modus zeigt mehr Felder");
 ok(w.localStorage.getItem("solasi_expert")==="1","Experten-Modus wird gemerkt");
 const n=d.getElementById("f_control_min_gap");n.value="7";n.dispatchEvent(new w.Event("input"));
 d.getElementById("save").click();await new Promise(r=>setTimeout(r,100));
 const s=saved.at(-1);
 ok(s&&s.grid.entity==="sensor.grid"&&s.features.eco===false&&s.control.min_gap===7,"Änderungen landen im gespeicherten JSON");
 // Schnellschalter
 const q=d.getElementById("q_dry");q.checked=false;q.dispatchEvent(new w.Event("change"));await new Promise(r=>setTimeout(r,100));
 ok(saved.at(-1).dry_run===false,"Schnellschalter Testmodus speichert sofort");
 w.showPage("card");await new Promise(r=>setTimeout(r,100));
 const pc=d.getElementById("p-card").textContent;
 ok(pc.includes("custom:solasi-card")&&pc.includes("registriert")&&pc.includes("sensor.solasi_pv_power"),"Seite Dashboard-Karte zeigt YAML, Status, Entitäten");
 ok(d.querySelector("#p-card a[href='card.js']")===null,"Kein manueller Download nötig, wenn automatisch installiert");

 const go=async p=>{w.showPage(p);await new Promise(r=>setTimeout(r,150));};
 // Entitäten (MQTT)
 await go("mqtt");let tm=d.getElementById("p-mqtt").textContent;
 ok(tm.includes("verbunden")&&tm.includes("core-mosquitto")&&tm.includes("Energiezähler")&&tm.includes("Not-Aus"),"MQTT-Seite zeigt Status, Broker und angelegte Entitäten");
 d.getElementById("mqtt_host").value="192.168.1.5";d.getElementById("mqtt_port").value="1884";d.getElementById("mqtt_enabled").checked=false;
 d.getElementById("mqtt_save").click();await new Promise(r=>setTimeout(r,100));
 ok(saved.at(-1).mqtt.host==="192.168.1.5"&&saved.at(-1).mqtt.port===1884&&saved.at(-1).mqtt.enabled===false,"MQTT-Einstellungen werden gespeichert");
 mqttState="fehler";await go("mqtt");tm=d.getElementById("p-mqtt").textContent;
 ok(tm.includes("nicht verbunden")&&tm.includes("Kein MQTT-Broker gefunden"),"MQTT-Fehler wird verständlich angezeigt");
 mqttState="verbunden";
 // Selbsttest
 await go("selftest");let t=d.getElementById("p-selftest").textContent;
 ok(t.includes("1 Problem gefunden")&&t.includes("liefert kW statt W")&&t.includes("Einheit umrechnen")&&t.includes("Greift nicht")&&t.includes("300 W Einspeisung"),"Selbsttest zeigt Befunde, Hinweise und Abregelungs-Ergebnis");
 // Statistik
 await go("stats");t=d.getElementById("p-stats").textContent;
 ok(t.includes("61 %")&&t.includes("83 %")&&t.includes("Netzbezug")&&d.querySelectorAll("#p-stats svg rect").length===10&&t.includes("Aus Speichern"),"Statistik: Kennzahlen und Balkendiagramm (2 Tage x 5 Balken, mit Speicher-Reihe)");
 // Replay
 await go("replay");
 ok(d.querySelectorAll("#p-replay [data-rp]").length>=17,"Replay-Formular mit Einstellungen");
 const mg=d.querySelector('[data-rp="control.min_gap"]');mg.value="8";
 const eco=d.querySelector('[data-rp="features.eco"]');eco.value="0";
 d.getElementById("rp_curtail").checked=true;
 d.getElementById("rprun").click();await new Promise(r=>setTimeout(r,200));
 ok(replayBody&&replayBody.overrides["control.min_gap"]===8&&replayBody.overrides["features.eco"]===false&&replayBody.curtail===true&&replayBody.hours===24&&Object.keys(replayBody.overrides).length===2,"Replay sendet nur geänderte Einstellungen");
 t=d.getElementById("rpout").textContent;
 ok(t.includes("7.4")&&t.includes("6.9")&&t.includes("0.50 kWh niedriger")&&t.includes("Modell-Check")&&d.querySelectorAll("#rpout polyline").length===6,"Replay-Ergebnis mit Vergleich und zwei Diagrammen");
 // Einstellungen: Lernen (Regelung) und Meldungen/Preise (eigene Seite)
 await go("control");t=d.getElementById("p-control").textContent;
 ok(t.includes("gelernter Grundlast"),"Regelung enthält Grundlast-Lernen");
 ok(d.getElementById("learnbox").textContent.includes("210 W")&&d.getElementById("learnbox").textContent.includes("231 W"),"Gelernte Grundlast wird angezeigt");
 await go("extras");t=d.getElementById("p-extras").textContent;
 ok(t.includes("Benachrichtigungen")&&t.includes("Preise für die Statistik")&&t.includes("Testnachricht senden"),"Sicherheit, Meldungen und Preise auf eigener Seite");
 ok(t.includes("Not-Aus")&&d.getElementById("f_safety_kill_entity")&&d.getElementById("f_safety_release_on_stop")&&d.getElementById("f_safety_auto_meter_min")&&d.getElementById("f_notify_events_stopped"),"Sicherheitsfelder vorhanden");
 await new Promise(r=>setTimeout(r,200));
 ok(d.getElementById("f_safety_watchdog")!==null&&d.getElementById("wdbox").textContent.includes("manuell"),"Wächter: Einstellung und Zustand");
 ok(d.getElementById("wdjson")&&d.getElementById("wdjson").value.includes("solasi_waechter")&&d.getElementById("wdcopy")!==null,"Wächter: Text zum Einfügen bei fehlenden Rechten");
 ok(d.querySelector('a[href="waechter.yaml"]')===null,"Kein Blueprint-Download mehr nötig");
 // Export / Import der Einstellungen
 let blobMade=false;w.URL.createObjectURL=b=>{blobMade=b.type==="application/json";return "blob:x"};
 d.getElementById("cfgexport").click();
 ok(blobMade,"Export erzeugt eine JSON-Datei");
 const im=d.getElementById("cfgimport");
 const before=saved.length;
 Object.defineProperty(im,"files",{configurable:true,value:[{text:async()=>"kein json"}]});im.dispatchEvent(new w.Event("change"));await new Promise(r=>setTimeout(r,150));
 ok(saved.length===before,"Import ignoriert ungültige Dateien");
 Object.defineProperty(im,"files",{configurable:true,value:[{text:async()=>JSON.stringify({foo:1})}]});im.dispatchEvent(new w.Event("change"));await new Promise(r=>setTimeout(r,150));
 ok(saved.length===before,"Import lehnt fremde JSON-Dateien ab");
 const exported=JSON.parse(JSON.stringify(cfg));exported.control.step=25;
 Object.defineProperty(im,"files",{configurable:true,value:[{text:async()=>JSON.stringify(exported)}]});im.dispatchEvent(new w.Event("change"));await new Promise(r=>setTimeout(r,200));
 ok(saved.length===before+1&&saved.at(-1).control.step===25,"Import sendet die Einstellungen an SOLASI");
 ok(d.querySelectorAll("#dl-notify option").length===2,"Benachrichtigungsziele als Vorschläge");

 // --- Aufgeräumte Navigation ---
 w.showPage("status");
 const navItems=[...d.querySelectorAll("#nav button")].map(b=>b.textContent.trim());
 ok(["Übersicht","Speicher","Überschuss","Statistik","Was-wäre-wenn","Gesundheit","Protokoll","Dashboard-Karte","Entitäten (MQTT)","Einrichtung","Einstellungen"].every(x=>navItems.includes(x)),"Seitenleiste mit allen Bereichen");
 ok([...d.querySelectorAll("#nav .sec")].map(x=>x.textContent).join()==="Betrieb,Auswertung,System","Seitenleiste in drei Abschnitte gegliedert");
 ok(d.getElementById("subnav").children.length===0,"Übersicht hat keine Unternavigation");
 w.showPage("units");ok(d.getElementById("p-units").classList.contains("act")&&d.getElementById("savebar").style.display==="flex"&&d.querySelector("#nav button[aria-current=page]").textContent.includes("Speicher"),"Speicher: Seite aktiv, Speichern-Leiste sichtbar");
 w.showPage("control");ok(d.querySelectorAll("#subnav button").length===5&&d.querySelector("#nav button[aria-current=page]").textContent.includes("Einstellungen"),"Einstellungen: Regelung, Sicherheit & Meldungen, Darstellung");
 ok([...d.querySelectorAll("#subnav button")].some(b=>b.textContent==="Sicherheit & Meldungen"),"Unterseite heißt Sicherheit & Meldungen");
 d.querySelector('#subnav [data-p="extras"]').click();ok(d.getElementById("p-extras").classList.contains("act")&&d.getElementById("title").textContent==="Sicherheit & Meldungen","Unterseite wechselt, Titel folgt");
 w.showPage("surplus");ok(d.getElementById("pagetools").classList.contains("on")&&d.getElementById("savebar").style.display==="flex","Überschuss: Schalter und Speichern-Leiste sichtbar");
 w.showPage("stats");ok(d.getElementById("savebar").style.display==="none"&&!d.getElementById("pagetools").classList.contains("on"),"Statistik: keine Speichern-Leiste");
 ok(d.querySelectorAll("#tabbar button").length===5&&d.querySelector("#tabbar #moreBtn")!==null,"Leiste am Handy (oben): vier Punkte und Mehr");
 d.getElementById("moreBtn").click();ok(d.getElementById("side").classList.contains("open"),"Mehr öffnet das Menü von unten");
 d.querySelector('#nav button[data-p="log"]').click();ok(!d.getElementById("side").classList.contains("open")&&d.getElementById("p-log").classList.contains("act"),"Auswahl schließt das Menü");
 w.showPage("look");ok(d.getElementById("look_start")!==null,"Darstellung: Startseite wählbar");
 d.querySelector('#look_dens [data-d="large"]').click();ok(d.body.classList.contains("dens-large"),"Dichte Groß wirkt sofort");
 d.querySelector('#look_dens [data-d="normal"]').click();
 d.querySelector('#nav button[data-p="stats"]').click();ok(d.getElementById("p-stats").classList.contains("act"),"Menüpunkt öffnet die Seite");

 // --- Energiefluss in weiteren Lagen ---
 const draw=async(o)=>{Object.assign(status,o);await new Promise(r=>setTimeout(r,2300));return require("./flowhelp").lines(d.querySelector(".flow svg"));};
 w.showPage("status");
 let L=await draw({pv_w:0,bat_w:300,grid_w:100,house_w:400,flows:{solar_house:0,solar_battery:0,battery_house:300,grid_house:100}});
 ok(!L.sh&&!L.sb&&L.bh==="fwd"&&L.gh==="fwd","Nachts: Speicher -> Haus (vorwärts) und Netz -> Haus, keine Solar-Linien");
 L=await draw({pv_w:0,bat_w:-600,grid_w:700,house_w:100,flows:{solar_house:0,solar_battery:0,battery_house:-600,grid_house:700}});
 ok(L.bh==="rev"&&L.gh==="fwd","Netzladen: Netz -> Haus und Haus -> Speicher (rückwärts auf der Speicher-Linie)");
 L=await draw({pv_w:1500,bat_w:0,grid_w:-700,house_w:800,flows:{solar_house:1500,solar_battery:0,battery_house:0,grid_house:-700}});
 ok(L.sh==="fwd"&&!L.sb&&L.gh==="rev","Einspeisung: Solar -> Haus und Haus -> Netz (vorwärts)");
 L=await draw({flows:null,pv_w:null,bat_w:null,house_w:null,grid_w:0});
 ok(Object.values(L).every(v=>v===null),"Ohne Flusswerte: alle Linien ruhig, nichts erfunden");
 Object.assign(status,{pv_w:780,bat_w:-260,house_w:529,grid_w:9,flows:{solar_house:520,solar_battery:260,battery_house:0,grid_house:9}});
 // --- Zähler-Seite ---
 d.querySelector('#nav button[data-p="meters"]').click();
 ok(d.getElementById("p-meters").classList.contains("act")&&d.getElementById("savebar").style.display==="flex","Zähler-Seite mit Speichern-Leiste");
 ok(d.querySelector("#p-meters").textContent.includes("So sieht es aus")&&d.querySelector("#p-meters .sfm"),"Zähler-Seite zeigt eine Vorschau");
 d.getElementById("addmeter").click();
 let mc=w.eval("cfg.meters");
 ok(mc.items.length===1&&mc.items[0].icon==="zaehler"&&mc.items[0].daily===true,"Zähler hinzufügen");
 await new Promise(r=>setTimeout(r,20));
 const en=d.getElementById("f_meters_items_0_entity");en.value="sensor.gas";en.dispatchEvent(new w.Event("input"));
 const ic=d.getElementById("f_meters_items_0_icon");ic.value="gas";ic.dispatchEvent(new w.Event("change"));
 await new Promise(r=>setTimeout(r,20));
 mc=w.eval("cfg.meters");
 ok(mc.items[0].entity==="sensor.gas"&&mc.items[0].icon==="gas","Sensor und Symbol werden übernommen");
 d.getElementById("f_meters_extra").click();
 ok(w.eval("cfg.meters.extra")===true,"Option „Solar und Netz heute“ lässt sich einschalten");
 d.querySelector("[data-delmeter]").click();
 ok(w.eval("cfg.meters.items.length")===0,"Zähler entfernen");
 w.showPage("status");
 // --- Kill-Switch ---
 w.showPage("status");await new Promise(r=>setTimeout(r,2300));
 const kb=d.getElementById("killbtn");
 ok(kb&&kb.textContent.includes("Not-Aus")&&!kb.classList.contains("resume"),"Not-Aus-Knopf im Kopf");
 kb.click();await new Promise(r=>setTimeout(r,2600));
 ok(calls.includes("kill"),"Not-Aus ruft /api/kill auf");
 ok(d.getElementById("killbtn").textContent.includes("Fortsetzen")&&d.getElementById("killbtn").classList.contains("resume"),"Knopf wird zu Fortsetzen");
 ok(d.getElementById("modetext").textContent==="Gestoppt","Modus-Pille zeigt Gestoppt");
 t=d.getElementById("p-status").textContent;
 ok(t.includes("SOLASI ist gestoppt")&&t.includes("Von Hand gestoppt")&&t.includes("an ihren eigenen Modus zurückgegeben"),"Banner mit Grund und Hinweis");
 ok(d.querySelector(".headline").textContent==="SOLASI ist gestoppt","Überschrift im Gestoppt-Zustand");
 d.getElementById("killbtn").click();await new Promise(r=>setTimeout(r,2600));
 ok(calls.includes("resume")&&d.getElementById("killbtn").textContent.includes("Not-Aus"),"Fortsetzen ruft /api/resume auf");
 // Rückfall-Modus je Speicher
 cfg.units[0].mode="select.mode_a";w.renderUnits();
 w.showPage("units");await new Promise(r=>setTimeout(r,300));
 const utab=async t=>{d.querySelector(`[data-utab="${t}"]`).click();await new Promise(r=>setTimeout(r,60));};
 await utab("adv");
 ok(d.getElementById("f_units_0_fallback_mode")!==null,"Rückfall-Modus beim Anker-Speicher");
 await utab("lim");
 { const mn=d.getElementById("f_units_0_min_soc"),wl=d.getElementById("f_units_0_write_limits");
   ok(!!mn&&!!d.getElementById("f_units_0_max_soc")&&!!wl,"Speicher: eigener Mindest-/Höchst-Ladestand und Schalter „Grenzen schreiben“");
   mn.value="25";mn.dispatchEvent(new w.Event("input"));ok(cfg.units[0].min_soc===25,"Eigener Mindest-Ladestand wird gespeichert");
   mn.value="";mn.dispatchEvent(new w.Event("input"));ok(cfg.units[0].min_soc===null,"Leeres Feld bedeutet globaler Wert (null)");
   const sb=[...d.querySelectorAll("[data-ustate]")];
   ok(sb.map(b=>b.dataset.ustate).join()==="active,maint,off"&&sb[0].classList.contains("a"),"Speicher: Betrieb Aktiv, Wartung, Aus als Schalter im Kopf");
   d.querySelector('[data-ustate="maint"]').click();ok(cfg.units[0].state==="maint","Betrieb Wartung wird gespeichert");
   d.querySelector('[data-ustate="active"]').click();await new Promise(r=>setTimeout(r,60));
   wl.checked=true;wl.dispatchEvent(new w.Event("change"));ok(cfg.units[0].write_limits===true,"Schalter „Grenzen schreiben“ wird gespeichert"); }
 ok(d.querySelectorAll("#dl-fb0 option").length===2&&d.querySelector("#dl-fb0 option").value==="third_party_control","Vorschläge aus den Optionen des Betriebsmodus");
 // --- Speichertypen ---
 ex.checked=false;ex.dispatchEvent(new w.Event("change"));await new Promise(r=>setTimeout(r,100));
 w.showPage("units");await new Promise(r=>setTimeout(r,50));
 const sec=[...d.querySelectorAll("#p-units details.fsec")];
 ok(sec.length===1&&sec[0].open&&d.querySelectorAll("#p-units .udev").length>=2&&d.querySelector("#p-units .udev.sel"),"Zähler offen, Speicherliste mit gewähltem Speicher");
 // --- Energiefluss-Korrektur: Messart, Gerätesensoren, PV-Durchleitung ---
 ok(d.querySelector("#p-status").textContent.includes("Solar 540 W")&&d.querySelector("#p-status").textContent.includes("540 W"),"Speicher-Karte zeigt die Solarleistung des Speichers");
 cfg.units[0].num="number.dev_geraet_1_leistung";w.renderUnits();await new Promise(r=>setTimeout(r,300));
 await utab("pow");
 const pb=d.getElementById("f_units_0_power_basis");
 ok(pb&&[...pb.options].map(o=>o.value).join()===",ac,battery","Messart-Auswahl: Automatisch, AC, Batterie");
 ok(d.getElementById("f_units_0_pv")&&d.getElementById("f_units_0_pv").getAttribute("list")==="dl-sens0","PV-Feld nutzt die Geräte-Vorschläge");
 const box=d.getElementById("devsens0").textContent;
 ok(box.includes("2 Sensoren gefunden")&&box.includes("Solarleistung")&&box.includes("540")&&box.includes("Batterie Ladeleistung"),"Sensorliste des Geräts mit aktuellen Werten");
 const o0=d.querySelector("#dl-sens0 option");
 ok(o0&&o0.value==="sensor.dev_charge"&&o0.getAttribute("label").includes("140 W"),"Vorschlagsliste enthält Gerätesensoren zuerst, mit Wert");
 pb.value="battery";pb.dispatchEvent(new w.Event("change"));
 ok(cfg.units[0].power_basis==="battery","Messart wird übernommen");
 await go("control");
 ok(d.getElementById("f_features_pv_passthrough")!==null,"Schalter PV-Durchleitung vorhanden");
 ok(d.getElementById("f_features_enforce_mode")!==null&&d.getElementById("f_features_enforce_mode").checked===true,"Schalter „Externe Steuerung automatisch einschalten“ vorhanden und standardmäßig an");
 w.showPage("units");await new Promise(r=>setTimeout(r,50));
 await utab("conn");
 const drvSel=d.getElementById("f_units_0_driver");
 ok(drvSel&&[...drvSel.options].map(o=>o.value).join()==="anker,signed,modal,limit,script","Speichertyp-Auswahl mit fünf Treibern");
 ok(d.querySelector("#p-units .drvdesc").textContent.includes("Richtung"),"Beschreibung zum Speichertyp");
 ok(d.getElementById("f_units_0_dir")!==null&&d.getElementById("f_units_0_num_chg")===null,"Anker: Richtung ja, Ladezahl nein");
 drvSel.value="modal";drvSel.dispatchEvent(new w.Event("change"));await new Promise(r=>setTimeout(r,100));
 ok(d.getElementById("f_units_0_num_chg")!==null&&d.getElementById("f_units_0_enable")!==null&&d.getElementById("f_units_0_power")!==null,"Modus + Leistungen: Ladezahl, Fernsteuerung, Leistungssensor mit Vorzeichen");
 const drvSel2=d.getElementById("f_units_0_driver");drvSel2.value="limit";drvSel2.dispatchEvent(new w.Event("change"));await new Promise(r=>setTimeout(r,100));
 ok(d.getElementById("f_units_0_num")!==null,"Ausgangslimit: nur eine Zahl");
 await utab("pow");ok(d.getElementById("f_units_0_max_chg")===null,"Ausgangslimit: kein Laden");
 await utab("adv");ok(d.getElementById("f_units_0_fallback_value")!==null&&d.getElementById("f_units_0_fallback_mode")===null,"Ausgangslimit: Rückfall-Limit statt Rückfall-Modus");
 await utab("conn");
 ok(cfg.units[0].driver==="limit"&&cfg.units[0].can_charge===false&&cfg.units[0].curtail===false,"Typwechsel setzt passende Voreinstellungen");
 const drvSel3=d.getElementById("f_units_0_driver");drvSel3.value="script";drvSel3.dispatchEvent(new w.Event("change"));await new Promise(r=>setTimeout(r,100));
 ok(d.getElementById("f_units_0_script")!==null&&d.querySelector("#p-units .drvdesc").textContent.includes("power_w"),"Skript: Skriptfeld und Hinweis auf power_w");
 // --- Vorschlagslisten beim ersten Einrichten (Fehlerbild: ab "Beim Stoppen" kamen keine Entitäten) ---
 cfg.units[1].driver="anker";cfg.units[1].num="";cfg.units[1].dir="";cfg.units[1].mode="";cfg.units[1].script="";
 w.renderUnits();d.querySelector('[data-usel="1"]').click();await utab("conn");      // frisches, leeres Formular: noch keine Entität bekannt (kurz warten, bis alle Eingabefelder bereit sind)
 const nSens=ents.filter(e=>e.domain==="sensor").length;
 ok(d.querySelectorAll("#dl-sens1 option").length===nSens&&nSens>=3,"Leeres Formular: sofort alle Sensoren als Vorschlag ("+nSens+")");
 const socOk=d.getElementById("f_units_1_soc").getAttribute("list")==="dl-sens1";await utab("pow");
 ok(socOk&&d.getElementById("f_units_1_pv").getAttribute("list")==="dl-sens1","Ladestand und PV nutzen diese Liste");
 ok(d.getElementById("devsens1").textContent.includes("Erst Leistung"),"Hinweis, solange noch keine Leistung gewählt ist");
 await utab("conn");
 ok(d.querySelectorAll("#dl-fb1 option").length===0,"Rückfall-Vorschläge leer, solange kein Betriebsmodus gewählt ist");
 // Nutzer tippt die Leistungs-Entität ein -> Gerätesensoren erscheinen ohne Neuladen
 const numIn=d.getElementById("f_units_1_num");numIn.value="number.dev_geraet_2_leistung";numIn.dispatchEvent(new w.Event("input"));
 await new Promise(r=>setTimeout(r,900));
 ok(d.querySelector("#dl-sens1 option").value==="sensor.dev_charge"&&d.querySelectorAll("#dl-sens1 option").length===nSens+2,"Nach dem Eintippen: Gerätesensoren zuerst, übrige danach");
 await utab("pow");ok(d.getElementById("devsens1").textContent.includes("2 Sensoren gefunden"),"Sensorliste des Geräts erscheint ohne Neuladen");await utab("conn");
 // Nutzer wählt den Betriebsmodus -> Rückfall-Optionen erscheinen
 const modeIn=d.getElementById("f_units_1_mode");modeIn.value="select.mode_b";modeIn.dispatchEvent(new w.Event("input"));
 await new Promise(r=>setTimeout(r,900));
 ok(d.querySelectorAll("#dl-fb1 option").length===2&&d.querySelector("#dl-fb1 option").value==="third_party_control","Nach Wahl des Betriebsmodus: dessen Optionen als Vorschlag für „Beim Stoppen“");
 // Abfrage schlägt fehl -> trotzdem alle Sensoren wählbar
 failDevice=true;cfg.units[1].num="number.dev_geraet_2_leistung";w.renderUnits();await new Promise(r=>setTimeout(r,400));
 ok(d.querySelectorAll("#dl-sens1 option").length===nSens,"Abfrage schlägt fehl: weiterhin alle Sensoren als Vorschlag");
 await utab("pow");ok(d.getElementById("devsens1").textContent.includes("nicht verfügbar"),"Hinweis, dass die Geräteliste fehlt");
 failDevice=false;

 // ---- Anordnung Übersicht/Statistik, ruhiges Aktualisieren ----
 {const ps2=d.querySelector("#p-status");
  const idx=sel=>{const n=ps2.querySelector(sel);return n?[...ps2.querySelectorAll("[data-blk]")].indexOf(n.closest("[data-blk]")):-1};
  ok(idx(".kpis")<idx(".sfm")&&idx(".sfm")<idx(".flow")&&idx(".flow")<idx(".trendbox")&&idx(".trendbox")<idx(".urow")&&idx(".urow")<idx("#minilog"),"Übersicht: Standardreihenfolge");
  ok(ps2.querySelectorAll(".cols").length===1&&ps2.querySelectorAll(".cols > .stack").length===2,"Übersicht: zwei Spalten wie bisher");
  const left=[...ps2.querySelectorAll(".cols > .stack")[0].querySelectorAll("[data-blk]")].map(e=>e.dataset.blk).join();
  ok(left==="meters,hero,trend","Übersicht: Standard links Zähler, Fluss, Verlauf");
  const det=ps2.querySelector("details.udet");det.open=true;
  w.poll&&await w.poll();await new Promise(r=>setTimeout(r,100));
  ok(ps2.querySelector("details.udet").open===true,"Technische Details bleiben beim Aktualisieren offen");
  const node=ps2.querySelector(".flow");w.renderStatus(status);
  ok(ps2.querySelector(".flow")===node,"Unveränderter Block wird nicht neu aufgebaut");
  cfg.ui={status_order:["log","kpis"],status_hidden:["trend","surplus"],stats_order:["chart"],stats_hidden:["period"]};
  w.renderStatus(status);
  const ids=[...ps2.querySelectorAll("[data-blk]")].map(e=>e.dataset.blk).filter(x=>x!=="banners");
  ok(ids[0]==="log"||ids[0]==="kpis","Eigene Reihenfolge wird angewendet");
  ok(!ids.includes("trend")&&!ids.includes("surplus")&&ids.includes("hero"),"Ausgeblendete Blöcke fehlen, der Rest bleibt");
  ok(ids.indexOf("log")<ids.indexOf("meters"),"Log steht vor den übrigen Blöcken");
  cfg.ui={status_order:[],status_hidden:[],stats_order:[],stats_hidden:[]};w.renderStatus(status);
  w.showPage("look");await new Promise(r=>setTimeout(r,100));
  ok(d.querySelectorAll("#p-look .ordlist[data-k]").length===2&&d.querySelectorAll('#p-look .ordlist[data-k="status"] .ordrow').length===8,"Darstellung: Anordnungslisten für Übersicht und Statistik");
  { // Energiefluss konfigurieren
    const fsel=d.querySelector("#fl_layout");
    ok(!!fsel&&d.querySelectorAll("#p-look [data-fl]").length===6&&!!d.querySelector("#fl_gp"),"Energiefluss: Vorlage, fünf Kachel-Schalter plus Durchgereicht, Platz des Netzes");
    fsel.value="pairs";fsel.dispatchEvent(new w.Event("change"));
    ok(cfg.flow.layout==="pairs","Vorlage wird in die Einstellungen übernommen");
    d.querySelector('#p-look [data-fl="grid"]').click();
    ok(cfg.flow.grid===false&&cfg.flow.layout==="pairs","Kachel ausblenden speichert den Schalter");
    const n=(cfg.units||[]).length;
    if(n>1){const first=cfg.units[0].name;d.querySelector('#fl_ord [data-fm="1"]').click();ok(cfg.flow.order[1]===first,"Pfeil ändert die Reihenfolge der Anlagen");}
    const fz=d.querySelector("#fl_size");fz.value="large";fz.dispatchEvent(new w.Event("change"));
    ok(cfg.flow.size==="large","Größe des Energieflusses wird gespeichert");
    ok(!!d.querySelector("#cd_size")&&d.querySelectorAll("#p-look [data-cd]").length===8&&d.querySelectorAll("#cd_ord .ordrow").length===7,"Dashboard-Karte: Aussehen mit acht Schaltern und sieben Blöcken");
    d.querySelector('#p-look [data-cd="gradient"]').click();
    ok(cfg.card.gradient===false,"Farbverlauf der Karte abschaltbar");
    d.querySelector('#cd_ord [data-cm="1"]').click();
    ok(cfg.card.order[0]==="headline"&&cfg.card.order[1]==="meters","Reihenfolge der Kartenblöcke ändern");
    d.querySelector("#cd_reset").click();
    ok(cfg.card.gradient===true&&cfg.card.order.length===0,"Kartenaussehen zurücksetzen");
    d.querySelector("#fl_reset").click();
    ok(cfg.flow.layout==="total"&&cfg.flow.grid===true&&cfg.flow.order.length===0,"Standard wiederherstellen setzt den Energiefluss zurück");
  }
  d.querySelector('#p-look [data-k="status"] button[data-mv="1"][data-id="kpis"]').click();
  ok(cfg.ui.status_order[1]==="meters"&&cfg.ui.status_order[2]==="kpis","Pfeil nach unten ändert die Reihenfolge");
  d.querySelector('#p-look [data-k="status"] input[data-show="log"]').click();
  ok(cfg.ui.status_hidden.includes("log"),"Haken blendet Block aus");
  d.querySelector('#p-look [data-reset="status"]').click();
  ok(cfg.ui.status_order.length===0&&cfg.ui.status_hidden.length===0,"Standard wiederherstellen");
  cfg.ui.stats_order=["chart","tiles"];cfg.ui.stats_hidden=["period"];
  w.showPage("stats");await new Promise(r=>setTimeout(r,300));
  const sb=d.querySelector("#p-stats");
  ok(!sb.textContent.includes("Zeitraum:")&&sb.querySelector(".chart")&&sb.innerHTML.indexOf("chart")<sb.innerHTML.indexOf("Autarkie"),"Statistik: Diagramm zuerst, Zeitraum ausgeblendet");
  cfg.ui=undefined;}

 // ---- Reihenfolge der Zählerkacheln im Add-on ----
 {cfg.meters.items=[{entity:"sensor.wh",name:"Wasser",icon:"wasser",color:"water",daily:true},{entity:"sensor.st",name:"Strom",icon:"zaehler",color:"zaehl",daily:true}];cfg.meters.show_day=true;cfg.meters.extra=false;cfg.meters.order=[];
  w.showPage("meters");w.renderMeters();
  ok(d.querySelectorAll("#mord .ordrow").length===3,"Zähler: Reihenfolge-Liste mit Tagesverbrauch und beiden Zählern");
  d.querySelector('#mord button[data-k="day"][data-mv="1"]').click();
  ok(cfg.meters.order.join()==="m:sensor.wh,day,m:sensor.st","Pfeil verschiebt Tagesverbrauch nach unten");
  w.renderStatus(status);
  const nm=[...d.querySelectorAll("#p-status .sfm-n")].map(n=>n.textContent);
  ok(nm[0]==="Wasserzähler Haus"||nm.length>0,"Übersicht übernimmt die Reihenfolge");
  cfg.meters.order=[];}

 // ---- Statistik je Kachel ----
 {w.showPage("status");w.renderStatus(status);
  const tiles=[...d.querySelectorAll("#p-status [data-tile]")].map(t=>t.dataset.tile);
  ok(tiles.includes("day")&&tiles.includes("m:sensor.wh"),"Kacheln tragen ihren Schlüssel");
  d.querySelector('#p-status [data-tile="m:sensor.wh"]').click();
  await new Promise(r=>setTimeout(r,200));
  const pt=d.querySelector("#p-tile");
  ok(d.querySelector("#p-tile").classList.contains("act")&&pt.textContent.includes("Wasserzähler Haus"),"Klick auf Wasserkachel öffnet deren Statistik");
  ok(pt.textContent.includes("150 l")&&pt.textContent.includes("Höchster Tag")&&pt.textContent.includes("200 l"),"Wasser-Statistik in Litern, höchster Tag 200 l");
  ok(pt.querySelectorAll("svg.chart rect").length>=3,"Balkendiagramm gezeichnet");
  pt.querySelector('[data-tdays="7"]').click();await new Promise(r=>setTimeout(r,150));
  ok(d.querySelector("#p-tile").textContent.includes("Zeitraum"),"Zeitraum umschaltbar");
  pt.querySelector("#tile_back").click();
  ok(d.querySelector("#p-status").classList.contains("act"),"Zurück zur Übersicht");
  w.renderStatus(status);
  d.querySelector('#p-status [data-tile="day"]').click();await new Promise(r=>setTimeout(r,200));
  ok(d.querySelector("#p-tile").textContent.includes("Tagesverbrauch")&&d.querySelector("#p-tile").textContent.includes("kWh"),"Tagesverbrauch-Kachel zeigt Statistik in kWh");
  w.showPage("status");}
 {w.showPage("look");await new Promise(r=>setTimeout(r,80));
  const cb=d.getElementById("look_dbg");cb.checked=true;cb.dispatchEvent(new w.Event("change"));
  ok(w.eval("dbg.on")&&w.localStorage.getItem("solasi_debug")==="1","Sprung-Diagnose lässt sich einschalten");
  cb.checked=false;cb.dispatchEvent(new w.Event("change"));ok(!w.eval("dbg.on"),"Sprung-Diagnose lässt sich ausschalten");
  w.showPage("status");}
 // ---- 2.0: Modi, Einstellungs-Übersicht, Ziele, Änderungsleiste, Speicher hinzufügen ----
 {w.showPage("status");await new Promise(r=>setTimeout(r,300));w.renderStatus(status);
  const ps=d.getElementById("p-status");
  ok(ps.querySelectorAll(".mode[data-mode]").length===2&&ps.querySelector(".mode.add")&&ps.querySelector('[data-blk="modes"]'),"Übersicht: Modi als Schnellwahl samt „Eigener Modus“");
  ps.querySelector('[data-mode="autarky"]').click();await new Promise(r=>setTimeout(r,200));
  ok(calls.includes("mode:autarky")&&d.querySelector('#p-status .mode.on[data-mode="autarky"]'),"Tipp auf einen Modus aktiviert ihn und markiert ihn");
  w.prompt=()=>"Wochenende";d.querySelector("#p-status .mode.add").click();await new Promise(r=>setTimeout(r,200));
  ok(calls.includes("custom:Wochenende")&&d.querySelectorAll("#p-status .mode [data-modedel]").length===1,"Eigener Modus wird angelegt und lässt sich löschen");
  w.showPage("settings");
  ok(d.querySelectorAll("#p-settings .cat").length===9&&d.querySelector("#nav button[aria-current=page]").textContent.includes("Einstellungen"),"Einstellungen-Übersicht mit neun Themen");
  ok(d.querySelector("#modechip")&&d.getElementById("modechiptxt").textContent.length>1,"Kopfzeile zeigt den aktiven Modus");
  d.querySelector('#p-settings .cat[data-p="goals"]').click();await new Promise(r=>setTimeout(r,100));
  ok(d.querySelector("#p-goals .modeexplain, #p-goals .fx-tab, #p-goals table"),"„So arbeitet SOLASI“ ist auf der Ziele-Seite vorhanden");
  ok(d.getElementById("p-goals").classList.contains("act")&&d.querySelectorAll("#p-goals input[type=range]").length===3,"Ziele: drei Regler");
  const rs=d.getElementById("g_reserve");rs.value="80";rs.dispatchEvent(new w.Event("input"));await new Promise(r=>setTimeout(r,400));
  ok(cfg.soc.min===40&&cfg.goals&&cfg.goals.reserve===80&&cfg.goals.mode==="","Regler schreibt berechnete Werte in die Einstellungen");
  ok(d.getElementById("gv_reserve").textContent.includes("40 %"),"Regler zeigt die Wirkung als Klartext");
  const tr=d.querySelector('#g_table [data-gpath="soc.min"]');
  ok(tr&&d.querySelector("#g_table .tag.ok"),"Tabelle: berechnete Werte als „wie berechnet“");
  tr.value="33";tr.dispatchEvent(new w.Event("input"));
  ok(cfg.soc.min===33&&tr.closest("tr").querySelector(".tag").textContent==="angepasst","Von Hand geänderter Wert wird als „angepasst“ markiert");
  ok(/Änderung/.test(d.getElementById("savemsg").textContent)&&d.getElementById("savemsg").textContent.includes("Mindest-Ladestand")&&d.getElementById("discard").style.display==="","Änderungsleiste nennt die Änderungen und bietet „Verwerfen“");
  d.getElementById("discard").click();await new Promise(r=>setTimeout(r,60));
  ok(w.eval("cfg.soc.min")!==33&&d.getElementById("discard").style.display==="none","Verwerfen stellt den gespeicherten Stand wieder her");
  w.showPage("units");await new Promise(r=>setTimeout(r,60));
  const n0=w.eval("cfg.units.length");d.getElementById("addunit").click();await new Promise(r=>setTimeout(r,200));
  ok(w.eval("cfg.units.length")===n0+1&&w.eval("cfg.units[cfg.units.length-1].name")==="Speicher "+(n0+1)&&d.querySelectorAll("#p-units .udev").length>=n0+1,"Speicher hinzufügen legt einen weiteren Speicher an");
  w.eval("cfg.units.pop()");w.renderUnits();
  global.DISC=[{name:"Garage Akku",driver:"anker",num:"number.g_ls",dir:"select.g_lf",mode:"",soc:"sensor.g_soc",pv:"",lim_res:"number.g_np",lim_dis:"",lim_chg:"",configured:false},{name:"Schon da",num:"number.x",configured:true}];
  d.getElementById("addunit").click();await new Promise(r=>setTimeout(r,200));
  ok(d.querySelectorAll("#addwiz [data-pickunit]").length===1&&/Garage Akku/.test(d.getElementById("addwiz").textContent)&&w.eval("cfg.units.length")===n0,"Assistent: zeigt nur gefundene, noch nicht eingerichtete Speicher");
  d.querySelector("#addwiz [data-pickunit]").click();await new Promise(r=>setTimeout(r,200));
  ok(!d.getElementById("addwiz")&&w.eval("cfg.units[cfg.units.length-1].num")==="number.g_ls"&&w.eval("cfg.units[cfg.units.length-1].name")==="Garage Akku"&&w.eval("cfg.units[cfg.units.length-1].lim_res")==="number.g_np","Assistent: übernimmt Name und Entitäten in den neuen Speicher");
  w.eval("cfg.units.pop()");w.renderUnits();
  d.getElementById("addunit").click();await new Promise(r=>setTimeout(r,200));
  d.getElementById("addmanual").click();await new Promise(r=>setTimeout(r,200));
  ok(w.eval("cfg.units.length")===n0+1&&w.eval("cfg.units[cfg.units.length-1].num")===""&&!d.getElementById("addwiz"),"Assistent: „Von Hand“ legt einen leeren Speicher an");
  w.eval("cfg.units.pop()");w.renderUnits();global.DISC=[];
  // Stromfresser
  w.eval('cfg.hogs={devices:[{id:"k",name:"Kühlschrank",icon:"🧊",power:"sensor.k",phase:"L1"},{id:"t",name:"TV",icon:"📺",power:"sensor.t",phase:""}]}');
  w.showPage("hogs");await new Promise(r=>setTimeout(r,250));
  ok(d.querySelectorAll("#p-hogs .hogrow").length===3&&/nicht gemessen/.test(d.getElementById("p-hogs").textContent),"Stromfresser: Rangliste mit Rest „nicht gemessen“");
  ok(d.querySelector("#p-hogs svg path")&&d.querySelectorAll("#p-hogs svg path").length===1,"Stromfresser: Leistungskurve gezeichnet");
  d.querySelector("#hog_cmp").click();d.querySelector("#hog_cmp").dispatchEvent(new w.Event("change",{bubbles:true}));await new Promise(r=>setTimeout(r,200));
  ok(d.querySelectorAll("#p-hogs svg path").length===2,"Stromfresser: Vergleich mit gestern zeichnet zweite Kurve");
  const hq=[];const of=w.fetch;w.fetch=(u,o)=>{hq.push(String(u));return of(u,o);};
  const ts=d.getElementById("hog_tod");ts.value="night";ts.dispatchEvent(new w.Event("change",{bubbles:true}));await new Promise(r=>setTimeout(r,200));
  d.querySelector('#hog_wd button[data-v="5"]').click();await new Promise(r=>setTimeout(r,200));
  ok(hq.some(u=>/from=1320&to=360/.test(u))&&hq.some(u=>/wd=0%2C1%2C2%2C3%2C4%2C6/.test(u)),"Stromfresser: Filter Uhrzeit und Wochentage gehen an die Abfrage");
  w.fetch=of;
  const ha=d.getElementById("hog_add");ha.value="sensor.plug_tv_power";ha.dispatchEvent(new w.Event("change",{bubbles:true}));
  ok(w.eval("cfg.hogs.devices.length")===3&&w.eval("cfg.hogs.devices[2].power")==="sensor.plug_tv_power"&&d.getElementById("discard").style.display==="","Stromfresser: Sensor hinzufügen markiert Änderung");
  d.querySelector("[data-hdel='2']").click();
  ok(w.eval("cfg.hogs.devices.length")===2,"Stromfresser: Gerät entfernen");
  // Phasen
  w.eval('cfg.phases={enabled:false,invert:false,fuse_a:0,warn_pct:90,feed:"",sensors:{}}');
  w.showPage("phases");await new Promise(r=>setTimeout(r,200));
  ok(d.getElementById("p-phases").classList.contains("act")&&!d.querySelector("#p-phases #ph_cfg").offsetParent&&d.getElementById("ph_on"),"Phasen: aus, solange nicht eingeschaltet");
  const pon=d.getElementById("ph_on");pon.checked=true;pon.dispatchEvent(new w.Event("change",{bubbles:true}));
  d.getElementById("ph_guess").click();
  ok(w.eval("cfg.phases.enabled")===true&&w.eval("cfg.phases.sensors.L2.power")==="sensor.em_b_power"&&w.eval("cfg.phases.sensors.L3.power")==="sensor.em_c_power","Phasen: Vorschläge ordnen Sensoren L1–L3 zu");
  w.eval('lastStatus=Object.assign({},lastStatus,{phases:{enabled:true,phases:{L1:{w:1200,v:231,a:5.2},L2:{w:-300,v:230,a:null},L3:{w:3600,v:229,a:15.4}},loads:{L1:5.2,L2:1.3,L3:15.4},imbalance_w:3900,max_phase:"L3",fuse:{phase:"L3",a:15.4,pct:96,warn:true,loads:{L1:5.2,L2:1.3,L3:15.4}},fuse_a:16,warn_pct:90,feed_units:[{name:"HÜTTE",phase:"L2",manual:false,detected:"L2",confidence:87,steps:14,share:{L1:5,L2:90,L3:5}},{name:"DACH",phase:"",manual:false,detected:"",confidence:20,steps:4,share:{L1:30,L2:30,L3:40}}]}})');
  w.renderPhasesLive();
  const pt=d.getElementById("ph_live").textContent;
  ok(/1200/.test(pt)&&/HÜTTE/.test(pt)&&/87 % sicher/.test(pt)&&/3900 W/.test(pt)&&/96 %/.test(pt),"Phasen: Werte, Einspeise-Phase je Speicher mit Sicherheit, Schieflast und Sicherung");
  ok(/wird gelernt/.test(pt),"Phasen: noch nicht erkannter Speicher zeigt den Lernstand");
  const tk=[...d.querySelectorAll("#ph_live .phk")];
  ok(tk.length===3&&tk[0].classList.contains("ok")&&tk[1].classList.contains("ok")&&tk[2].classList.contains("bad"),"Phasen: Kacheln grün/gelb/rot nach Auslastung");
  ok(tk[2].querySelector(".phbar i").style.width==="96.25%"||/^96/.test(tk[2].querySelector(".phbar i").style.width),"Phasen: Balken schlägt nur so weit aus wie die Auslastung");
  const pf=d.querySelector('[data-phfeed="DACH"]');pf.value="L3";pf.dispatchEvent(new w.Event("change",{bubbles:true}));
  ok(w.eval("cfg.phases.feed.DACH")==="L3","Phasen: manuelle Phase je Speicher wird gesetzt");
  d.getElementById("ph_reset").click();await new Promise(r=>setTimeout(r,50));
  ok(calls.includes("phases:reset"),"Phasen: „Neu messen“ ruft die API");
  // Phasen-Leiste im Energiefluss der Übersicht
  w.showPage("status");await new Promise(r=>setTimeout(r,150));w.renderStatus(w.eval("lastStatus"));
  ok(!!d.querySelector('#p-status svg[aria-label="Phasen"]')&&d.querySelectorAll('#p-status svg[aria-label="Phasen"] text').length>=9,"Phasen-Leiste unter dem Energiefluss");
  w.eval("cfg.flow.phases=false");w.renderStatus(w.eval("lastStatus"));
  ok(!d.querySelector('#p-status svg[aria-label="Phasen"]'),"Phasen-Leiste lässt sich in der Darstellung abschalten");
  w.eval("cfg.flow.phases=true");
  // „So arbeitet SOLASI“ öffnet die Ziele
  w.renderStatus(w.eval("lastStatus"));
  const lk=d.querySelector('#p-status .modefx a[data-p="goals"]');lk.click();await new Promise(r=>setTimeout(r,150));
  ok(d.getElementById("p-goals").classList.contains("act")&&!!d.getElementById("g_explain"),"Link „So arbeitet SOLASI“ öffnet die Erklärung");
  // Haus-Ansicht wählbar
  w.showPage("look");await new Promise(r=>setTimeout(r,100));
  const fv=d.getElementById("fl_view");fv.value="house";fv.dispatchEvent(new w.Event("change",{bubbles:true}));
  ok(w.eval("cfg.flow.view")==="house","Darstellung: Ansicht „Haus“ wählbar");
  w.eval("cfg.flow.view='flow'");
  // Laden aus dem Netz
  w.showPage("charge");await new Promise(r=>setTimeout(r,500));
  ok(d.getElementById("p-charge").classList.contains("act")&&!!d.getElementById("chg_go")&&/3,1 Stunden/.test(d.getElementById("chg_est").textContent),"Laden: Seite mit Schätzung");
  const ct=d.getElementById("chg_target");ct.value="30";ct.dispatchEvent(new w.Event("change",{bubbles:true}));
  const cp=d.getElementById("chg_power");cp.value="600";cp.dispatchEvent(new w.Event("change",{bubbles:true}));
  d.getElementById("chg_go").click();await new Promise(r=>setTimeout(r,200));
  ok(calls.includes("charge:start:30:600:"),"Laden: Start sendet Ziel und Leistung");
  ok(d.getElementById("chg_form").style.display==="none"&&/Laden bis 30 %/.test(d.getElementById("chg_live").textContent)&&/800 W/.test(d.getElementById("chg_live").textContent),"Laden: Fortschritt statt Formular");
  ok(d.getElementById("chgchip").style.display!=="none"&&/30 %/.test(d.getElementById("chgchiptxt").textContent),"Laden: Anzeige in der Kopfzeile");
  d.getElementById("chg_stop").click();await new Promise(r=>setTimeout(r,200));
  ok(calls.includes("charge:stop")&&d.getElementById("chgchip").style.display==="none"&&d.getElementById("chg_form").style.display==="","Laden: Beenden stellt Formular und Kopfzeile zurück");
  const dord=d.getElementById("chg_dorder");dord.value="parallel";dord.dispatchEvent(new w.Event("change",{bubbles:true}));
  ok(w.eval("cfg.charge.order")==="parallel","Laden: Standard-Reihenfolge wird in die Einstellungen übernommen");
  // Update (lokal)
  { const nav=()=>[...d.querySelectorAll("#nav button")].some(b=>b.dataset.p==="update");
    w.eval('expert=false;renderNav()');
    ok(!nav(),"Update: Menüpunkt nur im Experten-Modus");
    const ex=d.getElementById("q_expert");ex.checked=true;ex.dispatchEvent(new w.Event("change",{bubbles:true}));
    ok(nav(),"Update: Menüpunkt erscheint im Experten-Modus");
    global.UPD_OV=false;w.showPage("update");await new Promise(r=>setTimeout(r,300));
    const t=d.getElementById("p-update").textContent;
    ok(d.getElementById("p-update").classList.contains("act")&&/Update lokal einspielen/.test(t)&&/2\.3\.2/.test(t)&&!!d.getElementById("upd_file"),"Update: Seite mit Versionen und Upload");
    ok(d.getElementById("upd_back_img").disabled&&d.getElementById("upd_back_prev").disabled,"Update: Zurücksetzen gesperrt, solange es keinen lokalen Stand gibt");
    global.UPD_OV=true;global.UPD_FAIL=true;w.showPage("status");w.showPage("update");await new Promise(r=>setTimeout(r,300));
    ok(!d.getElementById("upd_back_img").disabled&&!d.getElementById("upd_back_prev").disabled&&/zurückgenommen/.test(d.getElementById("p-update").textContent),"Update: lokaler Stand, Vorgänger und gescheiterter Versuch werden angezeigt");
    global.UPD_OV=false;global.UPD_FAIL=false;
    await w.updUpload({name:"foto.png"});
    ok(/keine Zip/.test(d.getElementById("upd_msg").textContent),"Update: Nicht-Zip wird abgelehnt");
    ex.checked=false;ex.dispatchEvent(new w.Event("change",{bubbles:true}));w.showPage("status");
  }
  // Entladesperre
  w.showPage("charge");await new Promise(r=>setTimeout(r,300));
  { const ti=d.querySelector("#chg_locks [data-lkt]");ti.value="07:30";w.renderChargeLive();
    ok(d.querySelector("#chg_locks [data-lkt]").value==="07:30","Sperre: eingetippte Uhrzeit bleibt bei der Aktualisierung erhalten"); ti.value=""; }
  ok(d.querySelectorAll("#chg_locks [data-lk]").length>=1&&/gibt normal ab/.test(d.getElementById("chg_locks").textContent),"Sperre: Speicher mit Sperren-Knopf");
  d.querySelector('#chg_locks [data-lk][data-on="1"]').click();await new Promise(r=>setTimeout(r,200));
  ok(calls.some(c=>/^lock:.*:true:$/.test(c))&&/gesperrt bis zur Freigabe/.test(d.getElementById("chg_locks").textContent)&&d.getElementById("lkchip").style.display!=="none","Sperre: gesetzt, in der Liste und in der Kopfzeile");
  d.querySelector('#chg_locks [data-lk][data-on="0"]').click();await new Promise(r=>setTimeout(r,200));
  ok(calls.some(c=>/^lock:.*:false:/.test(c))&&d.getElementById("lkchip").style.display==="none","Sperre: Freigeben entfernt Sperre und Anzeige");
  const hd=d.getElementById("chg_hold");hd.value="until";hd.dispatchEvent(new w.Event("change",{bubbles:true}));
  ok(d.getElementById("chg_holdat").style.display!=="none"&&w.eval("chgF.hold")==="until"&&w.eval("chgBody().hold.at")==="08:00","Laden: „Danach halten bis Uhrzeit“ zeigt das Zeitfeld");
  // Automatik
  w.showPage("auto");await new Promise(r=>setTimeout(r,120));
  ok(d.getElementById("p-auto").classList.contains("act")&&d.querySelectorAll("#p-auto .rule").length===0&&/Wochenbericht/.test(d.getElementById("p-auto").textContent),"Automatik: leere Liste und Wochenbericht");
  d.getElementById("addrule").click();
  w.eval('cfg.rules[0].then={kind:"charge",target:20,power_w:0,units:[]}');w.renderAuto();
  ok(!!d.querySelector('#p-auto [data-rf="then.target"]')&&!!d.querySelector('#p-auto [data-runit]'),"Automatik: Aktion „Akkus laden“ mit Ziel und Speichern");
  w.eval('cfg.rules[0].then={kind:"mode",mode:"care"}');w.renderAuto();
  ok(d.querySelectorAll("#p-auto .rule").length===1&&w.eval("cfg.rules.length")===1&&d.getElementById("discard").style.display==="","Automatik: Regel hinzufügen markiert Änderung");
  const rk=d.querySelector("#p-auto [data-rf='when.kind']");rk.value="soc_below";rk.dispatchEvent(new w.Event("change",{bubbles:true}));
  ok(w.eval("cfg.rules[0].when.kind")==="soc_below"&&!!d.querySelector("#p-auto [data-rf='when.value']"),"Automatik: Bedingung wechseln zeigt passende Felder");
  const rv=d.querySelector("#p-auto [data-rf='when.value']");rv.value="25";rv.dispatchEvent(new w.Event("change",{bubbles:true}));
  const rt=d.querySelector("#p-auto [data-rf='then.kind']");rt.value="notify";rt.dispatchEvent(new w.Event("change",{bubbles:true}));
  const tx=d.querySelector("#p-auto [data-rf='then.text']");tx.value="Akku fast leer";tx.dispatchEvent(new w.Event("change",{bubbles:true}));
  ok(w.eval("cfg.rules[0].when.value")===25&&w.eval("cfg.rules[0].then.text")==="Akku fast leer"&&w.eval("cfg.rules[0].then.kind")==="notify","Automatik: Werte und Aktion werden übernommen");
  d.getElementById("rep_weekly").checked=true;d.getElementById("rep_weekly").dispatchEvent(new w.Event("change",{bubbles:true}));
  ok(w.eval("cfg.reports.weekly")===true,"Automatik: Wochenbericht einschalten");
  d.querySelector("#p-auto [data-rdel]").click();
  ok(w.eval("cfg.rules.length")===0,"Automatik: Regel löschen");
  d.getElementById("discard").click();await new Promise(r=>setTimeout(r,60));
  // Konten
  global.ACCTS=[{name:"Stefan",role:"owner",role_label:"Besitzer"},{name:"Anna",role:"member",role_label:"Mitbewohner"}];
  w.showPage("accounts");await new Promise(r=>setTimeout(r,150));
  ok(d.querySelectorAll("#p-accounts [data-acct]").length===2&&d.querySelector("[data-arole='Anna']").value==="member"&&/8100/.test(d.getElementById("p-accounts").textContent),"Konten: Liste mit Rollen und Hinweis zum eigenen Port");
  d.getElementById("an_name").value="Opa";d.getElementById("an_pw").value="kurz";
  d.getElementById("an_add").click();await new Promise(r=>setTimeout(r,100));
  ok(d.getElementById("p-accounts")!==null&&d.querySelectorAll("#p-accounts [data-acct]").length===2,"Konten: ungültige Eingabe legt nichts an");
  global.ACCTS=[];
  // klassische Ansicht
  w.showPage("settings");d.getElementById("set_classic").checked=true;d.getElementById("set_classic").dispatchEvent(new w.Event("change"));await new Promise(r=>setTimeout(r,200));
  ok(d.querySelectorAll("#p-status .mode").length===0&&[...d.querySelectorAll("#nav button")].some(b=>b.textContent.trim()==="Einstellungen")&&d.getElementById("p-control").classList.contains("act")&&d.querySelectorAll("#subnav button").length===3,"Klassische Ansicht: alte Menüs, keine Modi");
  w.renderUnits();ok(d.querySelectorAll("#p-units details.fsec").length===3,"Klassische Ansicht: Speicher als einklappbare Gruppen");
  w.localStorage.setItem("solasi_classic","0");w.renderNav();w.showPage("status");
  ok(d.querySelectorAll("#nav button").length>=10,"Zurück zur neuen Ansicht");
  w.showPage("status");}
 process.exit(process.exitCode||0);
})();
