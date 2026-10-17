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
        <text x="${mx.toFixed(1)}" y="${(my + 4).toFixed(1)}" text-anchor="middle" class="sf-c">${txt}</text>`;
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
      if (showT && showS) lines.push({ pts: vc(mc, Y.t + th, c, Y.s), col: "--sf-sun", val: pv });
      if (showS && showB) lines.push({ pts: vc(c, Y.s + th, c, Y.b), col: "--sf-sun", val: pv == null ? null : chg });
      else if (showT && showB) lines.push({ pts: vc(mc, Y.t + th, c, Y.b), col: "--sf-sun", val: pv == null ? null : chg });
      if (showH && showS) lines.push({ pts: [[ex, Y.s + 38], [mid, Y.s + 38], [mid, Y.h + 24], [hin, Y.h + 24]], col: "--sf-sun", val: toHouse });
      else if (showH && showT) { const sx = left ? mx + 35 : mx + TW - 35; lines.push({ pts: [[sx, Y.t + th], [mid, Y.t + th + (Y.h - Y.t - th) * .3], [mid, Y.h + 24], [hin, Y.h + 24]], col: "--sf-sun", val: toHouse }); }
      if (showB && showH) lines.push({ pts: [[c, Y.b + th], [c, Y.h + 52], [left ? ex + 25 : ex - 25, Y.h + 52], [hin, Y.h + 52]], col: "--sf-bat", val: dis });
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
    if (showH) tiles.push(tile("home", "Haus", wl(d.house), d.house != null ? "Verbrauch" : "", "--sf-home", ICON.home("var(--sf-home)"), { x: mx, y: Y.h, w: TW }));
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

  const FLOW_DEF = { size: "auto", layout: "total", total: true, solar: true, bat: true, grid: true, house: true, grid_pos: "mid", order: [] };
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
    .sfm-h .sfm-t{justify-content:center;gap:8px;padding:16px;background:linear-gradient(135deg,color-mix(in srgb,var(--sf-sun) 18%,var(--sf-tile,transparent)),var(--sf-tile,transparent) 85%)}
    .sfm-hd{display:flex;align-items:center;gap:9px;min-width:0;width:100%}
    .sfm-ic{flex:none;width:30px;height:30px;border-radius:10px;display:grid;place-items:center;background:color-mix(in srgb,var(--c) 16%,transparent);color:var(--c)}
    .sfm-h .sfm-ic{width:38px;height:38px;border-radius:12px}
    .sfm-ic svg{width:18px;height:18px}.sfm-h .sfm-ic svg{width:22px;height:22px}
    .sfm-n{font-size:13px;line-height:1.25;color:var(--sf-muted);font-weight:600;min-width:0;overflow-wrap:anywhere}
    .sfm-v{font-size:19px;font-weight:800;letter-spacing:-.01em;color:var(--sf-fg);white-space:nowrap}
    .sfm-h .sfm-v{font-size:28px}
    .sfm-v small{font-size:12.5px;font-weight:600;color:var(--sf-muted);margin-left:3px}
    .sfm-d{font-size:12px;color:var(--sf-muted);margin-top:1px;white-space:nowrap}
    .sfm-d b{color:var(--sf-ok);font-weight:700}
    .sfm-c{font-size:12px;color:var(--sf-muted);margin-top:1px;white-space:nowrap}
    .sfm-c i{font-style:normal;font-weight:700}.sfm-c .cg{color:var(--sf-ok)}.sfm-c .cb{color:var(--sf-bad)}
    .sfm.even .sfm-h .sfm-t{height:100%}
    .sfm.big .sfm-r .sfm-t{flex-direction:row;align-items:center;justify-content:space-between;gap:12px}
    .sfm.big .sfm-r .sfm-hd{width:auto;flex:1}
    .sfm.big .sfm-r .sfm-val{text-align:right;flex:none}
    .sfm.big .sfm-r .sfm-v{font-size:18px}
    @container (max-width:440px){
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
