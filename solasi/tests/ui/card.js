const {JSDOM}=require("jsdom");const fs=require("fs");const path=require("path");const APP=path.join(__dirname,"..","..","app");
const src=fs.readFileSync(path.join(APP,"card","solasi-card.js"),"utf8");
const errors=[];
const dom=new JSDOM("<!DOCTYPE html><body></body>",{url:"http://ha.local/lovelace/0",runScripts:"outside-only",pretendToBeVisual:true});
const w=dom.window;w.addEventListener("error",e=>errors.push(e.message));
w.eval(src);
const ok=(c,m)=>{if(!c){console.log("FAIL:",m);
process.exitCode=1}else console.log("ok  :",m)};
const attrs={meters:[{name:"Wasserzähler Haus",value:552.62,dec:2,unit:"m³",icon:"wasser",color:"water",day:0.18},{name:"<b>x</b>",value:13141.74,dec:2,unit:"kWh",icon:"zaehler",color:"zaehl",day:null}],today:{house:8.4,pv:6.4,imp:1.2},meters_cfg:{show_day:true,extra:false},mode:"test",flows:{solar_house:520,solar_battery:260,battery_house:0,grid_house:9},pv_w:780,battery_w:-260,house_w:529,grid_w:9,target_w:390,surplus_w:1620,avg_soc:62,eco_active:true,meter_ok:true,blocked_w:1380,
 units:[{name:"Speicher A",pv:540,soc:80,set:280,force:false,available:true},{name:"<img src=x onerror=alert(1)>",soc:-1,set:0,force:true,available:false}],
 slots:[{name:"Wallbox",state:"on",own_w:1380}]};
const mk=(cfg,states)=>{const el=w.document.createElement("solasi-card");w.document.body.appendChild(el);el.setConfig(cfg);el.hass={states};return el;};
const st=(state,a)=>({"sensor.solasi":{state,attributes:a,last_updated:String(Math.random())}});
const q=(el,s)=>el.shadowRoot.querySelectorAll(s);
const txt=el=>el.shadowRoot.textContent;

ok(w.customElements.get("solasi-card")!==undefined,"Element solasi-card registriert");
ok(w.customCards.some(c=>c.type==="solasi-card"),"Karte erscheint im Karten-Auswahldialog (customCards)");
ok(w.customElements.get("solasi-card").getStubConfig().entity==="sensor.solasi","Standard-Entität sensor.solasi");

let el=mk({},st("Entladen",attrs));
ok(txt(el).includes("780 W")&&txt(el).includes("260 W")&&txt(el).includes("529 W")&&txt(el).includes("lädt")&&txt(el).includes("Bezug"),"Diagramm zeigt Solar 780, Speicher 260 (lädt), Haus 529, Netz Bezug");
const FH=require("./flowhelp"),fs1=()=>el.shadowRoot.querySelector('svg[aria-label="Energiefluss"]');
const ln=FH.lines(fs1());
ok(ln.sh==="fwd"&&ln.sb==="fwd"&&ln.bh===null&&ln.gh==="fwd","Linien: Solar->Haus und Solar->Speicher aktiv, Speicher<->Haus ruhig, Netz->Haus (Bezug)");
ok(FH.chips(fs1()).sort().join()==="260 W,520 W,9 W","Linien tragen ihre Werte (520, 260, 9 W)");
ok(q(el,".headline")[0].textContent.startsWith("Im Test: Solar versorgt dein Haus und lädt den Speicher"),"Überschrift im Testmodus");
ok(q(el,".pill.test").length===1&&txt(el).includes("Testmodus"),"Modus-Pille");
ok(txt(el).includes("Wallbox")&&txt(el).includes("1620 W")&&txt(el).includes("Eco-Modus")&&txt(el).includes("Entladung gesperrt für 1380 W"),"Überschuss, Eco-Tag, Sperre");
ok(q(el,".unit").length===2&&txt(el).includes("Abregelung")&&txt(el).includes("nicht verfügbar")&&txt(el).includes("Solar 540 W"),"Speicher-Kacheln inkl. Abregelung und Solarleistung");
ok(!el.shadowRoot.innerHTML.includes("<img")&&el.shadowRoot.innerHTML.includes("&lt;img"),"HTML in Namen wird maskiert (kein XSS)");

