/* SOLASI – Dashboard-Karte (Energiefluss)
 *
 * Verwendung:
 *   type: custom:solasi-card
 *   entity: sensor.solasi          # optional, Standard
 *   title: SOLASI                  # optional, "" blendet den Titel aus
 *   show_headline: true             # Klartext-Überschrift
 *   show_batteries: true            # Ladestand je Speicher
 *   show_surplus: true              # Überschuss und Verbraucher
 *   show_tags: true                 # Eco, Zähler, Sollwert
 *   size: large                     # large oder compact (nur Kacheln)
 *   show_trend: true                # Tagesverlauf von Solar und Haus
 *   show_meters: true               # Reihe mit Tagesverbrauch und Zählern ganz oben
 *   meters_layout: big              # big (große Kachel links) oder even (alle gleich groß)
 *   # Tipp auf eine Zählerkachel öffnet Verlauf und Statistik des Zählers (Home Assistant)
 *   flow_layout: auto               # Energiefluss: auto (wie im Add-on), total, pairs oder compact
 *   flow_hide: [grid]               # Kacheln ausblenden: total, solar, bat, grid, house
 *   flow_size: auto                 # Größe des Energieflusses: auto, compact oder large
 *   flow_grid_pos: auto             # Netz: auto, mid (Mitte) oder side (neben dem Haus)
 *   flow_passthrough: true          # umgeladenen Strom als „durchgereicht“ zeigen (Hauskachel ohne Ladeleistung)
 *   flow_order: ["Name 1", "Name 2"] # Reihenfolge der Anlagen im Energiefluss (leer = wie im Add-on)
 *   meters_compare: auto            # Vergleich mit gestern: auto (wie im Add-on), same (gleiche Uhrzeit), full (ganzer Tag), off
 *   meters_order: [day, "m:sensor.wasser", pv, imp]   # Reihenfolge der Zählerkacheln (leer = wie im Add-on)
 *   order: [meters, headline, flow, trend, batteries, surplus, tags]   # Reihenfolge der Blöcke (Standard wie hier)
 *   show_kill: true                 # Not-Aus-Knopf (braucht MQTT, siehe Anleitung)
 *   debug: false                    # Sprung-Diagnose einblenden (auch über das Add-on einschaltbar)
 *   tap_open: true                  # Antippen öffnet SOLASI
 *   accent: ""                      # Akzentfarbe, z. B. "#3F5BD8" (leer = Standard)
 *   gradient: true                  # sanfter Farbverlauf im Kartenhintergrund (false = einfarbig)
 */
