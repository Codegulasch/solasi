const {JSDOM}=require("jsdom");const fs=require("fs");const path=require("path");const APP=path.join(__dirname,"..","..","app");
const html=fs.readFileSync(path.join(APP,"static","index.html"),"utf8");
const cfg=JSON.parse(require("child_process").execSync(`python3 -c "import json,controller;print(json.dumps(controller.DEFAULT_CONFIG))"`,{cwd:APP,env:{...process.env,SOLASI_DATA:require("os").tmpdir()}}).toString());
cfg.grid.entity="sensor.grid";const saved=[];let replayBody=null;const calls=[];let failDevice=false;
const status={safety:{state:"active",reason:"",since:null},pv_w:3000,bat_w:-1100,house_w:1380,connected:true,enabled:true,dry_run:true,surplus_enabled:true,surplus_dry_run:true,meter_ok:true,grid_w:400,net_balance:400,net_dis:400,t_target:390,eco_active:false,avg_soc:60,blocked_w:0,want:"Entladen",surplus_w:1620,
 units:[{name:"Speicher A",pv:540,soc:80,set:0,real:0,plan:280,force:false,available:false,mode:"self_consumption",dir:"discharge"},{name:"Speicher B",soc:40,set:0,real:0,plan:110,force:true,available:true,mode:"third_party_control",dir:"discharge"}],
 slots:[{name:"Wallbox",ent:"switch.wb",num:"number.wb",state:"on",own_w:1380,num_v:6}],
 events:[{ts:"12:00:01",level:"test",msg:"Test: Speicher A: 0 W → 280 W"},{ts:"12:00:00",level:"error",msg:"<b>x</b>"}]};
