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
 *   show_kill: true                 # Not-Aus-Knopf (braucht MQTT, siehe Anleitung)
 *   tap_open: true                  # Antippen öffnet SOLASI
 *   accent: ""                      # Akzentfarbe, z. B. "#3F5BD8" (leer = Standard)
 */
(() => {
  const VERSION = "__VERSION__";
  const W = v => (v == null || isNaN(v)) ? "–" : `${Math.round(v)} W`;
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const num = v => (v === null || v === undefined || v === "" || isNaN(Number(v))) ? null : Number(v);

  const STYLE = `
    :host{display:block}
    ha-card{padding:14px 16px 12px;overflow:hidden;
      --sc-sun:var(--solasi-sun,#f59e0b);--sc-bat:var(--solasi-battery,#14b8a6);
      --sc-grid:var(--solasi-grid,#6366f1);--sc-home:var(--solasi-home,#64748b);
      --sc-ok:var(--success-color,#1f9d63);--sc-warn:var(--warning-color,#d97706);--sc-bad:var(--error-color,#e5484d);
      --sc-test:var(--solasi-test,#8b5cf6);
      --sf-card:var(--ha-card-background,var(--card-background-color,#fff));--sf-fg:var(--primary-text-color);--sf-muted:var(--secondary-text-color);
      --sf-line:var(--divider-color,#ddd);--sf-sun:var(--sc-sun);--sf-bat:var(--sc-bat);--sf-grid:var(--sc-grid);--sf-home:var(--sc-home);
      --sf-ok:var(--sc-ok);--sf-warn:var(--sc-warn);--sf-bad:var(--sc-bad)}
    .head{display:flex;align-items:center;gap:8px;margin-bottom:2px}
    .head .t{font-size:16px;font-weight:600;color:var(--primary-text-color)}
    .pill{margin-left:auto;font-size:11.5px;font-weight:600;padding:3px 10px;border-radius:999px;
      background:var(--secondary-background-color,#f3f3f3);color:var(--secondary-text-color)}
    .pill.live{color:var(--sc-ok)}.pill.test{color:var(--sc-test)}.pill.observe{color:var(--sc-warn)}.pill.bad,.pill.stopped{color:var(--sc-bad)}
    .headline{font-size:17px;font-weight:650;color:var(--primary-text-color);margin-top:4px}
    .sub{font-size:12.5px;color:var(--secondary-text-color);margin-top:1px}
    svg{width:100%;height:auto;display:block;max-height:340px;margin-top:4px}
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
   --sf-card --sf-fg --sf-muted --sf-line --sf-sun --sf-bat --sf-grid --sf-home --sf-ok --sf-warn --sf-bad */
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

  function tile(k, label, val, sub, col, icon) {
    const t = T[k];
    return `<g><rect x="${t.x}" y="${t.y}" width="${TW}" height="${TH}" rx="18" style="fill:var(--sf-card)"/>
      <rect x="${t.x}" y="${t.y}" width="${TW}" height="${TH}" rx="18" style="fill:var(${col});fill-opacity:.13;stroke:var(${col});stroke-width:1.6"/>
      <g transform="translate(${t.x + 14} ${t.y + 14})">${icon}</g>
      <text x="${t.x + 54}" y="${t.y + 27}" class="sf-l">${label}</text>
      <text x="${t.x + 54}" y="${t.y + 50}" class="sf-v">${val}</text>
      ${sub ? `<text x="${t.x + 54}" y="${t.y + 66}" class="sf-s">${sub}</text>` : ""}</g>`;
  }

  /* d: {pv, house, bat (+ entlädt), grid (+ Bezug), soc, f:{sh, sb, bh, gh}} */
  function flow(d) {
    const f = d.f || {}, v = { sh: f.sh, sb: f.sb, bh: f.bh, gh: f.gh };
    let idle = "", live = "", dots = "", chips = "";
    for (const k in L) {
      const x = L[k], val = v[k] == null ? 0 : v[k];
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
        <text x="${mx.toFixed(1)}" y="${(my + 4).toFixed(1)}" text-anchor="middle" class="sf-c">${txt}</text>`;
    }
    const bat = d.bat, grid = d.grid == null ? 0 : d.grid, soc = d.soc != null && d.soc >= 0 ? Math.round(d.soc) : null;
    const batSub = bat == null ? "" : bat >= 5 ? "gibt ab" : bat <= -5 ? "lädt" : "ruht";
    const gridSub = grid >= 5 ? "Bezug" : grid <= -5 ? "Einspeisung" : "ausgeglichen";
    return `<svg viewBox="0 0 640 340" role="img" aria-label="Energiefluss">${CSS}${idle}${live}${dots}${chips}
      ${tile("sun", "Solar", wl(d.pv), d.pv != null && d.pv < 5 ? "keine Sonne" : "", "--sf-sun", ICON.sun("var(--sf-sun)"))}
      ${tile("bat", "Speicher", bat == null ? "–" : wl(Math.abs(bat)), batSub ? batSub + (soc != null ? " · " + soc + " %" : "") : (soc != null ? soc + " %" : ""), "--sf-bat", ICON.bat("var(--sf-bat)", soc))}
      ${tile("grid", "Netz", wl(Math.abs(grid)), gridSub, "--sf-grid", ICON.grid("var(--sf-grid)"))}
      ${tile("home", "Haus", wl(d.house), d.house != null ? "Verbrauch" : "", "--sf-home", ICON.home("var(--sf-home)"))}
    </svg>`;
  }

  /* Überschrift aus den Flüssen; ohne Flüsse aus dem Sollwert. d: {f, grid, soc, target} */
  function headline(d) {
    const f = d.f, s = d.soc != null && d.soc >= 0 ? ` · mittlerer Ladestand ${Math.round(d.soc)} %` : "";
    const g = d.grid == null ? 0 : d.grid;
    const gs = Math.abs(g) < 30 ? "Netzbezug nahe null" : g > 0 ? `Netzbezug ${fmt(g)} W` : `Einspeisung ${fmt(-g)} W`;
    if (f) {
      const sh = f.sh >= 5, sb = f.sb >= 5, bh = f.bh >= 5, gh = f.gh >= 5;
      if (sh && sb) return ["Solar versorgt dein Haus und lädt den Speicher", gs + s];
      if (sh && bh && gh) return ["Solar, Speicher und Netz versorgen dein Haus", `Der Verbrauch ist höher als die Abgabe der Speicher${s}`];
      if (sh && bh) return ["Solar und Speicher versorgen dein Haus", gs + s];
      if (bh) return [`Der Speicher versorgt dein Haus mit ${fmt(f.bh)} W`, gs + s];
      if (sb) return [`Überschuss lädt den Speicher mit ${fmt(f.sb)} W`, (Math.abs(g) < 30 ? "Einspeisung wird vermieden" : gs) + s];
      if (sh && !gh) return ["Solar versorgt dein Haus", gs + s];
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
    const pv = d.pv || [], hs = d.house || [], n = Math.max(pv.length, hs.length);
    if (n < 3) return "";
    const end = Date.now() / 1000;
    const ts = d.t && d.t.length === n ? d.t : Array.from({ length: n }, (_, i) => end - (n - 1 - i) * 300);
    const t1 = Math.max(ts[n - 1], ts[0] + 600), t0 = Math.max(ts[0], t1 - 86400);
    const X0 = 44, X1 = 626, Y0 = 18, Y1 = 150;
    const all = [...pv, ...hs].filter(v => v != null);
    const mx = Math.max(...all, 100);
    const step = [250, 500, 1000, 2000, 2500, 5000, 10000].find(s => mx / s <= 3.2) || 10000;
    const top = Math.ceil(mx / step) * step;
    const X = t => X0 + (t - t0) / (t1 - t0) * (X1 - X0), Y = v => Y1 - Math.min(v, top) / top * (Y1 - Y0);
    const pts = arr => { const o = []; let last = 0; for (let i = 0; i < n; i++) { if (ts[i] < t0) continue; if (arr[i] != null) last = arr[i]; o.push([X(ts[i]), Y(last)]); } return o; };
    const P = pts(pv), H = pts(hs);
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
    return `<svg viewBox="0 0 640 196" role="img" aria-label="Verlauf der letzten Stunden: Solar und Haus">${CSS}${grid}${ticks}
      <path d="${area}" style="fill:var(--sf-sun);fill-opacity:.2;stroke:none"/>
      <path d="${smooth(P, Y1)}" class="sf-o" style="stroke:var(--sf-sun);stroke-width:2.4;stroke-linejoin:round"/>
      <path d="${smooth(H, Y1)}" class="sf-o" style="stroke:var(--sf-home);stroke-width:2.4;stroke-linejoin:round"/>
      <circle cx="${nowP[0].toFixed(1)}" cy="${nowP[1].toFixed(1)}" r="4.5" style="fill:var(--sf-sun);stroke:var(--sf-card);stroke-width:2"/>
      <g transform="translate(${X0} 186)"><circle cx="5" cy="-4" r="5" style="fill:var(--sf-sun)"/><text x="16" y="0" class="sf-c">Solar</text>
      <circle cx="78" cy="-4" r="5" style="fill:var(--sf-home)"/><text x="89" y="0" class="sf-c">Haus</text></g></svg>`;
  }

  return { flow, trend, headline, wl };
})();
/*FLOW-END*/
  function flowData(a) {
    const f = a.flows;
    return { pv: num(a.pv_w), house: num(a.house_w), bat: num(a.battery_w), grid: num(a.grid_w) ?? 0, soc: num(a.avg_soc), target: num(a.target_w),
      f: f ? { sh: f.solar_house, sb: f.solar_battery, bh: f.battery_house, gh: f.grid_house } : null };
  }
  const flowSVG = a => SF.flow(flowData(a));

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

    setConfig(config) {
      this._cfg = { entity: "sensor.solasi", title: "SOLASI", show_headline: true, show_batteries: true,
                    show_surplus: true, show_tags: true, size: "large", show_trend: true, show_kill: true,
                    tap_open: true, accent: "", ...(config || {}) };
      this._key = null;
      this._render();
    }

    set hass(hass) {
      this._hass = hass;
      const st = hass && hass.states ? hass.states[this._cfg.entity] : null;
      const key = st ? `${st.state}|${st.last_updated}` : "none";
      if (key !== this._key) { this._key = key; this._render(); }
    }

    getCardSize() { return 5; }
    static getStubConfig() { return { entity: "sensor.solasi" }; }
    static getConfigElement() { return document.createElement("solasi-card-editor"); }

    _render() {
      if (!this._cfg) return;
      const c = this._cfg;
      const st = this._hass && this._hass.states ? this._hass.states[c.entity] : null;
      let body;
      if (!this._hass) {
        body = `<div class="msg">Lade …</div>`;
      } else if (!st) {
        body = `<div class="msg">Entität <b>${esc(c.entity)}</b> nicht gefunden.<br>Läuft das SOLASI-Add-on?</div>`;
      } else if (st.state === "unavailable" || st.state === "unknown") {
        body = `<div class="msg">SOLASI ist gerade nicht erreichbar.</div>`;
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
        body = compact ? `${c.show_headline ? `<div class="sub">${esc(hl)}</div>` : ""}${tiles}` : `
          ${c.show_headline ? `<div class="headline">${esc(hl)}</div><div class="sub">${esc(sub)}</div>` : ""}
          ${flowSVG(a)}
          ${c.show_trend ? trendSVG(a) : ""}
          ${c.show_batteries && (a.units || []).length ? `<div class="units">${a.units.map(u => {
            const soc = u.soc < 0 ? null : u.soc;
            return `<div class="unit"><div class="n">${esc(u.name)}</div><div class="s">${soc == null ? "–" : soc + " %"}</div>
              <div class="bar"><div style="width:${soc || 0}%;background:${socColor(soc)}"></div></div>
              <div class="d">${u.pv != null ? "Solar " + Math.round(u.pv) + " W · " : ""}${Math.round(u.set)} W gesetzt${u.force ? " · Abregelung" : ""}${u.available === false ? " · nicht verfügbar" : ""}</div></div>`;
          }).join("")}</div>` : ""}
          ${c.show_surplus && a.surplus_w != null ? `<div class="surplus"><div class="row"><span>Überschuss</span><b>${W(a.surplus_w)}</b></div>
            ${(a.slots || []).map(s => `<div class="row"><span>${esc(s.name)}</span><span>${s.state ? esc(s.state) + " · " : ""}<b>${W(s.own_w)}</b></span></div>`).join("")}</div>` : ""}
          ${c.show_tags ? `<div class="tags">
            ${a.eco_active ? '<span class="tag warn">🌙 Eco-Modus</span>' : ""}
            <span class="tag ${a.meter_ok === false ? "bad" : "ok"}">Zähler ${a.meter_ok === false ? "Ausfall" : "in Ordnung"}</span>
            <span class="tag">Sollwert ${W(a.target_w)}</span>
            ${a.blocked_w ? `<span class="tag">Entladung gesperrt für ${Math.round(a.blocked_w)} W</span>` : ""}</div>` : ""}`;
        this._pill = pill;
      }
      const pill = st && this._pill && st.state !== "unavailable" ? `<span class="pill ${this._pill[1]}">${esc(this._pill[0])}</span>` : "";
      const a2 = (st && st.attributes) || {};
      const ks = c.show_kill && a2.kill_switch && this._hass && this._hass.states[a2.kill_switch] ? this._hass.states[a2.kill_switch] : null;
      const stopped = ks && ks.state === "on";
      const killBtn = ks ? `<button type="button" class="kill ${stopped ? "go" : this._armed ? "arm" : ""}" data-kill="1">${stopped ? "Fortsetzen" : this._armed ? "Wirklich stoppen?" : "Not-Aus"}</button>` : "";
      const when = st && st.last_updated ? `<span class="when">${ago(st.last_updated)}</span>` : "";
      const canOpen = c.tap_open && a2.addon_slug;
      const head = c.title || killBtn ? `<div class="head"><span class="t">${esc(c.title)}</span>${pill}${when}${killBtn}</div>` : "";
      this.shadowRoot.innerHTML = `<style>${STYLE}${c.accent ? `ha-card{--sc-sun:${esc(c.accent)}}` : ""}</style><ha-card class="${canOpen ? "tap" : ""}">
        ${head}${body}</ha-card>`;
      this._slug = canOpen ? a2.addon_slug : "";
      this._kill = ks ? a2.kill_switch : "";
      this._stopped = stopped;
    }

    connectedCallback() {
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
    set hass(h) { this._hass = h; if (this._form) this._form.hass = h; }
    _build() {
      if (!this._form) {
        this._form = document.createElement("ha-form");
        this._form.computeLabel = s => ({ entity: "Entität", title: "Titel", size: "Größe", show_headline: "Überschrift zeigen",
          show_trend: "Tagesverlauf zeigen", show_batteries: "Speicher zeigen", show_surplus: "Überschuss zeigen", show_tags: "Hinweise zeigen",
          show_kill: "Not-Aus-Knopf zeigen", tap_open: "Antippen öffnet SOLASI", accent: "Akzentfarbe (z. B. #3F5BD8)" }[s.name] || s.name);
        this._form.schema = [
          { name: "entity", selector: { entity: { domain: "sensor" } } },
          { name: "title", selector: { text: {} } },
          { name: "size", selector: { select: { mode: "box", options: [{ value: "large", label: "Groß" }, { value: "compact", label: "Kompakt" }] } } },
          { name: "show_headline", selector: { boolean: {} } },
          { name: "show_trend", selector: { boolean: {} } },
          { name: "show_batteries", selector: { boolean: {} } },
          { name: "show_surplus", selector: { boolean: {} } },
          { name: "show_tags", selector: { boolean: {} } },
          { name: "show_kill", selector: { boolean: {} } },
          { name: "tap_open", selector: { boolean: {} } },
          { name: "accent", selector: { text: {} } }];
        this._form.addEventListener("value-changed", ev => {
          this._cfg = { ...this._cfg, ...ev.detail.value };
          this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._cfg }, bubbles: true, composed: true }));
        });
        this.appendChild(this._form);
      }
      this._form.hass = this._hass;
      this._form.data = { entity: "sensor.solasi", title: "SOLASI", size: "large", show_headline: true, show_trend: true, show_batteries: true,
        show_surplus: true, show_tags: true, show_kill: true, tap_open: true, accent: "", ...this._cfg };
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