(() => {
  const VERSION = "__VERSION__";

  /* Scroll-Wächter: Springt die Seite ohne Eingabe weit nach oben und landet dabei am unteren Ende (der Browser
     begrenzt die Position, weil die Seite kurz niedriger wurde), wird die alte Position zurückgeholt, sobald die
     Seite wieder wächst. Gemeinsam für alle Karten, läuft nur einmal je Seite. */
  (() => {
    if (window.__kwScrollGuard) return;
    window.__kwScrollGuard = true;
    let input = 0;
    const last = new WeakMap(), hooked = new WeakSet();
    const scrollerOf = t => (t === document || t === window || !t || t === document.documentElement || t === document.body) ? document.scrollingElement : t;
    const restore = (el, want) => {
      const t0 = Date.now(), seen = input;
      const step = () => {
        if (input !== seen || Date.now() - t0 > 2500) return;       // Nutzer greift ein oder zu lange her
        if (el.scrollTop < want - 1) { el.scrollTop = want; requestAnimationFrame(step); }
        else last.set(el, el.scrollTop);
      };
      requestAnimationFrame(step);
    };
    const onScroll = ev => {
      const el = scrollerOf(ev.target);
      if (!el) return;
      const y = el.scrollTop, prev = last.get(el) || 0, max = el.scrollHeight - el.clientHeight;
      if (Date.now() - input > 400 && prev - y > 120 && y >= max - 3) { if (window.__kwDbg) window.__kwDbg(`Wächter: Sprung ${Math.round(prev)}→${Math.round(y)} px, hole zurück`); restore(el, prev); }
      else last.set(el, y);
    };
    const hook = el => { if (el && !hooked.has(el)) { hooked.add(el); el.addEventListener("scroll", onScroll, { passive: true }); last.set(el, el.scrollTop); } };
    hook(window);
    addEventListener("scroll", onScroll, { passive: true, capture: true });
    ["wheel", "touchstart", "touchmove", "touchend", "keydown", "pointerdown", "mousedown"].forEach(n =>
      addEventListener(n, ev => {
        input = Date.now();
        for (const n2 of (ev.composedPath ? ev.composedPath() : [])) {      // Scroll-Container auch in Shadow-DOMs finden
          if (n2 && n2.nodeType === 1 && n2.scrollHeight > n2.clientHeight + 4) {
            const o = getComputedStyle(n2).overflowY;
            if (o === "auto" || o === "scroll") { hook(n2); break; }
          }
        }
      }, { passive: true, capture: true }));
  })();
  const W = v => (v == null || isNaN(v)) ? "–" : `${Math.round(v)} W`;
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  let lastScrollAt = 0;
  addEventListener("scroll", () => { lastScrollAt = Date.now(); }, { passive: true, capture: true });
  const BLOCKS = [["meters", "Zählerreihe"], ["headline", "Überschrift"], ["flow", "Energiefluss"], ["trend", "Tagesverlauf"],
                  ["batteries", "Speicher"], ["surplus", "Überschuss"], ["tags", "Hinweise"]];
  const CARD_KEYS = ["size", "show_headline", "show_meters", "meters_layout", "show_trend", "show_batteries", "show_surplus", "show_tags", "show_kill", "accent", "gradient", "order"];
  const blockOrder = o => {
    const all = BLOCKS.map(b => b[0]);
    const ord = (Array.isArray(o) ? o : []).filter((x, i, a) => all.includes(x) && a.indexOf(x) === i);
    return [...ord, ...all.filter(x => !ord.includes(x))];
  };

  /* Zeichnet in das Shadow-DOM, ohne <ha-card> neu zu erzeugen. Ein neues ha-card rendert seinen Inhalt erst in einem
     Microtask; erzwingt vorher irgendeine Karte ein Layout (Höhe messen), ist die Karte für einen Moment leer, die Seite
     wird kürzer, der Browser kappt die Scrollposition und die Ansicht springt nach oben. Hier bleibt ha-card bestehen,
     nur Stil und Inhalt werden ersetzt (in einem Schritt, ohne Zwischen-Layout). */
  function paintShadow(root, html) {
    const t = document.createElement("template");
    t.innerHTML = html;
    const kids = [...t.content.children], nc = kids[kids.length - 1];
    const cur = [...root.children].find(e => e.localName === "ha-card");
    const ok = cur && nc && nc.localName === "ha-card" && root.lastElementChild === cur && root.children.length === kids.length &&
      kids.slice(0, -1).every((k, i) => k.localName === "style" && root.children[i].localName === "style");
    if (!ok) { root.innerHTML = html; return; }
    kids.slice(0, -1).forEach((k, i) => { const s = root.children[i]; if (s.textContent !== k.textContent) s.textContent = k.textContent; });
    for (const a of [...cur.attributes]) if (a.name !== "style" && !nc.hasAttribute(a.name)) cur.removeAttribute(a.name);
    for (const a of [...nc.attributes]) if (a.name !== "style" && cur.getAttribute(a.name) !== a.value) cur.setAttribute(a.name, a.value);
    cur.replaceChildren(...nc.childNodes);
  }

  /* Diagnose (Add-on: Einstellungen → Darstellung → Sprung-Diagnose, oder Karten-Option debug: true) */
  const DBG = { box: null, lines: [] };
  const dbgOn = () => { try { return localStorage.getItem("solasi_debug") === "1"; } catch (e) { return false; } };
  const dbgNote = t => {
    if (!dbgOn() && !(window.__solasiDebugCard)) return;
    DBG.lines.unshift(new Date().toLocaleTimeString("de-DE") + " " + t);
    DBG.lines.length = Math.min(DBG.lines.length, 10);
    if (!DBG.box) {
      DBG.box = document.createElement("pre");
      DBG.box.style.cssText = "position:fixed;left:6px;bottom:70px;max-width:92vw;z-index:99999;margin:0;padding:6px 8px;border-radius:8px;background:rgba(0,0,0,.82);color:#fff;font:11px/1.35 monospace;white-space:pre-wrap;pointer-events:none";
      document.body.appendChild(DBG.box);
    }
    DBG.box.textContent = `SOLASI-Karte v${VERSION}\n` + DBG.lines.join("\n");
  };
  window.__kwDbg = window.__kwDbg || dbgNote;
  const num = v => (v === null || v === undefined || v === "" || isNaN(Number(v))) ? null : Number(v);

  const STYLE = `
    :host{display:block}
    .hero.grad{background:linear-gradient(135deg,color-mix(in srgb,var(--sc-sun) 16%,var(--sf-card)),var(--sf-card) 70%);border-radius:20px;padding:14px 16px 8px;margin:6px 0 12px;border:1px solid var(--sf-line)}
    .hero .headline{margin-top:0}
    ha-card{padding:14px 16px 12px;overflow:hidden;
      --sc-sun:var(--solasi-sun,#f59e0b);--sc-bat:var(--solasi-battery,#14b8a6);
      --sc-grid:var(--solasi-grid,#6366f1);--sc-home:var(--solasi-home,#64748b);
      --sc-ok:var(--success-color,#1f9d63);--sc-warn:var(--warning-color,#d97706);--sc-bad:var(--error-color,#e5484d);
      --sc-test:var(--solasi-test,#8b5cf6);
      --sf-tile:var(--secondary-background-color,#f3f3f3);
      --sf-card:var(--ha-card-background,var(--card-background-color,#fff));--sf-fg:var(--primary-text-color);--sf-muted:var(--secondary-text-color);
      --sf-line:var(--divider-color,#ddd);--sf-sun:var(--sc-sun);--sf-bat:var(--sc-bat);--sf-grid:var(--sc-grid);--sf-home:var(--sc-home);
      --sf-ok:var(--sc-ok);--sf-warn:var(--sc-warn);--sf-bad:var(--sc-bad)}
    .stale{opacity:.55}
    .oldv{font-size:11.5px;margin:0 0 6px;padding:6px 10px;border-radius:10px;background:color-mix(in srgb,var(--sc-warn) 18%,transparent);color:var(--primary-text-color)}
    .head{display:flex;align-items:center;gap:8px;margin-bottom:2px}
    .head .t{font-size:16px;font-weight:600;color:var(--primary-text-color)}
    .pill{margin-left:auto;font-size:11.5px;font-weight:600;padding:3px 10px;border-radius:999px;
      background:var(--secondary-background-color,#f3f3f3);color:var(--secondary-text-color)}
    .pill.live{color:var(--sc-ok)}.pill.test{color:var(--sc-test)}.pill.observe{color:var(--sc-warn)}.pill.bad,.pill.stopped{color:var(--sc-bad)}
    .headline{font-size:17px;font-weight:650;color:var(--primary-text-color);margin-top:4px}
    .sub{font-size:12.5px;color:var(--secondary-text-color);margin-top:1px}
    svg{width:100%;height:auto;display:block;max-height:640px;margin-top:4px}
    svg text{font-family:inherit}
    .lbl{fill:var(--secondary-text-color);font-size:13px;font-weight:600}
    .val{fill:var(--primary-text-color);font-size:17px;font-weight:700}
    .small{fill:var(--secondary-text-color);font-size:11.5px}
    .evl{fill:var(--secondary-text-color);font-size:12px;font-weight:650}
    .line{stroke:var(--divider-color,#dddddd);stroke-width:4;stroke-linecap:round;fill:none}
    .line.on{stroke-dasharray:3 11;animation:dash 1s linear infinite}
    .line.rev{animation-direction:reverse}
    @keyframes dash{to{stroke-dashoffset:-28}}
    @media (prefers-reduced-motion:reduce){.line.on{animation:none}}
    .units{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:8px}
    .unit{background:var(--secondary-background-color,#f6f6f6);border-radius:12px;padding:8px 12px}
    .unit .n{font-size:12px;color:var(--secondary-text-color);font-weight:600}
    .unit .s{font-size:19px;font-weight:700;color:var(--primary-text-color)}
    .bar{height:7px;border-radius:4px;background:var(--divider-color,#ddd);overflow:hidden;margin:4px 0 3px}
    .bar>div{height:100%}
    .unit .d{font-size:11.5px;color:var(--secondary-text-color)}
    .tags{margin-top:8px}
    .tag{display:inline-block;font-size:11.5px;border-radius:8px;padding:2px 9px;margin:2px 5px 0 0;
      background:var(--secondary-background-color,#f3f3f3);color:var(--secondary-text-color)}
    .tag.ok{color:var(--sc-ok)}.tag.warn{color:var(--sc-warn)}.tag.bad{color:var(--sc-bad)}
    .row{display:flex;justify-content:space-between;font-size:13px;padding:4px 0;color:var(--primary-text-color);
      border-bottom:1px solid var(--divider-color,#eee)}
    .row:last-child{border:0}
    .msg{padding:18px 6px;color:var(--secondary-text-color);text-align:center;font-size:14px}
    .surplus{margin-top:8px}
    ha-card.tap{cursor:pointer}
    .mwrap{margin:8px 0 18px;padding-bottom:18px;border-bottom:1px solid var(--divider-color,#e0e0e0)}
    .mwrap + .headline{margin-top:0}
    .kill{border:1px solid var(--sc-bad);background:none;color:var(--sc-bad);border-radius:999px;padding:3px 11px;font:inherit;font-size:12px;font-weight:700;cursor:pointer}
    .kill.arm{background:var(--sc-bad);color:#fff}
    .kill.go{border-color:var(--sc-ok);color:var(--sc-ok)}
    .when{font-size:11.5px;color:var(--secondary-text-color)}
    .tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:10px;margin-top:8px}
    .tile{background:var(--secondary-background-color,#f6f6f6);border-radius:12px;padding:8px 12px}
    .tile .n{font-size:11.5px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--secondary-text-color)}
    .tile .v{font-size:22px;font-weight:700;color:var(--primary-text-color)}
    .tile.sun .v{color:var(--sc-sun)}.tile.bat .v{color:var(--sc-bat)}.tile.grid .v{color:var(--sc-grid)}.tile.home .v{color:var(--sc-home)}
    .trend{margin-top:6px}
    .trend svg{max-height:none;margin:0}
    .eyebrow{font-size:11.5px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--secondary-text-color);margin-bottom:2px}
  `;

/*FLOW-BEGIN*/
/* Gemeinsame Zeichnungen für Oberfläche und Dashboard-Karte: Energiefluss, Verlauf, Überschrift.
   Quelle für beide Stellen. Nach Änderungen `python tools/sync_flow.py` ausführen, das kopiert
   diesen Block in solasi/app/static/index.html und solasi/app/card/solasi-card.js.
   Farben kommen aus Variablen, die jede Stelle selbst setzt:
   --sf-card --sf-tile --sf-fg --sf-muted --sf-line --sf-sun --sf-bat --sf-grid --sf-home --sf-ok --sf-warn --sf-bad */
const SF = (() => {
  const fmt = v => Math.round(v).toLocaleString("de-DE");
  const wl = v => (v == null || isNaN(v)) ? "–" : fmt(v) + " W";
  const TW = 150, TH = 76;
  const T = { sun: { x: 245, y: 12 }, bat: { x: 20, y: 152 }, grid: { x: 470, y: 152 }, home: { x: 245, y: 252 } };
  // Linien in Flussrichtung: Solar→Haus, Solar→Speicher, Speicher→Haus, Netz→Haus
  const L = {
    sh: { pts: [[320, 88], [320, 140], [320, 200], [320, 252]], col: "--sf-sun" },
    sb: { pts: [[245, 50], [140, 50], [95, 92], [95, 152]], col: "--sf-sun" },
    bh: { pts: [[95, 228], [95, 275], [150, 290], [245, 290]], col: "--sf-bat" },
    gh: { pts: [[545, 228], [545, 270], [490, 290], [395, 290]], col: "--sf-grid" }
  };
  const bez = (p, t) => { const u = 1 - t; return [0, 1].map(i => u * u * u * p[0][i] + 3 * u * u * t * p[1][i] + 3 * u * t * t * p[2][i] + t * t * t * p[3][i]); };
  const pd = p => `M${p[0][0]} ${p[0][1]}C${p[1][0]} ${p[1][1]} ${p[2][0]} ${p[2][1]} ${p[3][0]} ${p[3][1]}`;
  const reduced = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const socCol = s => s == null || s < 0 ? "var(--sf-muted)" : s < 20 ? "var(--sf-bad)" : s < 45 ? "var(--sf-warn)" : "var(--sf-ok)";
  const CSS = `<style>
    .sf-l{font-size:12.5px;font-weight:700;letter-spacing:.08em;fill:var(--sf-muted);text-transform:uppercase}
    .sf-t{font-size:11px;font-weight:600;fill:var(--sf-muted);text-anchor:end}
    .sf-v{font-size:22px;font-weight:800;fill:var(--sf-fg)}
    .sf-s{font-size:12.5px;font-weight:500;fill:var(--sf-muted)}
    .sf-c{font-size:12.5px;font-weight:700;fill:var(--sf-fg)}
    .sf-a{font-size:13px;fill:var(--sf-muted)}
    .sf-g{stroke:var(--sf-line);stroke-width:1;fill:none}
    .sf-i{fill:none;stroke:var(--sf-line);stroke-width:2.5;stroke-linecap:round}
    .sf-o{fill:none;stroke-linecap:round}
    svg text{font-family:inherit}</style>`;

  const ICON = {
    sun: c => `<g fill="none" stroke="${c}" stroke-width="2" stroke-linecap="round"><circle cx="16" cy="16" r="5.5"/><path d="M16 3v3.5M16 25.5V29M3 16h3.5M25.5 16H29M6.8 6.8l2.5 2.5M22.7 22.7l2.5 2.5M25.2 6.8l-2.5 2.5M9.3 22.7l-2.5 2.5"/></g>`,
    home: c => `<g fill="none" stroke="${c}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"><path d="M4 15.5 16 5l12 10.5"/><path d="M7 13.5V27h18V13.5"/><path d="M13.5 27v-7h5v7"/></g>`,
    grid: c => `<g fill="none" stroke="${c}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"><path d="M16 3v26M9 29l7-17 7 17M10.5 12h11M12.5 19.5h7"/></g>`,
    bat: (c, soc) => {
      const w = soc == null || soc < 0 ? 0 : Math.max(0, Math.min(100, soc)) / 100 * 17;
      return `<g fill="none" stroke="${c}" stroke-width="2" stroke-linejoin="round"><rect x="3" y="9" width="23" height="14" rx="3.5"/><path d="M28.5 13.5v5" stroke-linecap="round"/></g>` +
        (w ? `<rect x="6" y="12" width="${w.toFixed(1)}" height="8" rx="1.8" style="fill:${socCol(soc)}"/>` : "");
    }
  };

  function tile(k, label, val, sub, col, icon, pos, tag) {
    const t = pos || T[k], w = t.w || TW;
    return `<g${t.dim ? ' opacity=".42"' : ""}><rect x="${t.x}" y="${t.y}" width="${w}" height="${TH}" rx="18" style="fill:var(--sf-card)"/>
      <rect x="${t.x}" y="${t.y}" width="${w}" height="${TH}" rx="18" style="fill:var(${col});fill-opacity:.13;stroke:var(${col});stroke-width:1.6"/>
      <g transform="translate(${t.x + 14} ${t.y + 14})">${icon}</g>
      <text x="${t.x + 54}" y="${t.y + 27}" class="sf-l">${label}</text>
      ${tag ? `<text x="${t.x + w - 12}" y="${t.y + 27}" class="sf-t">${esc(tag)}</text>` : ""}
      <text x="${t.x + 54}" y="${t.y + 50}" class="sf-v">${val}</text>
      ${sub ? `<text x="${t.x + 54}" y="${t.y + 66}" class="sf-s">${sub}</text>` : ""}</g>`;
  }

  /* Linien zeichnen: lines = [{pts, col, val}] */
  function drawLines(lines) {
    let idle = "", live = "", dots = "", chips = "";
    for (const x of lines) {
      const val = x.val == null ? 0 : x.val;
      idle += `<path d="${pd(x.pts)}" class="sf-i"/>`;
      if (Math.abs(val) < 5) continue;
      const pts = val >= 0 ? x.pts : [...x.pts].reverse();
      const a = Math.abs(val), w = Math.min(6.5, 2.6 + a / 450);
      live += `<path d="${pd(pts)}" class="sf-o" style="stroke:var(${x.col});stroke-opacity:.5;stroke-width:${w.toFixed(1)}"/>`;
      const dur = Math.max(1.6, Math.min(4, 4.2 - a / 450));
      for (let i = 0; i < 3; i++) {
        if (reduced()) {
          const [px, py] = bez(pts, .2 + i * .3);
          dots += `<circle cx="${px.toFixed(1)}" cy="${py.toFixed(1)}" r="${(w / 2 + 1.6).toFixed(1)}" style="fill:var(${x.col})"/>`;
        } else {
          dots += `<circle r="${(w / 2 + 1.8).toFixed(1)}" style="fill:var(${x.col})"><animateMotion dur="${dur.toFixed(2)}s" begin="${(-i * dur / 3).toFixed(2)}s" repeatCount="indefinite" path="${pd(pts)}"/></circle>`;
        }
      }
      const [mx, my] = bez(x.pts, .5), txt = fmt(a) + " W", cw = txt.length * 7.8 + 16;
      chips += `<rect x="${(mx - cw / 2).toFixed(1)}" y="${(my - 11).toFixed(1)}" width="${cw.toFixed(1)}" height="22" rx="11" style="fill:var(--sf-card);stroke:var(${x.col});stroke-opacity:.55"/>
        <text x="${mx.toFixed(1)}" y="${(my + 4).toFixed(1)}" text-anchor="middle" class="sf-c">${txt}</text>${x.lab && val < 0 ? `<text x="${mx.toFixed(1)}" y="${(my + 24).toFixed(1)}" text-anchor="middle" class="sf-s">${x.lab}</text>` : ""}`;
    }
    return idle + live + dots + chips;
  }

  /* Breite der Zeichnung in Einheiten: bei schmalen Anzeigen 640, bei breiten wächst sie mit (bis 1100).
     Die Kacheln behalten ihre Größe, der Platz geht in Abstand zwischen den Spalten. */
  function flowW(d, o) {
    const px = Number(d.w) || 0;
    if (!px) return 640;
    const k = o.size === "large" ? 1.15 : o.size === "compact" ? 0.8 : 0.95, max = o.size === "large" ? 900 : o.size === "compact" ? 1200 : 1100;
    return Math.round(Math.max(640, Math.min(max, px / k)) / 20) * 20;
  }
  const nf1 = v => Number(v).toLocaleString("de-DE", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const kwhTxt = v => v == null || isNaN(v) ? "" : nf1(v) + " kWh";
  /* Kurznamen: gemeinsamen Anfang abschneiden („Anker Solix 4 HÜTTE“ und „… DACH“ -> „HÜTTE“, „DACH“) */
  function shortNames(names) {
    if (names.length < 2) return names.slice();
    let p = names[0];
    for (const n of names) { while (p && !n.startsWith(p)) p = p.slice(0, -1); }
    p = p.replace(/\S*$/, "");                       // nur an Wortgrenzen kürzen
    const cut = names.map(n => n.slice(p.length).trim());
    return cut.every(c => c.length >= 3) ? cut : names.slice();
  }
  const clip = (t, n) => { t = String(t); return t.length > n ? t.slice(0, n - 1) + "…" : t; };

  /* Anzeige eines Speichers: Wert und Richtung. Unter 5 W gilt er als bereit, mit Grenze/voll als solcher. */
  function batState(u, bat) {
    if (u && u.paused) return ["pausiert", "Wartung"];
    if (u && u.locked) return ["Grenze", ""];
    if (bat == null) return ["–", ""];
    if (Math.abs(bat) < 5) return [u && u.full ? "voll" : "bereit", ""];
    return [wl(Math.abs(bat)), bat > 0 ? "entlädt" : "lädt"];
  }

  /* Zwei Anlagen. Zeilen von oben nach unten: Solar gesamt, Solar je Anlage, Speicher je Anlage, Haus; das Netz sitzt in der
     Mitte der ersten freien Zeile (oder neben dem Haus). Ausgeblendete Kacheln nehmen ihre Zeile und ihre Linien mit. */
  function flowPairs(d, U, o) {
    const names = shortNames(U.map(u => u.name)), th = TH, w = 170, W = flowW(d, o);
    const cx = [10, W - 10 - w], mx = (W - TW) / 2, mc = W / 2;
    const showT = o.layout !== "pairs" && o.total, showS = o.solar, showB = o.bat, showG = o.grid, showH = o.house;
    const gridSide = showG && showH && o.grid_pos === "side";
    const gridRow = !showG || gridSide ? "" : showS ? "s" : showB ? "b" : "g";
    const rows = [["t", showT, 34], ["s", showS, 38], ["g", gridRow === "g", 38], ["b", showB, 42], ["h", showH, 24]];
    const Y = {}; let y = 12, bottom = 12;
    for (const [k, on, gap] of rows) if (on) { Y[k] = y; bottom = y + th; y += th + gap; }
    const H = bottom + 24;
    const vc = (x1, y1, x2, y2) => { const k = Math.min(18, Math.abs(y2 - y1) / 2); return [[x1, y1], [x1, y1 + k], [x2, y2 - k], [x2, y2]]; };
    const lines = [], tiles = [];
    // AC-Laden aus dem Haus (Umladen): zählt im gemessenen Verbrauch mit, ist aber nur durchgereicht
    const pass = !o.passthrough ? 0 : U.reduce((a, u) => { const p = u.paused || u.pv == null ? 0 : Math.max(u.pv, 0), c = u.paused || u.bat == null ? 0 : Math.max(-u.bat, 0); return a + Math.max(c - p, 0); }, 0);
    const known = U.filter(u => u.pv != null);
    const total = known.length ? known.reduce((a, u) => a + Math.max(u.pv, 0), 0) : (d.pv == null ? null : Math.max(d.pv, 0));
    U.forEach((u, i) => {
      const x = cx[i], c = x + w / 2, left = i === 0;
      const pz = !!u.paused;                            // Wartung: ausgegraut, ohne Werte und Linien
      const pv = pz || u.pv == null ? null : Math.max(u.pv, 0), bat = pz || u.bat == null ? 0 : u.bat;
      const chg = Math.max(-bat, 0), dis = Math.max(bat, 0);
      const toHouse = pv == null ? null : Math.max(pv - chg, 0);
      const ex = left ? x + w : x;                       // Seite zur Mitte
      const mid = left ? ex + 33 : ex - 33, hin = left ? mx : mx + TW;
      // Solar gesamt: die Linien verlassen die Kachel seitlich und laufen von oben in die Anlagen
      const ty = Y.t + th / 2, sx = left ? mx : mx + TW, sd = (mc - c) * .55;
      const side = yy => [[sx, ty], [sx - sd, ty], [c, ty + (yy - ty) * .5], [c, yy]];
      if (showT && showS) lines.push({ pts: side(Y.s), col: "--sf-sun", val: pv });
      const own = Math.min(chg, pv == null ? 0 : pv), ac = Math.max(chg - (pv == null ? 0 : pv), 0);   // Rest kommt per AC aus dem Haus
      if (showS && showB) lines.push({ pts: vc(c, Y.s + th, c, Y.b), col: "--sf-sun", val: pv == null ? null : own });
      else if (showT && showB) lines.push({ pts: side(Y.b), col: "--sf-sun", val: pv == null ? null : own });
      if (showH && showS) lines.push({ pts: [[ex, Y.s + 38], [mid, Y.s + 38], [mid, Y.h + 24], [hin, Y.h + 24]], col: "--sf-sun", val: toHouse });
      else if (showH && showT) { const sx = left ? mx + 35 : mx + TW - 35; lines.push({ pts: [[sx, Y.t + th], [mid, Y.t + th + (Y.h - Y.t - th) * .3], [mid, Y.h + 24], [hin, Y.h + 24]], col: "--sf-sun", val: toHouse }); }
      if (showB && showH) lines.push({ pts: [[c, Y.b + th], [c, Y.h + 52], [left ? ex + 25 : ex - 25, Y.h + 52], [hin, Y.h + 52]], col: "--sf-bat", val: dis > 0 ? dis : -ac, lab: o.passthrough ? "durchgereicht" : "" });
      const soc = u.soc != null && u.soc >= 0 ? Math.round(u.soc) : null;
      const sub = [soc != null ? soc + " %" : "", kwhTxt(u.kwh)].filter(Boolean).join(" · ");
      if (showS) tiles.push(tile("sun", "Solar " + esc(clip(names[i], 9)), pz ? "–" : wl(u.pv), pz ? "Wartung" : u.pv != null && u.pv < 5 ? "keine Sonne" : "", "--sf-sun", ICON.sun("var(--sf-sun)"), { x, y: Y.s, w, dim: pz }));
      if (showB) {
        const [bv, bt] = batState(u, u.bat);
        tiles.push(tile("bat", esc(clip(names[i], bt ? 7 : 12)), bv, sub, "--sf-bat", ICON.bat("var(--sf-bat)", soc), { x, y: Y.b, w, dim: pz }, bt));
      }
    });
    const grid = d.grid == null ? 0 : d.grid, gv = d.f ? d.f.gh : grid;
    if (showG && showH) {
      if (gridSide) lines.push({ pts: [[W - 170, Y.h + 38], [W - 195, Y.h + 38], [mx + TW + 25, Y.h + 38], [mx + TW, Y.h + 38]], col: "--sf-grid", val: gv });
      else lines.push({ pts: [[mc, Y[gridRow] + th], [mc, Y[gridRow] + th + 40], [mc, Y.h - 40], [mc, Y.h]], col: "--sf-grid", val: gv });
    }
    if (showT) tiles.push(tile("sun", "Solar", wl(total), total != null && total < 5 ? "keine Sonne" : "alle Anlagen", "--sf-sun", ICON.sun("var(--sf-sun)"), { x: mx, y: Y.t, w: TW }));
    if (showG) tiles.push(tile("grid", "Netz", wl(Math.abs(grid)), grid >= 5 ? "Bezug" : grid <= -5 ? "Einspeisung" : "ausgeglichen", "--sf-grid", ICON.grid("var(--sf-grid)"), gridSide ? { x: W - 170, y: Y.h, w: TW } : { x: mx, y: Y[gridRow], w: TW }));
    if (showH) { const ps = pass >= 10 && d.house != null; tiles.push(tile("home", "Haus", wl(ps ? Math.max(d.house - pass, 0) : d.house), d.house != null ? (ps ? "+" + fmt(pass) + " W Laden" : "Verbrauch") : "", "--sf-home", ICON.home("var(--sf-home)"), { x: mx, y: Y.h, w: TW })); }
    return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Energiefluss">${CSS}${drawLines(lines)}${tiles.join("")}</svg>`;
  }

  /* Mehrere Speicher: je Solaranlage und je Speicher eine Kachel */
  function flowMulti(d, U, o) {
    const f = d.f || {}, nb = U.length, th = TH;
    const ps = U.filter(u => u.pv != null), names = shortNames(U.map(u => u.name));
    const bx = 10, bw = 180, by0 = 112, step = 92;
    const bottom = by0 + (nb - 1) * step + th, H = bottom + 34;
    const hx = 275, hy = by0 + (nb - 1) * step, hm = hy + th / 2;
    const gx = 470, gy = by0;
    const two = ps.length >= 2, sw = 170;
    const sunX = two ? [165, 365] : [hx - 10];           // Mitte bei 350
    const sunN = two ? ps : [null];
    const pvSum = ps.reduce((a, u) => a + Math.max(u.pv, 0), 0);
    const disS = U.reduce((a, u) => a + Math.max(u.bat || 0, 0), 0);
    const lines = [], tiles = [];
    // Solar -> Haus je Solaranlage
    sunN.forEach((u, i) => {
      const x0 = sunX[i], cx = x0 + (two ? sw : 170) / 2, share = u ? (pvSum > 0 ? Math.max(u.pv, 0) / pvSum : 1 / ps.length) : 1;
      if (o.house) lines.push({ pts: [[cx, 88], [cx, 88 + (hy - 88) * .45], [350, hy - (hy - 88) * .45], [350, hy]], col: "--sf-sun", val: f.sh == null ? null : f.sh * share });
    });
    // Solar -> Speicher (gesamt) zur Speicherspalte
    lines.push({ pts: [[sunX[0], 50], [bx + bw / 2, 50], [bx + bw / 2, 80], [bx + bw / 2, by0]], col: "--sf-sun", val: f.sb });
    // Speicher -> Haus je Speicher
    U.forEach((u, i) => {
      const ym = by0 + i * step + th / 2, share = disS > 0 ? Math.max(u.bat || 0, 0) / disS : 1 / nb;
      if (o.house) lines.push({ pts: [[bx + bw, ym], [bx + bw + 42, ym], [hx - 42, hm], [hx, hm]], col: "--sf-bat", val: f.bh == null ? null : f.bh * share });
    });
    if (o.grid && o.house) lines.push({ pts: [[gx + 75, gy + th], [gx + 75, hm], [gx - 10, hm], [hx + 150, hm]], col: "--sf-grid", val: f.gh });
    sunN.forEach((u, i) => {
      tiles.push(tile("sun", u ? "Solar " + esc(clip(names[U.indexOf(u)], 9)) : "Solar", wl(u ? u.pv : d.pv),
        (u ? u.pv : d.pv) != null && (u ? u.pv : d.pv) < 5 ? "keine Sonne" : "", "--sf-sun", ICON.sun("var(--sf-sun)"), { x: sunX[i], y: 12, w: sw }));
    });
    U.forEach((u, i) => {
      const soc = u.soc != null && u.soc >= 0 ? Math.round(u.soc) : null;
      const sub = [soc != null ? soc + " %" : "", kwhTxt(u.kwh)].filter(Boolean).join(" · ");
      const [bv, bt] = batState(u, u.bat);
      tiles.push(tile("bat", esc(clip(names[i], bt ? 8 : 12)), bv, sub, "--sf-bat", ICON.bat("var(--sf-bat)", soc),
        { x: bx, y: by0 + i * step, w: bw }, bt));
    });
    const grid = d.grid == null ? 0 : d.grid;
    if (o.grid) tiles.push(tile("grid", "Netz", wl(Math.abs(grid)), grid >= 5 ? "Bezug" : grid <= -5 ? "Einspeisung" : "ausgeglichen", "--sf-grid", ICON.grid("var(--sf-grid)"), { x: gx, y: gy, w: TW }));
    if (o.house) tiles.push(tile("home", "Haus", wl(d.house), d.house != null ? "Verbrauch" : "", "--sf-home", ICON.home("var(--sf-home)"), { x: hx, y: hy, w: TW }));
    // Linien zuerst, dann Kacheln (Chips liegen über den Linien, Kacheln darüber); bei breiter Anzeige mittig
    const W = flowW(d, o);
    return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Energiefluss">${CSS}<g transform="translate(${(W - 640) / 2} 0)">${drawLines(lines)}${tiles.join("")}</g></svg>`;
  }

  /* Haus-Ansicht: Schrägansicht (isometrisch). Solaranlagen: die erste auf dem Hausdach, weitere auf Pergolen hinter dem Haus.
     Speicher stehen als Schränke vor dem Haus, das Netz als Mast. Linien tragen den Fluss (Punkte laufen gleichmäßig). */
  function flowHouse(d, U, o) {
    const S = 52, OX = 470, OY = 130, K = .866;
    const P = (x, y, z = 0) => [OX + (x - y) * K * S, OY + (x + y) * .5 * S - z * S];
    const pts = a => a.map(p => P(...p).map(v => v.toFixed(1)).join(",")).join(" ");
    const px = Number(d.w) || 0, m = px ? Math.max(1, Math.min(2.4, 850 / px * .8)) : 1;
    const mix = (c, k, w) => `color-mix(in srgb,var(${c}),${k} ${w}%)`;
    const FT = mix("--sf-tile", "#fff", 7), FL = mix("--sf-tile", "#000", 10), FR = mix("--sf-tile", "#000", 20), ST = "var(--sf-line)";
    let ob = "";
    const poly = (a, f, st = ST, sw = 1.4, ex = "") => { ob += `<polygon points="${pts(a)}" style="fill:${f};stroke:${st};stroke-width:${sw}" stroke-linejoin="round" ${ex}/>`; };
    const box = (x, y, z, w, dd, h, top = FT, left = FL, right = FR, st = ST) => {
      poly([[x + w, y, z], [x + w, y + dd, z], [x + w, y + dd, z + h], [x + w, y, z + h]], right, st);
      poly([[x, y + dd, z], [x + w, y + dd, z], [x + w, y + dd, z + h], [x, y + dd, z + h]], left, st);
      poly([[x, y, z + h], [x + w, y, z + h], [x + w, y + dd, z + h], [x, y + dd, z + h]], top, st);
    };
    const tint = (c, w) => `color-mix(in srgb,var(${c}) ${w}%,var(--sf-tile))`;

    // ---- Daten ----
    const grid = d.grid == null ? 0 : d.grid, gv = d.f && d.f.gh != null ? d.f.gh : grid;
    const units = U.length ? U : [{ name: "Speicher", soc: d.soc, kwh: d.kwh, pv: d.pv, bat: d.bat }];
    const n = Math.min(units.length, 4), UU = units.slice(0, n), names = shortNames(UU.map(u => u.name));
    const arrays = UU.map((u, i) => ({ i, pv: u.paused || u.pv == null ? null : Math.max(u.pv, 0), name: names[i] })).filter(a => a.pv != null);
    if (!arrays.length && d.pv != null) arrays.push({ i: 0, pv: Math.max(d.pv, 0), name: "Solar" });
    const pvTotal = arrays.length ? arrays.reduce((a, s) => a + s.pv, 0) : null;
    const lanes = [];      // {pts (Welt), col, val, chip}

    // ---- Boden ----
    box(-.4, -.4, -.3, 11.2, 7.6, .3, mix("--sf-tile", "#fff", 3), mix("--sf-tile", "#000", 8), mix("--sf-tile", "#000", 16));

    // ---- Zusätzliche Anlagen: Aufständerung auf dem Boden vor dem Haus ----
    const GR = [{ x: 8.6, y: 3.2, w: 1.9, d: 1.5, entry: [[8.6, 3.95, .3], [8.02, 3.95, .3]] },
      { x: 8.6, y: 5.1, w: 1.9, d: 1.5, entry: [[8.6, 5.85, .25], [8.3, 5.85, .02], [8.3, 3.3, .02], [8.02, 3.3, .3]] },
      { x: 6.7, y: 5.1, w: 1.7, d: 1.5, entry: [[7.55, 5.1, .3], [7.55, 4.6, .02], [7.2, 4.15, .02]] }];
    arrays.forEach((a, k) => {
      if (k === 0) return;
      const g = GR[Math.min(k - 1, GR.length - 1)], y1 = g.y + g.d;
      box(g.x + .1, y1 - .1, 0, .1, .1, .3, FL, FL, FR); box(g.x + g.w - .2, y1 - .1, 0, .1, .1, .3, FL, FL, FR);
      const pt = (u, v) => [g.x + u * g.w, y1 - v * g.d, .3 + v * .75];
      poly([pt(0, 0), pt(1, 0), pt(1, 1), pt(0, 1)], FR, ST, 1.2);
      for (let i = 0; i < 3; i++) for (let j = 0; j < 2; j++) {
        const u0 = .04 + i * .32, u1 = u0 + .28, v0 = .06 + j * .47, v1 = v0 + .42;
        poly([pt(u0, v0), pt(u1, v0), pt(u1, v1), pt(u0, v1)], tint("--sf-sun", 22), "var(--sf-sun)", 1.3);
      }
      a.world = pt(.5, 1); a.pole = g.entry;
    });

    // ---- Netzmast (hinten rechts) ----
    box(9.6, 1.4, 0, .3, .3, 3.2, FL, FL, FR);
    box(9.15, 1.35, 2.9, 1.2, .4, .12, tint("--sf-grid", 55), tint("--sf-grid", 40), tint("--sf-grid", 30), "var(--sf-grid)");
    ob += `<polyline points="${pts([[9.6, 1.55, 3.0], [8.6, 1.9, 2.4], [8, 2.0, 2.3]])}" style="fill:none;stroke:var(--sf-grid);stroke-width:2;opacity:.55"/>`;

    // ---- Haus ----
    box(4, 1, 0, 4, 3, 2.6);
    const win = (x0, x1, z0, z1, f) => poly([[x0, 4.001, z0], [x1, 4.001, z0], [x1, 4.001, z1], [x0, 4.001, z1]], f, ST, 1.2);
    const wf = tint("--sf-sun", 16);
    win(4.3, 4.9, 1.1, 2.0, wf); win(6.7, 7.5, 1.1, 2.0, wf); win(5.2, 5.9, 0, 1.7, mix("--sf-tile", "#000", 38));
    poly([[8.001, 1.5, 1.1], [8.001, 2.2, 1.1], [8.001, 2.2, 2.0], [8.001, 1.5, 2.0]], wf, ST, 1.2);
    poly([[8.001, 2.9, 1.1], [8.001, 3.6, 1.1], [8.001, 3.6, 2.0], [8.001, 2.9, 2.0]], wf, ST, 1.2);
    poly([[8, 1, 2.6], [8, 4, 2.6], [8, 2.5, 3.9]], FR, ST, 1.6);
    poly([[4, 4, 2.6], [8, 4, 2.6], [8, 2.5, 3.9], [4, 2.5, 3.9]], mix("--sf-tile", "#fff", 12), "var(--sf-muted)", 1.6);
    const roofPt = (u, v) => [4 + u * 4, 4 - v * 1.5, 2.6 + v * 1.3];
    if (arrays.length) for (let i = 0; i < 4; i++) for (let j = 0; j < 2; j++) {
      const u0 = .07 + i * .235, u1 = u0 + .205, v0 = .12 + j * .43, v1 = v0 + .38;
      poly([roofPt(u0, v0), roofPt(u1, v0), roofPt(u1, v1), roofPt(u0, v1)], tint("--sf-sun", 22), "var(--sf-sun)", 1.5);
    }

    // ---- Speicher-Schränke ----
    const cw = n > 2 ? 1.1 : 1.2, step = n > 2 ? 1.3 : 2.6, cab = [];
    UU.forEach((u, i) => {
      const x = i * step, soc = u.soc != null && u.soc >= 0 ? Math.round(u.soc) : null, pz = !!u.paused;
      box(x, 4.4, 0, cw, 1.0, 1.7, tint("--sf-bat", 26), tint("--sf-bat", 16), tint("--sf-bat", 10), "var(--sf-bat)");
      if (soc != null && !pz) {
        const fill = Math.max(.05, soc / 100) * 1.35;
        poly([[x + .12, 5.401, .15], [x + cw - .12, 5.401, .15], [x + cw - .12, 5.401, .15 + fill], [x + .12, 5.401, .15 + fill]], socCol(soc), "none", 0, 'opacity=".85"');
      }
      cab.push({ x, soc, pz, u });
      const bat = pz || u.bat == null ? 0 : u.bat;
      const doorx = 6.6 - i * .45, lane = 6.1 + (n - 1 - i) * .5, xc = x + cw / 2;
      lanes.push({ pts: [[xc, 5.5, .02], [xc, lane, .02], [doorx, lane, .02], [doorx, 4.15, .02]], col: "--sf-bat", val: bat, at: .34 + .1 * (i % 3) });
    });

    // ---- Linien: Netz, Solar ----
    lanes.push({ pts: [[9.6, 1.7, .02], [8.1, 1.7, .02]], col: "--sf-grid", val: gv });
    arrays.forEach((a, k) => {
      if (k === 0) lanes.push({ pts: [[6, 2.9, 3.8], [6, 3.6, 2.5], [6, 4, 1.8]], col: "--sf-sun", val: a.pv });
      else lanes.push({ pts: a.pole, col: "--sf-sun", val: a.pv });
    });

    // ---- Linien zeichnen (abgerundet, gleichmäßig laufende Punkte) ----
    const scr = a => a.map(p => P(...p));
    const rounded = (A, r = 14) => {
      let s = `M${A[0][0].toFixed(1)} ${A[0][1].toFixed(1)}`;
      for (let i = 1; i < A.length - 1; i++) {
        const p0 = A[i - 1], p1 = A[i], p2 = A[i + 1];
        const l1 = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]), l2 = Math.hypot(p2[0] - p1[0], p2[1] - p1[1]), rr = Math.min(r, l1 / 2, l2 / 2);
        if (rr < 1) { s += `L${p1[0].toFixed(1)} ${p1[1].toFixed(1)}`; continue; }
        const a1 = [p1[0] + (p0[0] - p1[0]) / l1 * rr, p1[1] + (p0[1] - p1[1]) / l1 * rr], a2 = [p1[0] + (p2[0] - p1[0]) / l2 * rr, p1[1] + (p2[1] - p1[1]) / l2 * rr];
        s += `L${a1[0].toFixed(1)} ${a1[1].toFixed(1)}Q${p1[0].toFixed(1)} ${p1[1].toFixed(1)} ${a2[0].toFixed(1)} ${a2[1].toFixed(1)}`;
      }
      const e = A[A.length - 1]; return s + `L${e[0].toFixed(1)} ${e[1].toFixed(1)}`;
    };
    const plen = A => A.reduce((t, p, i) => i ? t + Math.hypot(p[0] - A[i - 1][0], p[1] - A[i - 1][1]) : 0, 0);
    const along = (A, f) => { let t = plen(A) * f; for (let i = 1; i < A.length; i++) { const l = Math.hypot(A[i][0] - A[i - 1][0], A[i][1] - A[i - 1][1]); if (t <= l) return [A[i - 1][0] + (A[i][0] - A[i - 1][0]) * t / l, A[i - 1][1] + (A[i][1] - A[i - 1][1]) * t / l]; t -= l; } return A[A.length - 1]; };
    let base = "", live = "", chips = "";
    for (const x of lanes) {
      const A = scr(x.pts), val = x.val == null ? 0 : x.val, a = Math.abs(val);
      base += `<path d="${rounded(A)}" style="fill:none;stroke:var(${x.col});stroke-width:9;stroke-linecap:round;stroke-linejoin:round;opacity:.13"/>`;
      if (a < 5) continue;
      const Fw = val >= 0 ? A : [...A].reverse(), len = plen(Fw), w = Math.min(7, 3.2 + a / 500), spd = Math.max(55, Math.min(200, 55 + a / 8)), dur = len / spd, cnt = Math.max(2, Math.round(len / 46));
      const dstr = rounded(Fw);
      live += `<path d="${dstr}" style="fill:none;stroke:var(${x.col});stroke-width:${w.toFixed(1)};stroke-linecap:round;stroke-linejoin:round;opacity:.45"/>`;
      for (let i = 0; i < cnt; i++) {
        if (reduced()) { const [qx, qy] = along(Fw, (i + .5) / cnt); live += `<circle cx="${qx.toFixed(1)}" cy="${qy.toFixed(1)}" r="${(w / 2 + 1.6).toFixed(1)}" style="fill:var(${x.col})"/>`; }
        else live += `<circle r="${(w / 2 + 1.7).toFixed(1)}" style="fill:var(${x.col})"><animateMotion dur="${dur.toFixed(2)}s" begin="${(-i * dur / cnt).toFixed(2)}s" repeatCount="indefinite" path="${dstr}"/></circle>`;
      }
      const [cx, cy] = along(A, x.at || .5), t = fmt(a) + " W", tw = (t.length * 7.4 + 16) * m;
      chips += `<g><rect x="${(cx - tw / 2).toFixed(1)}" y="${(cy - 12 * m).toFixed(1)}" width="${tw.toFixed(1)}" height="${(24 * m).toFixed(1)}" rx="${12 * m}" style="fill:var(--sf-card);stroke:var(${x.col});stroke-opacity:.6;stroke-width:1.4"/><text x="${cx.toFixed(1)}" y="${(cy + 4.6 * m).toFixed(1)}" text-anchor="middle" style="font-size:${(13 * m).toFixed(1)}px" class="sf-c">${t}</text></g>`;
    }

    // ---- Beschriftungen ----
    const card = (p, l1, l2, col, lift = 0) => {
      const [x, y0] = P(...p), y = y0 - lift, w = (Math.max(l1.length, l2.length) * 8 + 26) * m, h = 44 * m;
      return `<g><rect x="${(x - w / 2).toFixed(1)}" y="${(y - h / 2).toFixed(1)}" width="${w.toFixed(1)}" height="${h.toFixed(1)}" rx="${12 * m}" style="fill:var(--sf-card);stroke:var(${col});stroke-width:1.5"/>
        <text x="${x.toFixed(1)}" y="${(y - 4 * m).toFixed(1)}" text-anchor="middle" class="sf-hl" style="font-size:${(11.5 * m).toFixed(1)}px;fill:var(${col})">${l1}</text>
        <text x="${x.toFixed(1)}" y="${(y + 14 * m).toFixed(1)}" text-anchor="middle" class="sf-hv" style="font-size:${(15 * m).toFixed(1)}px">${l2}</text></g>`;
    };
    let lab = "";
    cab.forEach((c, i) => {
      const [bv, bt] = batState(c.u, c.u.bat);
      lab += card([c.x + cw / 2, 4.9, 1.75], esc(clip(names[i], 9)) + (c.soc != null ? " · " + c.soc + " %" : ""), bt ? bv + " " + bt : bv, "--sf-bat", (n > 2 ? (2 - i % 3) * 50 * m : 0));
    });
    arrays.forEach((a, k) => { lab += card(k === 0 ? [6, 2.5, 5.0] : a.world.map((v, j) => j === 2 ? v + .9 : v), "SOLAR" + (arrays.length > 1 ? " " + esc(clip(a.name, 8)) : ""), wl(a.pv), "--sf-sun"); });
    lab += card([9.75, 1.55, 4.3], "NETZ", fmt(Math.abs(grid)) + " W" + (grid >= 5 ? " Bezug" : grid <= -5 ? " Einspeisung" : ""), "--sf-grid");
    lab += card([5.6, 4.0, 1.5], "HAUS", wl(d.house), "--sf-home");
    // Sonne
    const [sx, sy] = P(8.6, .2, 5.4), sun = pvTotal != null && pvTotal >= 5, sc = sun ? "var(--sf-sun)" : "var(--sf-muted)";
    const rays = [0, 45, 90, 135, 180, 225, 270, 315].map(a => `<line x1="${(sx + 22 * Math.cos(a * Math.PI / 180)).toFixed(1)}" y1="${(sy + 22 * Math.sin(a * Math.PI / 180)).toFixed(1)}" x2="${(sx + 30 * Math.cos(a * Math.PI / 180)).toFixed(1)}" y2="${(sy + 30 * Math.sin(a * Math.PI / 180)).toFixed(1)}" style="stroke:${sc};stroke-width:3;stroke-linecap:round"/>`).join("");
    const sunSvg = `<g opacity="${sun ? 1 : .35}"><circle cx="${sx.toFixed(1)}" cy="${sy.toFixed(1)}" r="16" style="fill:${sc}"/>${rays}</g>`;
    // Ansichtsfenster: bei schmaler Anzeige etwas enger
    const vb = "60 0 900 625";
    return `<svg viewBox="${vb}" role="img" aria-label="Energiefluss als Haus">${CSS}<style>.sf-hl{font-weight:700;letter-spacing:.04em}.sf-hv{font-weight:800;fill:var(--sf-fg)}</style>${sunSvg}${ob}${base}${live}${lab}${chips}</svg>`;
  }

  const FLOW_DEF = { view: "flow", size: "auto", layout: "total", total: true, solar: true, bat: true, grid: true, house: true, grid_pos: "mid", passthrough: true, order: [] };
  /* d: {pv, house, bat (+ entlädt), grid (+ Bezug), soc, f:{sh, sb, bh, gh}, units?:[{name, soc, kwh, pv, bat}],
         fl?:{layout: total|pairs|compact, total, solar, bat, grid, house, grid_pos: mid|side, order:[Namen]}} */
  function flow(d) {
    const o = Object.assign({}, FLOW_DEF, d.fl || {});
    let U = (d.units || []).filter(u => u && u.name && !u.off && u.soc != null && u.soc >= 0);
    const ord = Array.isArray(o.order) ? o.order : [];
    if (ord.length) {
      const rk = u => { const i = ord.indexOf(u.name); return i < 0 ? 999 : i; };
      U = U.map((u, i) => [u, i]).sort((a, b) => rk(a[0]) - rk(b[0]) || a[1] - b[1]).map(x => x[0]);
    }
    if (o.view === "house") return flowHouse(d, U, o);
    if (o.layout !== "compact") {
      if (U.length === 2) return flowPairs(d, U, o);
      if (U.length > 2) return flowMulti(d, U, o);
    }
    const f = d.f || {}, drop = {};
    if (!o.solar) { drop.sh = 1; drop.sb = 1; }
    if (!o.bat) { drop.sb = 1; drop.bh = 1; }
    if (!o.grid) drop.gh = 1;
    if (!o.house) { drop.sh = 1; drop.bh = 1; drop.gh = 1; }
    const W = flowW(d, o), ex = W - 640;
    const sx = x => x <= 200 ? x : x >= 400 ? x + ex : x + ex / 2;      // linke Spalte bleibt, rechte rückt nach außen, Mitte mittig
    const P = k => ({ ...T[k], x: k === "bat" ? T[k].x : k === "grid" ? T[k].x + ex : T[k].x + ex / 2 });
    const lines = Object.keys(L).filter(k => !drop[k]).map(k => ({ pts: L[k].pts.map(([x, y]) => [sx(x), y]), col: L[k].col, val: f[k] }));
    const bat = d.bat, grid = d.grid == null ? 0 : d.grid, soc = d.soc != null && d.soc >= 0 ? Math.round(d.soc) : null;
    const u0 = o.layout === "compact" ? { locked: d.limited, full: U.length > 0 && U.every(u => u.full) } : (d.units || [])[0] || { locked: d.limited };
    const [bv1, bt1] = batState(u0, bat);
    const batSub = bt1 === "entlädt" ? "gibt ab" : bt1;
    const gridSub = grid >= 5 ? "Bezug" : grid <= -5 ? "Einspeisung" : "ausgeglichen";
    const kw = kwhTxt(d.kwh);
    const socPart = soc != null ? soc + " %" + (kw ? " · " + kw : "") : kw;
    return `<svg viewBox="0 0 ${W} 340" role="img" aria-label="Energiefluss">${CSS}${drawLines(lines)}
      ${o.solar ? tile("sun", "Solar", wl(d.pv), d.pv != null && d.pv < 5 ? "keine Sonne" : "", "--sf-sun", ICON.sun("var(--sf-sun)"), P("sun")) : ""}
      ${o.bat ? tile("bat", "Speicher", bv1, batSub ? batSub + (socPart ? " · " + socPart : "") : socPart, "--sf-bat", ICON.bat("var(--sf-bat)", soc), P("bat")) : ""}
      ${o.grid ? tile("grid", "Netz", wl(Math.abs(grid)), gridSub, "--sf-grid", ICON.grid("var(--sf-grid)"), P("grid")) : ""}
      ${o.house ? tile("home", "Haus", wl(d.house), d.house != null ? "Verbrauch" : "", "--sf-home", ICON.home("var(--sf-home)"), P("home")) : ""}
    </svg>`;
  }

  /* Überschrift aus den echten Flüssen; nur ohne Batterie-Messwert aus dem Sollwert.
     d: {f, grid, soc, bat, target, limited} */
  function headline(d) {
    const f = d.f, s = d.soc != null && d.soc >= 0 ? ` · mittlerer Ladestand ${Math.round(d.soc)} %` + (d.cap ? ` (${nf1(d.kwh)} von ${Number(d.cap).toLocaleString("de-DE", { maximumFractionDigits: 1 })} kWh)` : "") : "";
    const g = d.grid == null ? 0 : d.grid;
    const gs = Math.abs(g) < 30 ? "Netzbezug nahe null" : g > 0 ? `Netzbezug ${fmt(g)} W` : `Einspeisung ${fmt(-g)} W`;
    // Überschuss einer vollen Anlage lädt eine andere (AC-Laden): Speicher lädt mit mehr, als seine eigenen Module liefern
    const UU = (d.units || []).filter(u => u && u.name && !u.off && !u.paused), nn = shortNames(UU.map(u => u.name));
    const from = UU.findIndex(u => u.full && (u.pv || 0) >= 5);
    const to = UU.findIndex(u => !u.full && u.bat != null && -u.bat >= 5 && -u.bat > (u.pv || 0) + 5);
    if (from >= 0 && to >= 0 && from !== to)
      return [`Überschuss von ${nn[from]} lädt ${nn[to]} mit ${fmt(-UU[to].bat - (UU[to].pv || 0))} W`, (d.fl && d.fl.passthrough === false ? "" : "durchgereicht, kein Mehrverbrauch · ") + gs + s];
    if (f && f.bh != null && d.bat != null) {
      const sh = f.sh >= 5, sb = f.sb >= 5, bh = f.bh >= 5, gh = f.gh >= 5;
      if (sh && sb) return ["Solar versorgt dein Haus und lädt den Speicher", gs + s];
      if (sh && bh && gh) return ["Solar, Speicher und Netz versorgen dein Haus", `Der Verbrauch ist höher als die Abgabe der Speicher${s}`];
      if (sh && bh) return ["Solar und Speicher versorgen dein Haus", gs + s];
      if (bh && gh) return ["Speicher und Netz versorgen dein Haus", `Speicher ${fmt(f.bh)} W · Netz ${fmt(f.gh)} W${s}`];
      if (bh) return [`Der Speicher versorgt dein Haus mit ${fmt(f.bh)} W`, gs + s];
      if (sb) return gh
        ? [`Solar lädt den Speicher mit ${fmt(f.sb)} W`, `Haus bezieht ${fmt(f.gh)} W aus dem Netz${s}`]
        : [`Überschuss lädt den Speicher mit ${fmt(f.sb)} W`, (Math.abs(g) < 30 ? "Einspeisung wird vermieden" : gs) + s];
      if (sh && gh) return ["Solar und Netz versorgen dein Haus", gs + s];
      if (sh) return ["Solar versorgt dein Haus", gs + s];
      if (f.bh <= -5) return [`Der Speicher wird aus dem Netz geladen (${fmt(-f.bh)} W)`, gs + s];
      if (gh) {
        if (d.limited) return ["Speicher an der Entladegrenze, das Netz versorgt dein Haus", gs + s];
        return ["Das Netz versorgt dein Haus", (d.target > 0 ? `Die Speicher liefern noch nichts (Sollwert ${fmt(d.target)} W)` : gs) + s];
      }
      return ["Alles ausgeglichen", `Gerade ist keine Regelung nötig${s}`];
    }
    const t = d.target == null ? 0 : d.target;
    if (t > 0) return [`Die Speicher versorgen dein Haus mit ${fmt(t)} W`, `Netzbezug wird auf nahe null geregelt${s}`];
    if (t < 0) return [`Überschuss lädt die Speicher mit ${fmt(-t)} W`, `Einspeisung wird vermieden${s}`];
    return ["Alles ausgeglichen", `Gerade ist keine Regelung nötig${s}`];
  }

  /* Glatte Kurve durch die Punkte (Catmull-Rom als Bézier), Werte ohne Überschwingen unter 0 */
  function smooth(P, floorY) {
    if (P.length < 2) return "";
    let s = `M${P[0][0].toFixed(1)} ${P[0][1].toFixed(1)}`;
    for (let i = 0; i < P.length - 1; i++) {
      const p0 = P[i - 1] || P[i], p1 = P[i], p2 = P[i + 1], p3 = P[i + 2] || p2;
      const c1x = p1[0] + (p2[0] - p0[0]) / 6, c1y = Math.min(floorY, p1[1] + (p2[1] - p0[1]) / 6);
      const c2x = p2[0] - (p3[0] - p1[0]) / 6, c2y = Math.min(floorY, p2[1] - (p3[1] - p1[1]) / 6);
      s += `C${c1x.toFixed(1)} ${c1y.toFixed(1)} ${c2x.toFixed(1)} ${c2y.toFixed(1)} ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
    }
    return s;
  }

  /* d: {t:[Sekunden]|null, pv:[W], house:[W]}; Werte im Abstand von 5 Minuten, das letzte ist „jetzt“ */
  function trend(d) {
    const pv = d.pv || [], hs = d.house || [], bt = d.bat || [], n = Math.max(pv.length, hs.length);
    if (n < 3) return "";
    const end = Date.now() / 1000;
    const ts = d.t && d.t.length === n ? d.t : Array.from({ length: n }, (_, i) => end - (n - 1 - i) * 300);
    const t1 = Math.max(ts[n - 1], ts[0] + 600), t0 = Math.max(ts[0], t1 - 86400);
    const X0 = 44, X1 = 626, Y0 = 18, Y1 = 150;
    const hasBat = bt.some(v => v != null && v > 5);
    const comb = pv.map((v, i) => (v || 0) + (bt[i] || 0));
    const all = [...pv, ...hs, ...(hasBat ? comb : [])].filter(v => v != null);
    const mx = Math.max(...all, 100);
    const step = [250, 500, 1000, 2000, 2500, 5000, 10000].find(s => mx / s <= 3.2) || 10000;
    const top = Math.ceil(mx / step) * step;
    const X = t => X0 + (t - t0) / (t1 - t0) * (X1 - X0), Y = v => Y1 - Math.min(v, top) / top * (Y1 - Y0);
    const pts = arr => { const o = []; let last = 0; for (let i = 0; i < n; i++) { if (ts[i] < t0) continue; if (arr[i] != null) last = arr[i]; o.push([X(ts[i]), Y(last)]); } return o; };
    const P = pts(pv), H = pts(hs), BT = hasBat ? pts(comb) : null;
    let grid = "";
    for (let v = 0; v <= top; v += step) {
      const y = Y(v).toFixed(1), lab = v === 0 ? "0" : v >= 1000 ? (v / 1000).toLocaleString("de-DE") + "k" : String(v);
      grid += `<path d="M${X0} ${y}H${X1}" class="sf-g"${v ? ' stroke-dasharray="2 5"' : ""}/><text x="${X0 - 8}" y="${(+y + 4).toFixed(1)}" text-anchor="end" class="sf-a">${lab}</text>`;
    }
    const span = (t1 - t0) / 3600, every = span <= 4 ? 1 : span <= 12 ? 3 : 6;
    let ticks = "";
    const first = new Date(t0 * 1000); first.setMinutes(0, 0, 0);
    for (let h = new Date(first.getTime() + 3600000); h.getTime() / 1000 < t1 - 900; h = new Date(h.getTime() + 3600000)) {
      if (h.getHours() % every) continue;
      const x = X(h.getTime() / 1000);
      if (x < X0 + 14 || x > X1 - 22) continue;
      ticks += `<text x="${x.toFixed(1)}" y="${Y1 + 20}" text-anchor="middle" class="sf-a">${h.getHours()} Uhr</text>`;
    }
    const area = P.length > 1 ? `${smooth(P, Y1)}L${P[P.length - 1][0].toFixed(1)} ${Y1}L${P[0][0].toFixed(1)} ${Y1}Z` : "";
    const nowP = P[P.length - 1];
    const batArea = BT && BT.length > 1 ? `${smooth(BT, Y1)}${smooth([...P].reverse(), Y1).replace(/^M/, "L")}Z` : "";
    return `<svg viewBox="0 0 640 196" role="img" aria-label="Verlauf der letzten Stunden: Solar, Speicher und Haus">${CSS}${grid}${ticks}
      ${batArea ? `<path d="${batArea}" style="fill:var(--sf-bat);fill-opacity:.28;stroke:var(--sf-bat);stroke-opacity:.7;stroke-width:1.2"/>` : ""}
      <path d="${area}" style="fill:var(--sf-sun);fill-opacity:.2;stroke:none"/>
      <path d="${smooth(P, Y1)}" class="sf-o" style="stroke:var(--sf-sun);stroke-width:2.4;stroke-linejoin:round"/>
      <path d="${smooth(H, Y1)}" class="sf-o" style="stroke:var(--sf-home);stroke-width:2.4;stroke-linejoin:round"/>
      <circle cx="${nowP[0].toFixed(1)}" cy="${nowP[1].toFixed(1)}" r="4.5" style="fill:var(--sf-sun);stroke:var(--sf-card);stroke-width:2"/>
      <g transform="translate(${X0} 186)"><circle cx="5" cy="-4" r="5" style="fill:var(--sf-sun)"/><text x="16" y="0" class="sf-c">Solar</text>
      <circle cx="78" cy="-4" r="5" style="fill:var(--sf-home)"/><text x="89" y="0" class="sf-c">Haus</text>
      ${batArea ? `<circle cx="140" cy="-4" r="5" style="fill:var(--sf-bat)"/><text x="151" y="0" class="sf-c">aus Speichern</text>` : ""}</g></svg>`;
  }


  /* ---- Zählerreihe: Tagesverbrauch, eigene Zähler (Strom, Wasser, Gas …), optional Solar und Netz heute ---- */
  const esc = t => String(t ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const MCOL = { zaehl: "#e8548a", water: "#3b8eea", water2: "#34b36b", sun: "var(--sf-sun)", bat: "var(--sf-bat)", grid: "var(--sf-grid)", home: "var(--sf-home)", accent: "var(--sf-sun)" };
  const MI = {
    haus: '<path d="M3.5 11 12 4l8.5 7M6 9.5V20h12V9.5M10 20v-5h4v5" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round" stroke-linecap="round"/>',
    zaehler: '<rect x="3" y="5.5" width="18" height="13" rx="3" fill="none" stroke="currentColor" stroke-width="1.9"/><path d="M8 9.5v5M8 9.5 6.6 10.6M13 9.5h2.4l-2.4 5h2.6M17 9.5v5" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>',
    wasser: '<path d="M12 3.2c3.6 4.5 6 7.3 6 10.3a6 6 0 0 1-12 0c0-3 2.4-5.8 6-10.3z" fill="currentColor"/>',
    blitz: '<path d="M13.2 2.5 5.5 13.6h5.3L9.8 21.5 18.5 9.8h-5.4z" fill="currentColor"/>',
    gas: '<path d="M12 3c1 3.5 5 5.5 5 10a5 5 0 0 1-10 0c0-2 1-3.5 2-4.5.3 1.5 1 2.3 1.8 2.5C10.5 8.5 11 5.5 12 3z" fill="currentColor"/>',
    waerme: '<path d="M10 14.2V5a2 2 0 0 1 4 0v9.2a4 4 0 1 1-4 0z" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"/><circle cx="12" cy="16.5" r="1.6" fill="currentColor"/>',
    sonne: '<g fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 3v2.5M12 18.5V21M3 12h2.5M18.5 12H21M5.6 5.6l1.8 1.8M16.6 16.6l1.8 1.8M18.4 5.6l-1.8 1.8M7.4 16.6l-1.8 1.8"/></g>',
    netz: '<g fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2.5v19M7 21.5l5-12.5 5 12.5M8 9h8M9.5 15h5"/></g>',
    akku: '<g fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="2.8" y="6.5" width="16.4" height="11" rx="3"/><path d="M21.6 10.5v3M7 12h6.4"/></g>'
  };
  const MCSS = `<style>
    .sfm-w{container-type:inline-size}
    .sfm{display:grid;gap:10px;font-family:inherit}
    .sfm.even{grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}
    .sfm.big{grid-template-columns:minmax(0,.8fr) minmax(0,1.6fr)}
    .sfm-r{display:grid;gap:10px;grid-template-columns:minmax(0,1fr)}
    .sfm-t{cursor:pointer;display:flex;flex-direction:column;align-items:flex-start;gap:5px;border-radius:14px;padding:12px 14px;min-width:0;background:var(--sf-tile,rgba(128,128,128,.12))}
    .sfm-h{display:grid}
    .sfm-h .sfm-t{justify-content:center;gap:8px;padding:16px;min-width:0;background:linear-gradient(135deg,color-mix(in srgb,var(--sf-sun) 18%,var(--sf-tile,transparent)),var(--sf-tile,transparent) 85%)}
    .sfm-hd{display:flex;align-items:center;gap:9px;min-width:0;width:100%}
    .sfm-ic{flex:none;width:30px;height:30px;border-radius:10px;display:grid;place-items:center;background:color-mix(in srgb,var(--c) 16%,transparent);color:var(--c)}
    .sfm-h .sfm-ic{width:38px;height:38px;border-radius:12px}
    .sfm-ic svg{width:18px;height:18px}.sfm-h .sfm-ic svg{width:22px;height:22px}
    .sfm-n{font-size:13px;line-height:1.25;color:var(--sf-muted);font-weight:600;min-width:0;overflow-wrap:break-word;hyphens:auto}
    .sfm-v{font-size:19px;font-weight:800;letter-spacing:-.01em;color:var(--sf-fg);white-space:nowrap}
    .sfm-h .sfm-v{font-size:28px}
    .sfm-v small{font-size:12.5px;font-weight:600;color:var(--sf-muted);margin-left:3px}
    .sfm-d{font-size:12px;color:var(--sf-muted);margin-top:1px;white-space:normal;overflow-wrap:break-word}
    .sfm-d b{color:var(--sf-ok);font-weight:700}
    .sfm-c{font-size:12px;color:var(--sf-muted);margin-top:1px;white-space:normal;overflow-wrap:break-word}
    .sfm-c i{font-style:normal;font-weight:700}.sfm-c .cg{color:var(--sf-ok)}.sfm-c .cb{color:var(--sf-bad)}
    .sfm.even .sfm-h .sfm-t{height:100%}
    .sfm.big .sfm-r .sfm-t{flex-direction:row;align-items:center;justify-content:space-between;gap:12px}
    .sfm.big .sfm-r .sfm-hd{width:auto;flex:1}
    .sfm.big .sfm-r .sfm-val{text-align:right;flex:none}
    .sfm.big .sfm-r .sfm-v{font-size:18px}
    @container (max-width:560px){
      .sfm.big{grid-template-columns:minmax(0,1fr)}
      .sfm.big .sfm-h .sfm-t{flex-direction:row;align-items:center;justify-content:space-between;gap:12px;padding:12px 14px;height:auto}
      .sfm.big .sfm-h .sfm-hd{width:auto;flex:1}.sfm.big .sfm-h .sfm-val{text-align:right;flex:none}
      .sfm.big .sfm-h .sfm-v{font-size:24px}
      .sfm.even .sfm-h .sfm-t{padding:12px 14px;gap:5px}.sfm.even .sfm-h .sfm-v{font-size:22px}
      .sfm.even .sfm-h .sfm-ic{width:30px;height:30px;border-radius:10px}.sfm.even .sfm-h .sfm-ic svg{width:18px;height:18px}
      .sfm.even{grid-template-columns:repeat(2,minmax(0,1fr))}
    }</style>`;
  const nf = (v, dec) => v == null || isNaN(v) ? "–" : Number(v).toLocaleString("de-DE", { minimumFractionDigits: dec, maximumFractionDigits: dec });
  const nd = v => Number(v).toLocaleString("de-DE", { minimumFractionDigits: 0, maximumFractionDigits: 2 });

  /* Wasserzähler: Tagesverbrauch in Litern (Zählerstand bleibt in m³) */
  const isWater = m => /^m[³3]$/i.test(String(m.unit || "").trim()) && (m.icon === "wasser" || /wasser|water/i.test(String(m.name || "") + " " + String(m.entity || "")));
  const dayText = m => {
    if (isWater(m)) {
      const l = Math.round(m.day * 1000);
      return `<b>${l >= 0 ? "+" : ""}${l.toLocaleString("de-DE")} l</b> heute`;
    }
    return `<b>${m.day >= 0 ? "+" : ""}${nd(m.day)} ${esc(m.unit)}</b> heute`;
  };

  /* Vergleich mit gestern: cur = Wert heute, c = {y, full}, mode = same (bis zur gleichen Uhrzeit, sonst ganzer Tag) | full | off.
     good: +1 = mehr ist gut (grün), -1 = mehr ist schlecht (rot), 0 = neutral. fmt formatiert den Vergleichswert. */
  function cmpLine(cur, c, mode, good, fmtv) {
    if (mode === "off" || !c || cur == null) return "";
    let ref = mode === "full" ? c.full : c.y, lab = mode === "full" ? "gestern gesamt" : "gestern";
    if (ref == null && mode !== "full" && c.full != null) { ref = c.full; lab = "gestern gesamt"; }
    if (ref == null) return "";
    const diff = cur - ref;
    let delta = "";
    if (ref > 0) {
      const pc = Math.round(diff / ref * 100);
      if (Math.abs(pc) < 1) delta = ` · <i>≈ gleich</i>`;
      else {
        const cls = good === 0 ? "" : (diff > 0) === (good > 0) ? "cg" : "cb";
        delta = ` · <i class="${cls}">${diff > 0 ? "▲" : "▼"} ${Math.abs(pc).toLocaleString("de-DE")} %</i>`;
      }
    }
    return `<div class="sfm-c">${lab} ${fmtv(ref)}${delta}</div>`;
  }

  /* d: {items:[{name,value,dec,unit,icon,color,day,cmp}], today:{house,pv,imp,cmp}|null, show_day, extra, layout, compare} */
  function meters(d) {
    const all = [];
    const cm = d.compare === "full" || d.compare === "off" ? d.compare : "same";
    const t = d.today;
    if (d.show_day !== false && t && t.house != null)
      all.push({ k: "day", n: "Tagesverbrauch", v: nf(t.house, 1), u: "kWh", ic: "haus", c: "accent", sub: "Haus heute", hero: true,
        cmp: cmpLine(t.house, t.cmp && t.cmp.house, cm, 0, v => nf(v, 1) + " kWh") });
    (d.items || []).forEach(m => all.push({ k: "m:" + (m.entity || ""), n: m.name, v: nf(m.value, m.dec || 0), u: m.unit, ic: m.icon, c: m.color,
      sub: m.day != null && m.value != null ? dayText(m) : "",
      cmp: m.day != null && m.value != null ? cmpLine(m.day, m.cmp, cm, 0, v => isWater(m) ? Math.round(v * 1000).toLocaleString("de-DE") + " l" : nd(v) + " " + esc(m.unit)) : "" }));
    if (d.extra && t) {
      if (t.pv != null) all.push({ k: "pv", n: "Solarertrag heute", v: nf(t.pv, 1), u: "kWh", ic: "sonne", c: "sun", sub: "", cmp: cmpLine(t.pv, t.cmp && t.cmp.pv, cm, 1, v => nf(v, 1) + " kWh") });
      if (t.imp != null) all.push({ k: "imp", n: "Netzbezug heute", v: nf(t.imp, 1), u: "kWh", ic: "netz", c: "grid", sub: "", cmp: cmpLine(t.imp, t.cmp && t.cmp.imp, cm, -1, v => nf(v, 1) + " kWh") });
      if (t.bat != null) all.push({ k: "bat", n: "Aus Speichern heute", v: nf(t.bat, 1), u: "kWh", ic: "akku", c: "bat", sub: t.chg != null ? nf(t.chg, 1) + " kWh geladen" : "", cmp: cmpLine(t.bat, t.cmp && t.cmp.bat, cm, 0, v => nf(v, 1) + " kWh") });
    }
    // eigene Reihenfolge: genannte Kacheln zuerst, der Rest in Standardreihenfolge
    const ord = Array.isArray(d.order) ? d.order : [];
    const rank = x => { const i = ord.indexOf(x.k); return i < 0 ? ord.length + all.indexOf(x) : i; };
    const seq = all.slice().sort((x, y) => rank(x) - rank(y));
    if (!seq.length) return "";
    const first = seq[0];
    const hero = first.hero ? first : null;
    const tiles = hero ? seq.slice(1) : seq;
    const tile = x => `<div class="sfm-t" data-tile="${esc(x.k)}" role="button" tabindex="0" style="--c:${MCOL[x.c] || MCOL.zaehl}"><div class="sfm-hd"><span class="sfm-ic"><svg viewBox="0 0 24 24" aria-hidden="true">${MI[x.ic] || MI.zaehler}</svg></span><span class="sfm-n">${esc(x.n)}</span></div>
      <div class="sfm-val"><div class="sfm-v">${x.v}<small>${esc(x.u)}</small></div>${x.sub ? `<div class="sfm-d">${x.sub}</div>` : ""}${x.cmp || ""}</div></div>`;
    if (hero && tiles.length && d.layout !== "even")
      return `${MCSS}<div class="sfm-w"><div class="sfm big"><div class="sfm-h">${tile(hero)}</div><div class="sfm-r">${tiles.map(tile).join("")}</div></div></div>`;
    return `${MCSS}<div class="sfm-w"><div class="sfm even">${(hero ? [hero, ...tiles] : tiles).map(x => x === hero ? `<div class="sfm-h">${tile(x)}</div>` : tile(x)).join("")}</div></div>`;
  }

  return { flow, trend, headline, wl, meters, isWater };
})();
/*FLOW-END*/
  /* Energiefluss: Einstellungen aus dem Add-on, Optionen der Karte gehen vor */
  function flowCfg(a, c) {
    const fl = { ...(a.flow_cfg || {}) };
    c = c || {};
    if (["total", "pairs", "compact"].includes(c.flow_layout)) fl.layout = c.flow_layout;
    if (["mid", "side"].includes(c.flow_grid_pos)) fl.grid_pos = c.flow_grid_pos;
    if (Array.isArray(c.flow_hide)) c.flow_hide.forEach(k => { if (["total", "solar", "bat", "grid", "house"].includes(k)) fl[k] = false; });
    if (["auto", "compact", "large"].includes(c.flow_size)) fl.size = c.flow_size;
    if (typeof c.flow_passthrough === "boolean") fl.passthrough = c.flow_passthrough;
    if (Array.isArray(c.flow_order) && c.flow_order.length) fl.order = c.flow_order;
    return fl;
  }
  function flowData(a, c) {
    const f = a.flows;
    return {
      fl: flowCfg(a, c), w: c && c._w, pv: num(a.pv_w), house: num(a.house_w), bat: num(a.battery_w), grid: num(a.grid_w) ?? 0, soc: num(a.avg_soc), target: num(a.target_w),
      kwh: num(a.kwh), cap: num(a.cap_kwh),
      limited: !!a.limited,
      units: (a.units || []).map(u => ({ name: u.name, soc: u.soc, kwh: u.kwh, pv: u.pv, bat: u.bat, locked: !!u.locked, full: !!u.full, paused: !!u.paused })),
      f: f ? { sh: f.solar_house, sb: f.solar_battery, bh: f.battery_house, gh: f.grid_house } : null };
  }
  const flowSVG = (a, c) => SF.flow(flowData(a, c));

  function headline(a, state) {
    const t = num(a.target_w) ?? 0, soc = a.avg_soc, prefix = a.mode === "test" ? "Im Test: " : "";
    if (a.mode === "stopped") return ["SOLASI ist gestoppt", a.stop_reason ? `${a.stop_reason}. Die Speicher laufen im eigenen Modus.` : "Die Speicher laufen im eigenen Modus."];
    if (a.mode === "observe") return ["SOLASI beobachtet nur", "Die Regelung ist aus, es wird nichts gesendet."];
    if (a.meter_ok === false) return ["Zähler ohne Meldung", "Zur Sicherheit gehen die Speicher auf 0 W."];
    const [h, sub] = SF.headline(flowData(a));
    return [prefix + h, sub];
  }

  function trendSVG(a) {
    const svg = SF.trend(a.trend || {});
    return svg ? `<div class="trend"><div class="eyebrow">Verlauf</div>${svg}</div>` : "";
  }

  function ago(ts) {
    const d = (Date.now() - new Date(ts).getTime()) / 1000;
    if (!isFinite(d) || d < 0) return "";
    return d < 90 ? `vor ${Math.round(d)} s` : d < 5400 ? `vor ${Math.round(d / 60)} min` : "länger her";
  }

  const socColor = s => s == null ? "var(--secondary-text-color)" : s >= 50 ? "var(--sc-ok)" : s >= 20 ? "var(--sc-warn)" : "var(--sc-bad)";

  class SOLASICard extends HTMLElement {
    constructor() { super(); this.attachShadow({ mode: "open" }); this._key = null; }

    /* Wirksame Optionen: Aussehen aus dem Add-on, Optionen der Karte selbst gehen vor */
    _eff(ac) {
      const o = { ...this._cfg };
      if (ac && typeof ac === "object") for (const k of CARD_KEYS) if (!(k in (this._raw || {})) && ac[k] !== undefined) o[k] = ac[k];
      return o;
    }

    setConfig(config) {
      this._raw = { ...(config || {}) };
      this._cfg = { entity: "sensor.solasi", title: "SOLASI", show_headline: true, show_batteries: true,
                    show_surplus: true, show_tags: true, size: "large", show_trend: true, show_meters: true, meters_layout: "big", show_kill: true,
                    tap_open: true, accent: "", gradient: true, ...(config || {}) };
      if (this._cfg.debug) window.__solasiDebugCard = true;
      this._key = null;
      this._render();
    }

    set hass(hass) {
      this._hass = hass;
      const st = hass && hass.states ? hass.states[this._cfg.entity] : null;
      const key = st ? `${st.state}|${st.last_updated}` : "none";
      if (key === this._key) return;
      if (Date.now() - lastScrollAt < 250) {            // nicht mitten im Scrollen neu zeichnen
        if (!this._defer) this._defer = setTimeout(() => { this._defer = null; this._key = null; this.hass = this._hass; }, 300);
        return;
      }
      this._key = key; this._render();
    }

    getCardSize() {                       // echte Höhe melden, damit HA das Layout nicht nachträglich verschiebt
      const h = this._minH || 0;
      return h ? Math.max(3, Math.round(h / 50)) : 8;
    }
    static getStubConfig() { return { entity: "sensor.solasi" }; }
    static getConfigElement() { return document.createElement("solasi-card-editor"); }

    _render() {
      if (!this._cfg) return;
      const st = this._hass && this._hass.states ? this._hass.states[this._cfg.entity] : null;
      const c = this._eff(st && st.attributes && st.attributes.card_cfg);
      let body, ready = false;
      if (!this._hass) {
        body = `<div class="msg">Lade …</div>`;
      } else if (!st) {
        body = this._goodBody ? `<div class="stale">${this._goodBody}</div>` : `<div class="msg">Entität <b>${esc(c.entity)}</b> nicht gefunden.<br>Läuft das SOLASI-Add-on?</div>`;
      } else if (st.state === "unavailable" || st.state === "unknown") {
        body = this._goodBody ? `<div class="stale">${this._goodBody}</div>` : `<div class="msg">SOLASI ist gerade nicht erreichbar.</div>`;
      } else {
        const a = st.attributes || {};
        const [hl, sub] = headline(a, st.state);
        const pill = { live: ["Live", "live"], test: ["Testmodus", "test"], observe: ["Beobachten", "observe"], stopped: ["Gestoppt", "stopped"] }[a.mode] || [st.state, ""];
        const compact = c.size === "compact";
        const g = num(a.grid_w) ?? 0, b = num(a.battery_w);
        const tiles = `<div class="tiles">
          <div class="tile sun"><div class="n">Solar</div><div class="v">${W(a.pv_w)}</div></div>
          <div class="tile home"><div class="n">Haus</div><div class="v">${W(a.house_w)}</div></div>
          <div class="tile bat"><div class="n">Speicher</div><div class="v">${b == null ? "–" : W(Math.abs(b))}</div></div>
          <div class="tile grid"><div class="n">Netz</div><div class="v">${W(Math.abs(g))}</div></div></div>`;
        const mc = a.meters_cfg || {};
        const mhtml = c.show_meters ? SF.meters({ items: a.meters || [], today: a.today, show_day: mc.show_day, extra: mc.extra, layout: c.meters_layout, compare: ["off", "same", "full"].includes(c.meters_compare) ? c.meters_compare : mc.compare, order: Array.isArray(c.meters_order) && c.meters_order.length ? c.meters_order : mc.order }) : "";
        const parts = {
          meters: mhtml ? `<div class="mwrap">${mhtml}</div>` : "",
          headline: c.show_headline ? `<div class="headline">${esc(hl)}</div><div class="sub">${esc(sub)}</div>` : "",
          flow: flowSVG(a, { ...c, _w: Math.max(0, (this.offsetWidth || 0) - 32 - (c.gradient !== false ? 34 : 0)) }),
          trend: c.show_trend ? trendSVG(a) : "",
          batteries: c.show_batteries && (a.units || []).length ? `<div class="units">${a.units.map(u => {
            const soc = u.soc < 0 ? null : u.soc;
            return `<div class="unit"><div class="n">${esc(u.name)}</div><div class="s">${soc == null ? "–" : soc + " %"}${u.kwh != null ? ` · ${Number(u.kwh).toLocaleString("de-DE", { maximumFractionDigits: 1 })} von ${Number(u.cap).toLocaleString("de-DE", { maximumFractionDigits: 1 })} kWh` : ""}</div>
              <div class="bar"><div style="width:${soc || 0}%;background:${socColor(soc)}"></div></div>
              <div class="d">${u.pv != null ? "Solar " + Math.round(u.pv) + " W · " : ""}${u.obs ? "beobachtet" : Math.round(u.set) + " W gesetzt"}${u.force ? " · Abregelung" : ""}${u.available === false ? " · nicht verfügbar" : ""}</div></div>`;
          }).join("")}</div>` : "",
          surplus: c.show_surplus && a.surplus_w != null ? `<div class="surplus"><div class="row"><span>Überschuss</span><b>${W(a.surplus_w)}</b></div>
            ${(a.slots || []).map(s => `<div class="row"><span>${esc(s.name)}</span><span>${s.state ? esc(s.state) + " · " : ""}<b>${W(s.own_w)}</b></span></div>`).join("")}</div>` : "",
          tags: c.show_tags ? `<div class="tags">
            ${a.mode_name ? `<span class="tag">${esc(a.mode_icon || "")} Modus: ${esc(a.mode_name)}</span>` : ""}
            ${a.eco_active ? '<span class="tag warn">🌙 Eco-Modus</span>' : ""}
            <span class="tag ${a.meter_ok === false ? "bad" : "ok"}">Zähler ${a.meter_ok === false ? "Ausfall" : "in Ordnung"}</span>
            <span class="tag">Sollwert ${W(a.target_w)}</span>
            ${a.blocked_w ? `<span class="tag">Entladung gesperrt für ${Math.round(a.blocked_w)} W</span>` : ""}</div>` : ""
        };
        body = compact ? `${c.show_headline ? `<div class="sub">${esc(hl)}</div>` : ""}${tiles}`
          : this._compose(blockOrder(c.order), parts, c);
        ready = true;
        this._goodBody = body;
        this._pill = pill;
      }
      const pill = st && this._pill && st.state !== "unavailable" ? `<span class="pill ${this._pill[1]}">${esc(this._pill[0])}</span>` : "";
      const a2 = (st && st.attributes) || {};
      const ks = c.show_kill && a2.kill_switch && this._hass && this._hass.states[a2.kill_switch] ? this._hass.states[a2.kill_switch] : null;
      const stopped = ks && ks.state === "on";
      const killBtn = ks ? `<button type="button" class="kill ${stopped ? "go" : this._armed ? "arm" : ""}" data-kill="1">${stopped ? "Fortsetzen" : this._armed ? "Wirklich stoppen?" : "Not-Aus"}</button>` : "";
      const when = st && st.last_updated ? `<span class="when">${ago(st.last_updated)}</span>` : "";
      const canOpen = c.tap_open && a2.addon_slug;
      const stale = a2.card_version && !VERSION.startsWith("__") && a2.card_version !== VERSION
        ? `<div class="oldv">Karte v${esc(VERSION)} ist veraltet (Add-on v${esc(a2.card_version)}). Bitte Seite neu laden bzw. in der App den Frontend-Cache leeren.</div>` : "";
      const head0 = c.title || killBtn ? `<div class="head"><span class="t">${esc(c.title)}</span>${pill}${when}${killBtn}</div>` : "";
      const head = stale + head0;
      const html = `<style>${STYLE}${c.accent ? `ha-card{--sc-sun:${esc(c.accent)}}` : ""}</style><ha-card class="${canOpen ? "tap" : ""}">
        ${head}${body}</ha-card>`;
      if (!ready) dbgNote(`Zustand ohne Inhalt: ${!this._hass ? "kein hass" : !st ? "Entität fehlt" : st.state}`);
      this._paint(html, ready);
      this._slug = canOpen ? a2.addon_slug : "";
      this._kill = ks ? a2.kill_switch : "";
      this._stopped = stopped;
    }

    /* Überschrift und Energiefluss stehen (wie im Add-on) zusammen auf dem Farbverlauf-Block, wenn sie nebeneinander liegen */
    _compose(order, parts, c) {
      const grad = c.gradient !== false;
      const out = [];
      for (let i = 0; i < order.length; i++) {
        const id = order[i];
        if (grad && id === "headline" && order[i + 1] === "flow") { out.push(`<div class="hero grad">${parts.headline}${parts.flow}</div>`); i++; continue; }
        if (grad && id === "flow" && parts.flow) { out.push(`<div class="hero grad">${parts.flow}</div>`); continue; }
        out.push(parts[id] || "");
      }
      return out.join("\n");
    }

    /* Zeichnet nur bei Änderung und hält die Höhe, damit die Seite nicht springt:
       die Karte wird nie kleiner als zuvor (gleiche Breite), und beim Laden gilt die zuletzt bekannte Höhe. */
    _paint(html, ready) {
      const root = this.shadowRoot;
      const vb = Math.round((window.innerWidth || 0) / 40);          // Breitenklasse des Fensters, auch vor dem ersten Layout bekannt
      const key = `sc-h:${this._cfg.entity}:${this._cfg.size}:${(this._cfg.order || []).join(",")}:${(this._cfg.meters_order || []).join(",")}:${vb}`;
      const w = this.offsetWidth || 0;
      if (this._hk !== key) { this._hk = key; this._minH = 0; }
      if (this._hw && w && Math.abs(this._hw - w) > 2) this._minH = 0;
      if (!this._minH) {
        try { const v = JSON.parse(localStorage.getItem(key) || "null"); if (v && v.h > 60 && v.h < 3000) this._minH = v.h; } catch (e) { /* ohne Speicher */ }
      }
      const full = `${html}<!--${this._minH || 0}-->`;
      if (full === this._last) return;
      this._last = full;
      const old = this.getBoundingClientRect();
      paintShadow(root, html);
      const card = root.querySelector("ha-card");
      this.style.minHeight = this._minH ? this._minH + "px" : "";
      if (card && this._minH) card.style.minHeight = this._minH + "px";
      const h = card ? Math.ceil(card.getBoundingClientRect().height) : 0;
      if (ready && h > (this._minH || 0)) {
        this._minH = h; this._hw = w;
        try { localStorage.setItem(key, JSON.stringify({ h, w })); } catch (e) { /* ohne Speicher */ }
      }
      if (ready) this._hw = w;
      // Wuchs die Karte oberhalb des sichtbaren Bereichs, Scrollposition ausgleichen
      const now = this.getBoundingClientRect();
      const dh = now.height - old.height;
      if (dh && old.bottom <= 0 && old.height) window.scrollBy(0, dh);
    }

    disconnectedCallback() { dbgNote("Karte entfernt"); if (this._ro) { this._ro.disconnect(); this._ro = null; } }

    connectedCallback() {
      dbgNote("Karte eingefügt" + (this._minH ? ` (Mindesthöhe ${this._minH} px)` : ""));
      if (!this._ro && window.ResizeObserver) {
        this._h0 = 0;
        this._ro = new ResizeObserver(() => {
          const h = Math.round(this.getBoundingClientRect().height);
          if (this._h0 && Math.abs(h - this._h0) > 40) dbgNote(`Höhe ${this._h0}→${h} px`);
          this._h0 = h;
          const wb = Math.round((this.offsetWidth || 0) / 40);
          if (this._wb !== undefined && wb !== this._wb && this._goodBody) this._render();
          this._wb = wb;
        });
        this._ro.observe(this);
      }
      this.shadowRoot.addEventListener("click", ev => {
        const k = ev.target.closest && ev.target.closest("[data-kill]");
        if (k) {
          ev.stopPropagation();
          if (this._stopped) { this._hass.callService("switch", "turn_off", { entity_id: this._kill }); return; }
          if (!this._armed) { this._armed = true; this._render(); clearTimeout(this._armT); this._armT = setTimeout(() => { this._armed = false; this._render(); }, 4000); return; }
          this._armed = false; clearTimeout(this._armT);
          this._hass.callService("switch", "turn_on", { entity_id: this._kill });
          this._render();
          return;
        }
        const tl = ev.target.closest && ev.target.closest("[data-tile]");
        if (tl && tl.dataset.tile.startsWith("m:") && this._hass) {
          const eid = tl.dataset.tile.slice(2);
          if (eid && this._hass.states[eid]) {            // Verlauf und Statistik des Zählers in Home Assistant
            ev.stopPropagation();
            this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId: eid }, bubbles: true, composed: true }));
            return;
          }
        }
        if (this._slug) {
          history.pushState(null, "", `/hassio/ingress/${this._slug}`);
          window.dispatchEvent(new CustomEvent("location-changed", { bubbles: true, composed: true }));
        }
      });
    }
  }

  // ---- Visueller Editor ----
  class SOLASICardEditor extends HTMLElement {
    setConfig(config) { this._cfg = config || {}; this._build(); }
    set hass(h) { const first = !this._hass; this._hass = h; if (this._form) this._form.hass = h; if (first && this._ord) this._drawOrder(); }
    _tiles() {
      const st = this._hass && this._hass.states ? this._hass.states[this._cfg.entity || "sensor.solasi"] : null;
      const a = (st && st.attributes) || {}, mc = a.meters_cfg || {}, out = [];
      if (mc.show_day !== false && a.today) out.push(["day", "Tagesverbrauch"]);
      (a.meters || []).forEach(m => out.push(["m:" + (m.entity || ""), m.name || m.entity]));
      if (mc.extra && a.today) { out.push(["pv", "Solarertrag heute"]); out.push(["imp", "Netzbezug heute"]); }
      const ord = Array.isArray(this._cfg.meters_order) && this._cfg.meters_order.length ? this._cfg.meters_order : (mc.order || []);
      const rk = k => { const i = ord.indexOf(k); return i < 0 ? 1e3 + out.findIndex(x => x[0] === k) : i; };
      return out.sort((x, y) => rk(x[0]) - rk(y[0]));
    }
    _drawOrder() {
      const names = Object.fromEntries(BLOCKS), o = blockOrder(this._cfg.order);
      const tl = this._tiles();
      const row = (n, key, i, len, attr) => `<div style="display:flex;align-items:center;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--divider-color,#ddd)">
          <span>${esc(n)}</span><span>
          <button type="button" ${attr}="${esc(key)}" data-mv="-1" ${i === 0 ? "disabled" : ""} aria-label="nach oben">↑</button>
          <button type="button" ${attr}="${esc(key)}" data-mv="1" ${i === len - 1 ? "disabled" : ""} aria-label="nach unten">↓</button></span></div>`;
      this._tileList = tl.map(x => x[0]);
      this._ord.innerHTML = `<div style="margin:14px 0 6px;font-weight:600">Reihenfolge der Blöcke</div>` + o.map((id, i) =>
        `<div style="display:flex;align-items:center;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--divider-color,#ddd)">
          <span>${esc(names[id])}</span><span>
          <button type="button" data-mv="-1" data-id="${id}" ${i === 0 ? "disabled" : ""} aria-label="nach oben">↑</button>
          <button type="button" data-mv="1" data-id="${id}" ${i === o.length - 1 ? "disabled" : ""} aria-label="nach unten">↓</button></span></div>`).join("") +
        `<div style="font-size:12px;color:var(--secondary-text-color);margin-top:6px">Ein- und Ausblenden über die Schalter oben.</div>` +
        (tl.length > 1 ? `<div style="margin:14px 0 6px;font-weight:600">Reihenfolge der Zählerkacheln</div>` + tl.map(([k, n], i) => row(n, k, i, tl.length, "data-tk")).join("") : "") +
        `<div style="font-size:11px;color:var(--secondary-text-color);margin-top:12px">Kartenversion ${esc(VERSION)}</div>`;
    }
    _build() {
      if (!this._form) {
        this._form = document.createElement("ha-form");
        this._form.computeLabel = s => ({ entity: "Entität", title: "Titel", size: "Größe", show_headline: "Überschrift zeigen",
          show_trend: "Tagesverlauf zeigen", show_meters: "Zählerreihe zeigen", meters_layout: "Anordnung der Zähler", show_batteries: "Speicher zeigen", show_surplus: "Überschuss zeigen", show_tags: "Hinweise zeigen",
          show_kill: "Not-Aus-Knopf zeigen", tap_open: "Antippen öffnet SOLASI", accent: "Akzentfarbe (z. B. #3F5BD8)", gradient: "Farbverlauf im Hintergrund", meters_compare: "Vergleich mit gestern", flow_layout: "Energiefluss: Vorlage", flow_size: "Energiefluss: Größe", flow_hide: "Energiefluss: ausblenden", flow_grid_pos: "Energiefluss: Platz des Netzes", flow_passthrough: "Umgeladenen Strom als durchgereicht zeigen" }[s.name] || s.name);
        this._form.schema = [
          { name: "entity", selector: { entity: { domain: "sensor" } } },
          { name: "title", selector: { text: {} } },
          { name: "size", selector: { select: { mode: "box", options: [{ value: "large", label: "Groß" }, { value: "compact", label: "Kompakt" }] } } },
          { name: "show_headline", selector: { boolean: {} } },
          { name: "show_meters", selector: { boolean: {} } },
          { name: "meters_layout", selector: { select: { mode: "box", options: [{ value: "big", label: "Große Kachel links" }, { value: "even", label: "Alle gleich groß" }] } } },
          { name: "meters_compare", selector: { select: { mode: "dropdown", options: [{ value: "auto", label: "Wie im Add-on" }, { value: "same", label: "Gleiche Uhrzeit" }, { value: "full", label: "Ganzer Tag" }, { value: "off", label: "Aus" }] } } },
          { name: "show_trend", selector: { boolean: {} } },
          { name: "show_batteries", selector: { boolean: {} } },
          { name: "show_surplus", selector: { boolean: {} } },
          { name: "show_tags", selector: { boolean: {} } },
          { name: "show_kill", selector: { boolean: {} } },
          { name: "tap_open", selector: { boolean: {} } },
          { name: "accent", selector: { text: {} } },
          { name: "gradient", selector: { boolean: {} } },
          { name: "flow_layout", selector: { select: { mode: "dropdown", options: [{ value: "auto", label: "Wie im Add-on" }, { value: "total", label: "Gesamt-Solar oben" }, { value: "pairs", label: "Paare" }, { value: "compact", label: "Kompakt" }] } } },
          { name: "flow_size", selector: { select: { mode: "dropdown", options: [{ value: "auto", label: "Wie im Add-on" }, { value: "compact", label: "Kompakt" }, { value: "large", label: "Groß" }] } } },
          { name: "flow_hide", selector: { select: { multiple: true, mode: "list", options: [{ value: "total", label: "Solar gesamt" }, { value: "solar", label: "Solar je Anlage" }, { value: "bat", label: "Speicher" }, { value: "grid", label: "Netz" }, { value: "house", label: "Haus" }] } } },
          { name: "flow_grid_pos", selector: { select: { mode: "dropdown", options: [{ value: "auto", label: "Wie im Add-on" }, { value: "mid", label: "In der Mitte" }, { value: "side", label: "Neben dem Haus" }] } } },
          { name: "flow_passthrough", selector: { boolean: {} } }];
        this._form.addEventListener("value-changed", ev => {
          const def = this._defaults || {}, before = this._cfg || {}, merged = { ...before, ...(ev.detail.value || {}) };
          const next = {};
          // nur Abweichungen vom Standard speichern, damit Werte aus dem Add-on gelten, solange nichts eingestellt wurde
          for (const k of Object.keys(merged)) if (k === "entity" || !(k in def) || k in before || JSON.stringify(merged[k]) !== JSON.stringify(def[k])) next[k] = merged[k];
          this._cfg = { ...next };
          this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._cfg }, bubbles: true, composed: true }));
        });
        this.appendChild(this._form);
        this._ord = document.createElement("div");
        this._ord.className = "sc-order";
        this._ord.addEventListener("click", ev => {
          const b = ev.target.closest && ev.target.closest("button[data-mv]");
          if (!b) return;
          if (b.dataset.tk !== undefined) {
            const t = [...(this._tileList || [])], i = t.indexOf(b.dataset.tk), j = i + Number(b.dataset.mv);
            if (i < 0 || j < 0 || j >= t.length) return;
            [t[i], t[j]] = [t[j], t[i]];
            this._cfg = { ...this._cfg, meters_order: t };
            this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._cfg }, bubbles: true, composed: true }));
            this._drawOrder();
            return;
          }
          const o = blockOrder(this._cfg.order), i = o.indexOf(b.dataset.id), j = i + Number(b.dataset.mv);
          if (i < 0 || j < 0 || j >= o.length) return;
          [o[i], o[j]] = [o[j], o[i]];
          this._cfg = { ...this._cfg, order: o };
          this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._cfg }, bubbles: true, composed: true }));
          this._drawOrder();
        });
        this.appendChild(this._ord);
      }
      this._drawOrder();
      this._form.hass = this._hass;
      this._defaults = { entity: "sensor.solasi", title: "SOLASI", size: "large", show_headline: true, show_meters: true, meters_layout: "big", show_trend: true, show_batteries: true,
        show_surplus: true, show_tags: true, show_kill: true, tap_open: true, accent: "", gradient: true, meters_compare: "auto", flow_layout: "auto", flow_hide: [], flow_size: "auto", flow_grid_pos: "auto", flow_passthrough: true };
      this._form.data = { ...this._defaults, ...this._cfg };
    }
  }

  if (!customElements.get("solasi-card-editor")) customElements.define("solasi-card-editor", SOLASICardEditor);
  if (!customElements.get("solasi-card")) customElements.define("solasi-card", SOLASICard);
  window.customCards = window.customCards || [];
  if (!window.customCards.some(c => c.type === "solasi-card")) {
    window.customCards.push({ type: "solasi-card", name: "SOLASI", preview: true,
      description: "Energiefluss von Solar, Speicher, Haus und Netz mit Ladestand und Überschuss." });
  }
  console.info(`%c SOLASI-CARD %c v${VERSION} `, "background:#f59e0b;color:#2b1c00;font-weight:700", "background:#2b2a28;color:#f59e0b");
})();
