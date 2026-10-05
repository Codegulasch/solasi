// Führt alle Oberflächen-Tests aus und beendet sich mit Fehlercode, wenn einer fehlschlägt.
const { spawnSync } = require("child_process");
const path = require("path");
let failed = 0;
for (const f of ["ui.js", "ui_welcome.js", "card.js"]) {
  const r = spawnSync("node", [path.join(__dirname, f)], { encoding: "utf8" });
  const out = (r.stdout || "") + (r.stderr || "");
  const ok = (out.match(/^ok /gm) || []).length;
  const bad = (out.match(/^FAIL/gm) || []).length;
  console.log(`${f}: ${ok} bestanden, ${bad} fehlgeschlagen (Exit ${r.status})`);
  if (r.status !== 0 || bad > 0) { failed++; console.log(out); }
}
process.exit(failed ? 1 : 0);
