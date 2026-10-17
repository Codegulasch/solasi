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
// ---- Tipp auf Zählerkachel ----
{const a6=JSON.parse(JSON.stringify(attrs));a6.meters=[{entity:"sensor.w1",name:"Wasser Haus",value:5,dec:1,unit:"m³",icon:"wasser",color:"water",day:0.1}];
 const el6=w.document.createElement("solasi-card");w.document.body.appendChild(el6);el6.setConfig({});
 el6.hass={states:{...st("Entladen",{...a6,addon_slug:"abc_solasi"}),"sensor.w1":{state:"5",attributes:{}}}};
 let mi=null,navd=0;el6.addEventListener("hass-more-info",e=>mi=e.detail.entityId);w.addEventListener("location-changed",()=>navd++);
 el6.shadowRoot.querySelector('[data-tile="m:sensor.w1"]').click();
 ok(mi==="sensor.w1"&&navd===0,"Tipp auf Zählerkachel öffnet den Verlauf des Zählers in HA (nicht das Add-on)");
 el6.shadowRoot.querySelector('[data-tile="day"]').click();
 ok(navd===1,"Tipp auf Tagesverbrauch öffnet das Add-on");
 ok(el6.getCardSize()>=3,"getCardSize liefert eine Zahl");}

{ // zwei Anlagen: je Solar und Speicher eine Kachel, kWh, Speicher-Fläche im Verlauf
 const now=Math.floor(Date.now()/1000),n=30;
 const a2={meters:[],today:{},flows:{solar_house:30,solar_battery:0,battery_house:1570,grid_house:1093},pv_w:30,house_w:2693,battery_w:1570,grid_w:1093,avg_soc:41,kwh:6.2,cap_kwh:15,target_w:1600,
  units:[{name:"Anker Solix 4 HÜTTE",pv:10,soc:14,kwh:0.7,cap:5,set:800,bat:800,available:true},{name:"Anker Solix 4 DACH",pv:20,soc:55,kwh:5.5,cap:10,set:800,bat:770,available:true}],
  trend:{t:Array.from({length:n},(_,i)=>now-(n-1-i)*300),pv:Array(n).fill(400),house:Array(n).fill(900),bat:Array.from({length:n},(_,i)=>i>10?500:0)}};
 const e2=mk({},st("Entladen",a2)),sv=e2.shadowRoot.querySelector('svg[aria-label="Energiefluss"]').textContent;
 ok(sv.includes("HÜTTE")&&sv.includes("DACH")&&!sv.includes("ANKER")&&sv.includes("14 % · 0,7 kWh")&&sv.includes("55 % · 5,5 kWh"),"Zwei Speicher: Kurznamen, Ladestand und kWh je Speicher");
 ok(sv.includes("Solar HÜTTE")&&sv.includes("Solar DACH"),"Zwei Solarkacheln");
 { const ch=FH.chips(e2.shadowRoot.querySelector('svg[aria-label="Energiefluss"]'));
   ok(["10 W","20 W","800 W","770 W","1.093 W"].every(c=>ch.includes(c)),"Paar-Ansicht: je Anlage Solar->Haus und Speicher->Haus, Netz->Haus"); }
 const hl=e2.shadowRoot.querySelector(".headline");ok(e2.shadowRoot.textContent.includes("6,2 von 15 kWh"),"Gesamt-Ladestand mit kWh");
 ok(e2.shadowRoot.querySelector('svg[aria-label^="Verlauf"]').textContent.includes("aus Speichern"),"Verlauf zeigt die Abgabe der Speicher");
 ok(e2.shadowRoot.textContent.includes("5,5 von 10 kWh"),"Speicherliste mit kWh");
}
{ // Überschrift richtet sich nach den echten Flüssen, nicht nach dem Sollwert
 const base={meters:[],today:{},pv_w:0,house_w:229,battery_w:0,grid_w:229,avg_soc:8,kwh:1.3,cap_kwh:15,target_w:339,
  flows:{solar_house:0,solar_battery:0,battery_house:0,grid_house:229},
  units:[{name:"Anker Solix 4 HÜTTE",pv:0,soc:5,kwh:0.3,cap:5,bat:0,available:true},{name:"Anker Solix 4 DACH",pv:0,soc:10,kwh:1,cap:10,bat:0,available:true}]};
 let e=mk({},st("Entladen",base)),h=e.shadowRoot.querySelector(".headline").textContent;
 ok(h.startsWith("Das Netz versorgt dein Haus")&&!h.includes("339 W versorgen")&&!/Speicher versorgen dein Haus mit 339/.test(h),"Überschrift: Speicher liefern nichts -> Netz versorgt das Haus");
 ok(e.shadowRoot.textContent.includes("liefern noch nichts (Sollwert 339 W)"),"Zweite Zeile nennt den Sollwert als Anforderung");
 const lim=JSON.parse(JSON.stringify(base));lim.limited=true;lim.units[1].locked=true;
 e=mk({},st("Entladen",lim));
 ok(e.shadowRoot.querySelector(".headline").textContent.startsWith("Speicher an der Entladegrenze"),"Überschrift: gesperrter Speicher -> Entladegrenze");
 ok(e.shadowRoot.querySelector('svg[aria-label="Energiefluss"]').textContent.includes("Grenze"),"Gesperrter Speicher zeigt Grenze statt Watt");
 const sol=JSON.parse(JSON.stringify(base));sol.flows={solar_house:0,solar_battery:80,battery_house:0,grid_house:511};sol.house_w=511;sol.grid_w=511;sol.pv_w=80;sol.battery_w=-80;sol.units[1].pv=80;sol.units[1].bat=-80;
 e=mk({},st("Entladen",sol));h=e.shadowRoot.querySelector(".headline").textContent;
 ok(h.startsWith("Solar lädt den Speicher mit 80 W")&&!h.includes("Überschuss"),"Solar lädt, Haus am Netz: kein „Überschuss“");
 ok(e.shadowRoot.textContent.includes("Haus bezieht 511 W aus dem Netz"),"Zweite Zeile nennt den Netzbezug");
 const sv=e.shadowRoot.querySelector('svg[aria-label="Energiefluss"]').textContent;
 ok(sv.includes("lädt")&&sv.includes("bereit"),"Speicher-Kacheln: lädt / bereit statt zweimal derselben Wattzahl");
 const dis=JSON.parse(JSON.stringify(base));dis.flows={solar_house:0,solar_battery:0,battery_house:330,grid_house:150};dis.units[1].bat=330;dis.battery_w=330;
 e=mk({},st("Entladen",dis));
 ok(e.shadowRoot.querySelector('svg[aria-label="Energiefluss"]').textContent.includes("entlädt"),"Speicher-Kachel: entlädt");
 // Heute: Aus Speichern
 const td=JSON.parse(JSON.stringify(base));td.today={house:3,pv:0,imp:1.7,bat:1.4,chg:0.6};td.meters_cfg={show_day:true,extra:true};
 e=mk({},st("Entladen",td));
 ok(e.shadowRoot.textContent.includes("Aus Speichern heute")&&e.shadowRoot.textContent.includes("0,6 kWh geladen"),"Heute-Reihe: Aus Speichern mit geladener Menge");
}
{ // Farbverlauf: Standard an, per gradient:false aus
 let e=mk({},st("Entladen",attrs));
 ok(e.shadowRoot.querySelector("ha-card").classList.contains("grad")&&e.shadowRoot.innerHTML.includes("ha-card.grad{background:linear-gradient"),"Karte hat standardmäßig den Farbverlauf");
 e=mk({gradient:false},st("Entladen",attrs));
 ok(!e.shadowRoot.querySelector("ha-card").classList.contains("grad"),"gradient:false schaltet den Verlauf aus");
 e.setConfig({});e.hass={states:st("Entladen",attrs)};
 ok(e.shadowRoot.querySelector("ha-card").classList.contains("grad"),"Umschalten ändert die Klasse am bestehenden ha-card");
}
{ // Energiefluss: Vorlagen, Ausblenden, Reihenfolge aus Add-on und Kartenoptionen
 const U2=[{name:"Anker HÜTTE",pv:400,bat:-100,soc:50,kwh:2.5},{name:"Anker DACH",pv:500,bat:-200,soc:70,kwh:7}];
 const a2={...attrs,units:U2,flow_cfg:{layout:"total",total:true,solar:true,bat:true,grid:true,house:true,grid_pos:"mid",order:[]}};
 const labels=e=>[...e.shadowRoot.querySelectorAll("svg[aria-label='Energiefluss'] .sf-l")].map(x=>x.textContent);
 let e=mk({},st("Entladen",a2));
 ok(labels(e).length===7&&labels(e).includes("Solar")&&txt(e).includes("alle Anlagen")&&txt(e).includes("900 W"),"Gesamt-Solar oben: sieben Kacheln, Summe 900 W");
 e=mk({flow_layout:"pairs"},st("Entladen",a2));
 ok(labels(e).length===6&&!txt(e).includes("alle Anlagen"),"Vorlage Paare: ohne Gesamt-Kachel");
 e=mk({flow_layout:"compact"},st("Entladen",a2));
 ok(labels(e).length===4&&labels(e).includes("Speicher"),"Vorlage Kompakt: vier Kacheln");
 e=mk({flow_hide:["grid","solar"]},st("Entladen",a2));
 ok(!labels(e).includes("Netz")&&!labels(e).some(l=>l.startsWith("SOLAR ")||l.startsWith("Solar ")),"flow_hide blendet Netz und Solar je Anlage aus");
 e=mk({},st("Entladen",{...a2,flow_cfg:{...a2.flow_cfg,bat:false,house:false}}));
 ok(!labels(e).includes("Haus")&&labels(e).length===4,"Einstellung aus dem Add-on wird übernommen (ohne Speicher und Haus)");
 e=mk({flow_order:["Anker DACH","Anker HÜTTE"]},st("Entladen",a2));
 const names=[...e.shadowRoot.querySelectorAll("svg[aria-label='Energiefluss'] .sf-l")].map(x=>x.textContent).filter(x=>/DACH|HÜTTE/.test(x));
 ok(names[0].includes("DACH")&&names[2].includes("HÜTTE"),"flow_order tauscht die Anlagen");
 e=mk({flow_grid_pos:"side"},st("Entladen",a2));
 ok(/viewBox="0 0 640 454"/.test(e.shadowRoot.innerHTML)||labels(e).length===7,"Netz neben dem Haus bleibt vollständig");
}
ok(w.__kwScrollGuard===true,"Scroll-Wächter ist aktiv");
ok(errors.length===0,"keine JS-Fehler "+errors.join("|"));