el=mk({title:"",show_batteries:false,show_surplus:false,show_tags:false,show_headline:false},st("Leerlauf",attrs));
ok(q(el,".head").length===0&&q(el,".unit").length===0&&q(el,".surplus").length===0&&q(el,".tags").length===0&&q(el,".headline").length===0&&q(el,'svg[aria-label="Energiefluss"]').length===1,"Optionen blenden Teile aus, Diagramm bleibt");

el=mk({entity:"sensor.gibtsnicht"},st("x",{}));
ok(txt(el).includes("sensor.gibtsnicht")&&txt(el).includes("nicht gefunden"),"Hinweis bei fehlender Entität");
el=mk({},st("unavailable",{}));
ok(txt(el).includes("nicht erreichbar"),"Hinweis bei unavailable");
el=mk({},st("Beobachten",{...attrs,mode:"observe"}));
ok(q(el,".headline")[0].textContent==="SOLASI beobachtet nur","Beobachten-Modus");
el=mk({},st("Gestoppt",{...attrs,mode:"stopped",stop_reason:"Von Hand gestoppt"}));
ok(q(el,".headline")[0].textContent==="SOLASI ist gestoppt"&&txt(el).includes("Von Hand gestoppt")&&q(el,".pill.stopped").length===1&&txt(el).includes("Gestoppt"),"Karte: Gestoppt-Zustand mit Grund");
el=mk({},st("Zähler-Ausfall",{...attrs,mode:"live",meter_ok:false}));
ok(q(el,".headline")[0].textContent==="Zähler ohne Meldung"&&q(el,".tag.bad").length===1,"Zähler-Ausfall");
el=mk({},st("Leerlauf",{mode:"live",grid_w:0,target_w:0,units:[],slots:[]}));
ok(txt(el).includes("Alles ausgeglichen")&&FH.lines(fs1()).sh===null&&txt(el).includes("ausgeglichen"),"Leerlauf: keine Animation, fehlende PV/Haus = –");
// ---- Größen, Verlauf, Not-Aus, Antippen, Editor ----
el=mk({size:"compact"},st("Entladen",attrs));
ok(q(el,".tile").length===4&&q(el,"svg").length===0&&txt(el).includes("780 W"),"Kompakt: vier Kacheln, kein Diagramm");
const withTrend={...attrs,trend:{pv:[0,100,400,900,700,200],house:[300,320,310,500,450,400]}};
el=mk({},st("Entladen",withTrend));
ok(q(el,".trend svg").length===1&&txt(el).includes("Verlauf"),"Tagesverlauf wird gezeichnet");
el=mk({show_trend:false},st("Entladen",withTrend));
ok(q(el,".trend").length===0,"Tagesverlauf abschaltbar");
const calls=[];
const hassFull=(extra)=>({states:{"sensor.solasi":{state:"Entladen",attributes:{...attrs,kill_switch:"switch.solasi_not_aus",addon_slug:"abc_solasi"},last_updated:new Date().toISOString()},"switch.solasi_not_aus":{state:"off"},...(extra||{})},callService:(d,s,x)=>calls.push([d,s,x.entity_id])});
el=w.document.createElement("solasi-card");w.document.body.appendChild(el);el.setConfig({});el.hass=hassFull();
ok(q(el,"button.kill").length===1&&q(el,"button.kill")[0].textContent==="Not-Aus","Not-Aus-Knopf erscheint, wenn der Schalter existiert");
q(el,"button.kill")[0].click();
ok(calls.length===0&&q(el,"button.kill")[0].textContent==="Wirklich stoppen?","Erster Tipp fragt nach, sendet nichts");
q(el,"button.kill")[0].click();
ok(calls.length===1&&calls[0].join()==="switch,turn_on,switch.solasi_not_aus","Zweiter Tipp löst den Not-Aus aus");
el.hass=hassFull({"switch.solasi_not_aus":{state:"on"}});
ok(q(el,"button.kill")[0].textContent==="Fortsetzen","Im Zustand Gestoppt heißt der Knopf Fortsetzen");
q(el,"button.kill")[0].click();
ok(calls.at(-1).join()==="switch,turn_off,switch.solasi_not_aus","Fortsetzen schaltet den Not-Aus aus");
el=w.document.createElement("solasi-card");w.document.body.appendChild(el);el.setConfig({show_kill:false});el.hass=hassFull();
ok(q(el,"button.kill").length===0,"Not-Aus-Knopf abschaltbar");
el=mk({},{"sensor.solasi":{state:"Entladen",attributes:attrs,last_updated:"x"}});
ok(q(el,"button.kill").length===0,"Ohne Schalter (kein MQTT) kein Knopf");
el=w.document.createElement("solasi-card");w.document.body.appendChild(el);el.setConfig({});el.hass=hassFull();
q(el,"ha-card")[0].click();
ok(w.location.pathname==="/hassio/ingress/abc_solasi"||w.location.href.includes("abc_solasi"),"Antippen öffnet die SOLASI-Oberfläche");
ok(w.customElements.get("solasi-card").getConfigElement().tagName.toLowerCase()==="solasi-card-editor","Visueller Editor vorhanden");
const ed=w.customElements.get("solasi-card").getConfigElement();w.document.body.appendChild(ed);ed.setConfig({title:"Mein Solar"});
ok(ed.querySelector("ha-form")&&ed.querySelector("ha-form").schema.length>=10&&ed.querySelector("ha-form").data.title==="Mein Solar","Editor zeigt die Optionen mit den aktuellen Werten");
let got=null;ed.addEventListener("config-changed",e=>got=e.detail.config);
ed.querySelector("ha-form").dispatchEvent(new w.CustomEvent("value-changed",{detail:{value:{size:"compact"}}}));
ok(got&&got.size==="compact"&&got.title==="Mein Solar","Editor meldet Änderungen zurück");
// ---- Zählerreihe ----
el=mk({},st("Entladen",attrs));
ok(q(el,".sfm").length===1&&txt(el).includes("Tagesverbrauch")&&txt(el).includes("8,4")&&txt(el).includes("552,62")&&txt(el).includes("13.141,74")&&txt(el).includes("+180 l")&&!txt(el).includes("0,18 m³"),"Zählerreihe: Tagesverbrauch, Zähler, Tageswert");
ok(q(el,".mwrap").length===1&&q(el,".mwrap")[0].nextElementSibling&&q(el,".mwrap")[0].nextElementSibling.classList.contains("headline"),"Reihe steht ganz oben, vor der Überschrift");
ok(q(el,".sfm b").length===1&&q(el,".sfm")[0].innerHTML.includes("&lt;b&gt;x"),"Zählernamen werden maskiert");
el=mk({show_meters:false},st("Entladen",attrs));
ok(q(el,".sfm").length===0&&q(el,".mwrap").length===0,"Zählerreihe abschaltbar");
el=mk({meters_layout:"even"},st("Entladen",attrs));
ok(q(el,".sfm.even").length===1&&q(el,".sfm.big").length===0,"Anordnung: alle gleich groß");
el=mk({},st("Entladen",{...attrs,meters_cfg:{show_day:false,extra:true}}));
ok(!txt(el).includes("Tagesverbrauch")&&txt(el).includes("Solarertrag heute")&&txt(el).includes("Netzbezug heute"),"Ohne Tageskachel, mit Solar und Netz heute");
el=mk({},st("Entladen",{...attrs,meters:undefined,today:undefined}));
ok(q(el,".sfm").length===0,"Ältere Version ohne Zählerdaten: keine Reihe");
el=mk({size:"compact"},st("Entladen",attrs));
ok(q(el,".sfm").length===0,"Kompakt zeigt keine Zählerreihe");
// ---- Reihenfolge, Liter, ruhiges Zeichnen ----
const pos=(el,sel)=>{const n=el.shadowRoot.querySelector(sel);return n?[...el.shadowRoot.querySelectorAll("ha-card *")].indexOf(n):-1};
el=mk({},st("Entladen",attrs));
ok(pos(el,".mwrap")<pos(el,".headline")&&pos(el,".headline")<pos(el,"svg[aria-label=Energiefluss]")&&pos(el,"svg[aria-label=Energiefluss]")<pos(el,".units")&&pos(el,".units")<pos(el,".tags"),"Standardreihenfolge unverändert");
el=mk({order:["tags","batteries","headline"]},st("Entladen",attrs));
ok(pos(el,".tags")<pos(el,".units")&&pos(el,".units")<pos(el,".headline")&&pos(el,".headline")<pos(el,".mwrap")&&pos(el,".mwrap")<pos(el,"svg[aria-label=Energiefluss]"),"order: genannte Blöcke zuerst, Rest in Standardreihenfolge");
el=mk({order:["tags","tags","quatsch"],show_tags:false},st("Entladen",attrs));
ok(q(el,".tags").length===0&&q(el,".headline").length===1,"order: Doppelte und Unbekannte werden ignoriert, show_* gilt weiter");
ok(txt(mk({},st("Entladen",attrs))).includes("+180 l"),"Wasserzähler: Tagesverbrauch in Litern");
{const a2=JSON.parse(JSON.stringify(attrs));a2.meters=[{name:"Gaszähler",value:100,dec:1,unit:"m³",icon:"gas",color:"gas",day:0.5},{name:"Kaltwasser",value:5,dec:3,unit:"m³",icon:"zaehler",color:"zaehl",day:1.2345},{name:"Wasser",value:5,dec:1,unit:"l",icon:"wasser",color:"water",day:3}];
 const t=txt(mk({},st("Entladen",a2)));
 ok(t.includes("+0,5 m³")&&t.includes("+1.235 l")&&t.includes("+3 l")&&t.includes("5,000 m³".replace(",",","))||t.includes("5,000"),"Gas bleibt m³; Wasser nach Name erkannt (1.235 l); Zählerstand bleibt m³");}
{const e2=w.customElements.get("solasi-card").getConfigElement();w.document.body.appendChild(e2);e2.setConfig({});
 let got2=null;e2.addEventListener("config-changed",e=>got2=e.detail.config);
 e2.querySelector('button[data-mv="1"][data-id="meters"]').click();
 ok(got2&&got2.order[0]==="headline"&&got2.order[1]==="meters","Editor: Block nach unten verschieben");
 e2.querySelector('button[data-mv="-1"][data-id="tags"]').click();
 ok(got2.order.indexOf("tags")===got2.order.indexOf("surplus")-1,"Editor: Block nach oben verschieben");}
{const e3=mk({},st("Entladen",attrs));const h1=e3.shadowRoot.querySelector("ha-card");
 e3.hass={states:st("Entladen",attrs)};   // gleicher Inhalt, nur neue last_updated
 ok(e3.shadowRoot.querySelector("ha-card")===h1,"Gleicher Inhalt: kein Neuaufbau der Karte");}
