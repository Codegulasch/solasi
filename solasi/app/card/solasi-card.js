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
      --sc-test:var(--solasi-test,#8b5cf6)}
    .head{display:flex;align-items:center;gap:8px;margin-bottom:2px}
    .head .t{font-size:16px;font-weight:600;color:var(--primary-text-color)}
    .pill{margin-left:auto;font-size:11.5px;font-weight:600;padding:3px 10px;border-radius:999px;
      background:var(--secondary-background-color,#f3f3f3);color:var(--secondary-text-color)}
    .pill.live{color:var(--sc-ok)}.pill.test{color:var(--sc-test)}.pill.observe{color:var(--sc-warn)}.pill.bad,.pill.stopped{color:var(--sc-bad)}
    .headline{font-size:17px;font-weight:650;color:var(--primary-text-color);margin-top:4px}
    .sub{font-size:12.5px;color:var(--secondary-text-color);margin-top:1px}
    svg{width:100%;height:auto;display:block;max-height:300px;margin-top:4px}
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
    .trend svg{max-height:56px;margin:0}
    .trend .leg{font-size:11.5px;color:var(--secondary-text-color);display:flex;gap:12px;margin-top:2px}
  `;

  function flowSVG(a) {
    const pv = num(a.pv_w), bat = num(a.battery_w), grid = num(a.grid_w) ?? 0, house = num(a.house_w), f = a.flows || {};
    const act = v => v != null && Math.abs(v) >= 5;
    // Linie mit Wert; fwd: Fluss in Richtung des Pfads (von x1,y1 nach x2,y2)
    const edge = (d, val, fwd, col, lx, ly, anchor) =>
      `<path d="${d}" class="line ${act(val) ? "on" + (fwd ? "" : " rev") : ""}" ${act(val) ? `style="stroke:${col}"` : ""}/>` +
      (act(val) ? `<text x="${lx}" y="${ly}" text-anchor="${anchor}" class="evl">${Math.round(Math.abs(val))} W</text>` : "");
    const node = (x, y, icon, label, val, sub, col, side) =>
      `<g><circle cx="${x}" cy="${y}" r="38" fill="${col}" fill-opacity=".15" stroke="${col}" stroke-width="2.5"/>
        <text x="${x}" y="${y + 10}" text-anchor="middle" font-size="30">${icon}</text>
        ${side
          ? `<text x="${x + 52}" y="${y - 2}" class="lbl">${label}</text><text x="${x + 52}" y="${y + 20}" class="val">${val}</text>`
          : `<text x="${x}" y="${y + 62}" text-anchor="middle" class="lbl">${label}</text>
             <text x="${x}" y="${y + 82}" text-anchor="middle" class="val">${val}</text>
             ${sub ? `<text x="${x}" y="${y + 98}" text-anchor="middle" class="small">${sub}</text>` : ""}`}</g>`;
    const batSub = bat == null ? "" : bat >= 5 ? "entlädt" : bat <= -5 ? "lädt" : "ruht";
    const gridSub = grid >= 5 ? "Bezug" : grid <= -5 ? "Einspeisung" : "ausgeglichen";
    const bh = f.battery_house;
    return `<svg viewBox="0 0 640 330" role="img" aria-label="Energiefluss">
      ${edge("M320 92 L320 158", f.solar_house, true, "var(--sc-sun)", 332, 130, "start")}
      ${edge("M288.6 75.4 L143.4 174.6", f.solar_battery, true, "var(--sc-sun)", 204, 114, "end")}
      ${edge("M150 196 L282 196", bh, bh != null && bh > 0, "var(--sc-bat)", 216, 186, "middle")}
      ${edge("M358 196 L490 196", f.grid_house, f.grid_house != null && f.grid_house < 0, "var(--sc-grid)", 424, 186, "middle")}
      ${node(320, 54, "☀️", "Solar", W(pv), "", "var(--sc-sun)", true)}
      ${node(112, 196, "🔋", "Speicher", bat == null ? "–" : W(Math.abs(bat)), batSub, "var(--sc-bat)")}
      ${node(320, 196, "🏠", "Haus", W(house), "", "var(--sc-home)")}
      ${node(528, 196, "⚡", "Netz", W(Math.abs(grid)), gridSub, "var(--sc-grid)")}
    </svg>`;
  }

  function headline(a, state) {
    const t = num(a.target_w) ?? 0, soc = a.avg_soc, prefix = a.mode === "test" ? "Im Test: " : "";
    if (a.mode === "stopped") return ["SOLASI ist gestoppt", a.stop_reason ? `${a.stop_reason}. Die Speicher laufen im eigenen Modus.` : "Die Speicher laufen im eigenen Modus."];
    if (a.mode === "observe") return ["SOLASI beobachtet nur", "Die Regelung ist aus, es wird nichts gesendet."];
    if (a.meter_ok === false) return ["Zähler ohne Meldung", "Zur Sicherheit gehen die Speicher auf 0 W."];
    const s = soc != null ? ` · mittlerer Ladestand ${soc} %` : "";
    if (t > 0) return [`${prefix}Die Speicher versorgen dein Haus mit ${Math.abs(t)} W`, `Netzbezug wird auf nahe null geregelt${s}`];
    if (t < 0) return [`${prefix}Überschuss lädt die Speicher mit ${Math.abs(t)} W`, `Einspeisung wird vermieden${s}`];
    return [`${prefix}Alles ausgeglichen`, `Gerade ist keine Regelung nötig${s}`];
  }

  function trendSVG(a) {
    const t = a.trend || {}, pv = t.pv || [], hs = t.house || [];
    const n = Math.max(pv.length, hs.length);
    if (n < 3) return "";
    const all = [...pv, ...hs].filter(v => v != null);
    const hi = Math.max(...all, 100);
    const X = i => (i / (n - 1)) * 560, Y = v => 50 - (v / hi) * 46;
    const path = arr => arr.map((v, i) => v == null ? null : `${i && arr[i - 1] != null ? "L" : "M"}${X(i).toFixed(1)} ${Y(v).toFixed(1)}`).filter(Boolean).join("");
    const area = pv.length > 1 && pv.every(v => v != null) ? `<path d="${path(pv)}L${X(pv.length - 1).toFixed(1)} 50L0 50Z" fill="var(--sc-sun)" fill-opacity=".18"/>` : "";
    return `<div class="trend"><svg viewBox="0 0 560 54" preserveAspectRatio="none" role="img" aria-label="Verlauf der letzten 24 Stunden">
      ${area}<path d="${path(pv)}" fill="none" stroke="var(--sc-sun)" stroke-width="2" vector-effect="non-scaling-stroke"/>
      <path d="${path(hs)}" fill="none" stroke="var(--sc-home)" stroke-width="2" vector-effect="non-scaling-stroke"/></svg>
      <div class="leg"><span style="color:var(--sc-sun)">● Solar</span><span style="color:var(--sc-home)">● Haus</span><span>letzte 24 Stunden</span></div></div>`;
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