const ents=[{id:"sensor.grid",name:"Netz",domain:"sensor"},{id:"sensor.extra_a",name:"Irgendein Sensor A",domain:"sensor"},{id:"sensor.extra_b",name:"Irgendein Sensor B",domain:"sensor"},{id:"number.a",name:"A",domain:"number"},{id:"switch.wb",name:"WB",domain:"switch"},{id:"select.m",name:"M",domain:"select"}];
const errors=[];
const dom=new JSDOM(html,{runScripts:"dangerously",pretendToBeVisual:true,url:"http://localhost/",
 beforeParse(w){
  w.fetch=async(u,o)=>{
    const post=o&&o.method==="POST";
    const routes={
      "api/config":()=>post?(saved.push(JSON.parse(o.body)),{ok:true}):cfg,
      "api/status":()=>status,
      "api/card":()=>({installed:true,target:"/homeassistant/www/solasi/solasi-card.js",resource:"registriert",url:"/local/solasi/solasi-card.js?v=1.3.0",restart_needed:false,yaml:"x"}),
      "api/selfcheck":()=>({summary:{ok:5,warn:1,error:1,info:1},curtail:{state:"fehlgeschlagen",note:"Speicher voll, trotzdem 300 W Einspeisung.",since:"04.10. 12:00",export_w:300},
        items:[{area:"Zähler",item:"Netzleistung",status:"warn",text:"sensor.g liefert kW statt W",hint:"Einheit umrechnen"},{area:"Speicher A",item:"Modus-Option",status:"error",text:"nicht vorhanden",hint:""},{area:"Verbindung",item:"Home Assistant",status:"ok",text:"verbunden",hint:""}]}),
      "api/stats":()=>({days:[{date:"2026-10-03",pv:10,house:12,imp:4,exp:2,bat_dis:3,bat_chg:4,autarky:.66,selfcons:.8},{date:"2026-10-04",pv:8,house:11,imp:5,exp:1,bat_dis:2,bat_chg:3,autarky:.55,selfcons:.9}],
        total:{pv:18,house:23,imp:9,exp:3,bat_dis:5,bat_chg:7,autarky:.61,selfcons:.83,saved_eur:4.9,battery_eur:1.75,feedin_eur:.24}}),
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
  w.confirm=()=>true;
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
 ok(d.querySelector(".headline").textContent.includes("Im Test: Die Speicher versorgen dein Haus mit 390 W"),"Überschrift in Klartext");
 const fl=d.querySelector(".flow svg").textContent;
 ok(fl.includes("3000 W")&&fl.includes("1100 W")&&fl.includes("1380 W")&&fl.includes("lädt"),"Energiefluss zeigt PV, Speicher (lädt), Haus");
 ok(d.querySelectorAll(".flow .line.active").length===3,"drei aktive Flusslinien");
 ok(d.querySelectorAll(".flow .line.active.rev").length===2,"Speicher-Linie (lädt) und Netz-Linie (Bezug) laufen Richtung Haus bzw. Speicher");
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
 // Selbsttest
 await go("selftest");let t=d.getElementById("p-selftest").textContent;
 ok(t.includes("1 Problem gefunden")&&t.includes("liefert kW statt W")&&t.includes("Einheit umrechnen")&&t.includes("Greift nicht")&&t.includes("300 W Einspeisung"),"Selbsttest zeigt Befunde, Hinweise und Abregelungs-Ergebnis");
 // Statistik
 await go("stats");t=d.getElementById("p-stats").textContent;
 ok(t.includes("61 %")&&t.includes("83 %")&&t.includes("Netzbezug")&&d.querySelectorAll("#p-stats svg rect").length===8,"Statistik: Kennzahlen und Balkendiagramm (2 Tage x 4 Balken)");
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
 ok(d.querySelectorAll("#nav button").length===4,"vier Hauptbereiche statt neun Reiter");
 ok(d.getElementById("subnav").children.length===0,"Übersicht hat keine Unternavigation");
 w.showPage("units");ok(d.querySelectorAll("#subnav button").length===4&&d.querySelector("#nav button.act").dataset.g==="settings","Einstellungen: vier Unterseiten");
 ok([...d.querySelectorAll("#subnav button")].some(b=>b.textContent==="Sicherheit & Meldungen"),"Unterseite heißt Sicherheit & Meldungen");
 d.querySelector('#subnav [data-p="surplus"]').click();ok(d.getElementById("p-surplus").classList.contains("act")&&d.getElementById("savebar").style.display==="flex","Unterseite wechselt, Speichern-Leiste sichtbar");
 w.showPage("stats");ok(d.querySelectorAll("#subnav button").length===2&&d.getElementById("savebar").style.display==="none","Auswertung: Statistik und Replay");
 w.showPage("log");ok(d.querySelectorAll("#subnav button").length===3&&d.querySelector("#nav button.act").dataset.g==="system","System: Selbsttest, Protokoll, Dashboard-Karte");
 d.querySelector('#nav [data-g="eval"]').click();ok(d.getElementById("p-stats").classList.contains("act"),"Hauptbereich öffnet die erste Unterseite");

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
 ok(d.getElementById("f_units_0_fallback_mode")!==null,"Rückfall-Modus beim Anker-Speicher");
 ok(d.querySelectorAll("#dl-fb0 option").length===2&&d.querySelector("#dl-fb0 option").value==="third_party_control","Vorschläge aus den Optionen des Betriebsmodus");
 // --- Speichertypen ---
 ex.checked=false;ex.dispatchEvent(new w.Event("change"));await new Promise(r=>setTimeout(r,100));
 w.showPage("units");await new Promise(r=>setTimeout(r,50));
 const sec=[...d.querySelectorAll("#p-units details.fsec")];
 ok(sec.length===3&&sec[0].open&&sec[1].open===true,"Zähler und Speicher A sind offen");
 // --- Energiefluss-Korrektur: Messart, Gerätesensoren, PV-Durchleitung ---
 ok(d.querySelector("#p-status").textContent.includes("Solar dieses Speichers")&&d.querySelector("#p-status").textContent.includes("540 W"),"Speicher-Karte zeigt die Solarleistung des Speichers");
 cfg.units[0].num="number.dev_geraet_1_leistung";w.renderUnits();await new Promise(r=>setTimeout(r,300));
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
 w.showPage("units");await new Promise(r=>setTimeout(r,50));
 const drvSel=d.getElementById("f_units_0_driver");
 ok(drvSel&&[...drvSel.options].map(o=>o.value).join()==="anker,signed,modal,limit,script","Speichertyp-Auswahl mit fünf Treibern");
 ok(d.querySelector("#p-units .drvdesc").textContent.includes("Richtung"),"Beschreibung zum Speichertyp");
 ok(d.getElementById("f_units_0_dir")!==null&&d.getElementById("f_units_0_num_chg")===null,"Anker: Richtung ja, Ladezahl nein");
 drvSel.value="modal";drvSel.dispatchEvent(new w.Event("change"));await new Promise(r=>setTimeout(r,100));
 ok(d.getElementById("f_units_0_num_chg")!==null&&d.getElementById("f_units_0_enable")!==null&&d.getElementById("f_units_0_power")!==null,"Modus + Leistungen: Ladezahl, Fernsteuerung, Leistungssensor mit Vorzeichen");
 const drvSel2=d.getElementById("f_units_0_driver");drvSel2.value="limit";drvSel2.dispatchEvent(new w.Event("change"));await new Promise(r=>setTimeout(r,100));
 ok(d.getElementById("f_units_0_max_chg")===null&&d.getElementById("f_units_0_num")!==null,"Ausgangslimit: kein Laden, nur eine Zahl");
 ok(d.getElementById("f_units_0_fallback_value")!==null&&d.getElementById("f_units_0_fallback_mode")===null,"Ausgangslimit: Rückfall-Limit statt Rückfall-Modus");
 ok(cfg.units[0].driver==="limit"&&cfg.units[0].can_charge===false&&cfg.units[0].curtail===false,"Typwechsel setzt passende Voreinstellungen");
 const drvSel3=d.getElementById("f_units_0_driver");drvSel3.value="script";drvSel3.dispatchEvent(new w.Event("change"));await new Promise(r=>setTimeout(r,100));
 ok(d.getElementById("f_units_0_script")!==null&&d.querySelector("#p-units .drvdesc").textContent.includes("power_w"),"Skript: Skriptfeld und Hinweis auf power_w");
 // --- Vorschlagslisten beim ersten Einrichten (Fehlerbild: ab "Beim Stoppen" kamen keine Entitäten) ---
 cfg.units[1].driver="anker";cfg.units[1].num="";cfg.units[1].dir="";cfg.units[1].mode="";cfg.units[1].script="";
 w.renderUnits();await new Promise(r=>setTimeout(r,60));      // frisches, leeres Formular: noch keine Entität bekannt (kurz warten, bis alle Eingabefelder bereit sind)
 const nSens=ents.filter(e=>e.domain==="sensor").length;
 ok(d.querySelectorAll("#dl-sens1 option").length===nSens&&nSens>=3,"Leeres Formular: sofort alle Sensoren als Vorschlag ("+nSens+")");
 ok(d.getElementById("f_units_1_soc").getAttribute("list")==="dl-sens1"&&d.getElementById("f_units_1_pv").getAttribute("list")==="dl-sens1","Ladestand und PV nutzen diese Liste");
 ok(d.getElementById("devsens1").textContent.includes("Erst Leistung"),"Hinweis, solange noch keine Leistung gewählt ist");
 ok(d.querySelectorAll("#dl-fb1 option").length===0,"Rückfall-Vorschläge leer, solange kein Betriebsmodus gewählt ist");
 // Nutzer tippt die Leistungs-Entität ein -> Gerätesensoren erscheinen ohne Neuladen
 const numIn=d.getElementById("f_units_1_num");numIn.value="number.dev_geraet_2_leistung";numIn.dispatchEvent(new w.Event("input"));
 await new Promise(r=>setTimeout(r,900));
 ok(d.querySelector("#dl-sens1 option").value==="sensor.dev_charge"&&d.querySelectorAll("#dl-sens1 option").length===nSens+2,"Nach dem Eintippen: Gerätesensoren zuerst, übrige danach");
 ok(d.getElementById("devsens1").textContent.includes("2 Sensoren gefunden"),"Sensorliste des Geräts erscheint ohne Neuladen");
 // Nutzer wählt den Betriebsmodus -> Rückfall-Optionen erscheinen
 const modeIn=d.getElementById("f_units_1_mode");modeIn.value="select.mode_b";modeIn.dispatchEvent(new w.Event("input"));
 await new Promise(r=>setTimeout(r,900));
 ok(d.querySelectorAll("#dl-fb1 option").length===2&&d.querySelector("#dl-fb1 option").value==="third_party_control","Nach Wahl des Betriebsmodus: dessen Optionen als Vorschlag für „Beim Stoppen“");
 // Abfrage schlägt fehl -> trotzdem alle Sensoren wählbar
 failDevice=true;cfg.units[1].num="number.dev_geraet_2_leistung";w.renderUnits();await new Promise(r=>setTimeout(r,400));
 ok(d.querySelectorAll("#dl-sens1 option").length===nSens,"Abfrage schlägt fehl: weiterhin alle Sensoren als Vorschlag");
 ok(d.getElementById("devsens1").textContent.includes("nicht verfügbar"),"Hinweis, dass die Geräteliste fehlt");
 failDevice=false;
 process.exit(process.exitCode||0);
})();