// ---- Reihenfolge der Zählerkacheln ----
{const a3=JSON.parse(JSON.stringify(attrs));a3.meters=[{entity:"sensor.w1",name:"Wasser Haus",value:5,dec:1,unit:"m³",icon:"wasser",color:"water",day:0.1},{entity:"sensor.w2",name:"Wasser Garten",value:7,dec:1,unit:"m³",icon:"wasser",color:"water",day:0.2}];
 a3.meters_cfg={show_day:true,extra:true};
 const names=el=>[...el.shadowRoot.querySelectorAll(".sfm-n")].map(n=>n.textContent);
 ok(names(mk({},st("Entladen",a3))).join()==="Tagesverbrauch,Wasser Haus,Wasser Garten,Solarertrag heute,Netzbezug heute","Kacheln: Standardreihenfolge");
 ok(names(mk({meters_order:["m:sensor.w2","day"]},st("Entladen",a3))).join()==="Wasser Garten,Tagesverbrauch,Wasser Haus,Solarertrag heute,Netzbezug heute","meters_order setzt die Reihenfolge");
 const e4=mk({meters_order:["m:sensor.w2","day"]},st("Entladen",a3));
 ok(q(e4,".sfm.even").length===1&&q(e4,".sfm.big").length===0,"Ohne Tagesverbrauch an erster Stelle: gleich große Kacheln");
 a3.meters_cfg.order=["pv","m:sensor.w1"];
 ok(names(mk({},st("Entladen",a3)))[0]==="Solarertrag heute","Ohne meters_order gilt die Reihenfolge aus dem Add-on");
 ok(names(mk({meters_order:["imp"]},st("Entladen",a3)))[0]==="Netzbezug heute","meters_order hat Vorrang vor dem Add-on");
 const e5=w.customElements.get("solasi-card").getConfigElement();w.document.body.appendChild(e5);e5.hass={states:st("Entladen",a3)};e5.setConfig({});
 let g5=null;e5.addEventListener("config-changed",e=>g5=e.detail.config);
 e5.querySelector('button[data-tk="pv"][data-mv="1"]').click();
 ok(g5&&g5.meters_order&&g5.meters_order.join()==="m:sensor.w1,pv,day,m:sensor.w2,imp","Editor: Zählerkachel verschieben");}
ok(errors.length===0,"keine JS-Fehler "+errors.join("|"));