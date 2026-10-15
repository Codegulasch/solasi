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
