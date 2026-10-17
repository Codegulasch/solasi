// Liest aus der Energiefluss-Grafik, welche Linien laufen und in welche Richtung.
// Bei breiter Anzeige rücken die Kacheln auseinander (siehe flow() in flow_shared.js), die Startpunkte werden entsprechend verschoben.
const START={sh:[[320,88],[320,252]],sb:[[245,50],[95,152]],bh:[[95,228],[245,290]],gh:[[545,228],[395,290]]};
const sx=(x,ex)=>x<=200?x:x>=400?x+ex:x+ex/2;
exports.lines=svg=>{
  const out={sh:null,sb:null,bh:null,gh:null};
  const ex=Number((svg.getAttribute("viewBox")||"0 0 640 0").split(" ")[2])-640;
  const M=([x,y])=>`M${sx(x,ex)} ${y}`;
  [...svg.querySelectorAll("path.sf-o")].forEach(p=>{
    const d=p.getAttribute("d");
    for(const k in START){if(d.startsWith(M(START[k][0])))out[k]="fwd";else if(d.startsWith(M(START[k][1])))out[k]="rev";}
  });
  return out;
};
exports.chips=svg=>[...svg.querySelectorAll("text.sf-c")].map(t=>t.textContent);
