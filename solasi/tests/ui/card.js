const {JSDOM}=require("jsdom");const fs=require("fs");const path=require("path");const APP=path.join(__dirname,"..","..","app");
const src=fs.readFileSync(path.join(APP,"card","solasi-card.js"),"utf8");
const errors=[];
const dom=new JSDOM("<!DOCTYPE html><body></body>",{runScripts:"outside-only",pretendToBeVisual:true});
const w=dom.window;w.addEventListener("error",e=>errors.push(e.message));
w.eval(src);
const ok=(c,m)=>{if(!c){console.log("FAIL:",m);process.exitCode=1}else console.log("ok  :",m)};
const attrs={mode:"test",pv_w:3000,battery_w:-1100,house_w:1380,grid_w:400,target_w:390,surplus_w:1620,avg_soc:62,eco_active:true,meter_ok:true,blocked_w:1380,
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
ok(txt(el).includes("3000 W")&&txt(el).includes("1100 W")&&txt(el).includes("1380 W")&&txt(el).includes("lädt")&&txt(el).includes("Bezug"),"Diagramm zeigt PV, Speicher (lädt), Haus, Netz (Bezug)");
ok(q(el,".line.on").length===3&&q(el,".line.on.rev").length===2,"3 aktive Linien, davon 2 rückwärts (Speicher lädt, Netz-Bezug)");
ok(q(el,".headline")[0].textContent.startsWith("Im Test: Die Speicher versorgen dein Haus mit 390 W"),"Überschrift im Testmodus");
ok(q(el,".pill.test").length===1&&txt(el).includes("Testmodus"),"Modus-Pille");
ok(txt(el).includes("Wallbox")&&txt(el).includes("1620 W")&&txt(el).includes("Eco-Modus")&&txt(el).includes("Entladung gesperrt für 1380 W"),"Überschuss, Eco-Tag, Sperre");
ok(q(el,".unit").length===2&&txt(el).includes("Abregelung")&&txt(el).includes("nicht verfügbar")&&txt(el).includes("Solar 540 W"),"Speicher-Kacheln inkl. Abregelung und Solarleistung");
ok(!el.shadowRoot.innerHTML.includes("<img")&&el.shadowRoot.innerHTML.includes("&lt;img"),"HTML in Namen wird maskiert (kein XSS)");

el=mk({title:"",show_batteries:false,show_surplus:false,show_tags:false,show_headline:false},st("Leerlauf",attrs));
ok(q(el,".head").length===0&&q(el,".unit").length===0&&q(el,".surplus").length===0&&q(el,".tags").length===0&&q(el,".headline").length===0&&q(el,"svg").length===1,"Optionen blenden Teile aus, Diagramm bleibt");

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
ok(txt(el).includes("Alles ausgeglichen")&&q(el,".line.on").length===0&&txt(el).includes("ausgeglichen"),"Leerlauf: keine Animation, fehlende PV/Haus = –");
ok(errors.length===0,"keine JS-Fehler "+errors.join("|"));
