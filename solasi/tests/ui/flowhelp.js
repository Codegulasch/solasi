// Liest aus der Energiefluss-Grafik, welche Linien laufen und in welche Richtung.
const START={sh:["M320 88","M320 252"],sb:["M245 50","M95 152"],bh:["M95 228","M245 290"],gh:["M545 228","M395 290"]};
exports.lines=svg=>{
  const out={sh:null,sb:null,bh:null,gh:null};
  [...svg.querySelectorAll("path.sf-o")].forEach(p=>{
    const d=p.getAttribute("d");
    for(const k in START){if(d.startsWith(START[k][0]))out[k]="fwd";else if(d.startsWith(START[k][1]))out[k]="rev";}
  });
  return out;
};
exports.chips=svg=>[...svg.querySelectorAll("text.sf-c")].map(t=>t.textContent);
