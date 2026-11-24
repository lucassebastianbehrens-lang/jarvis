"use strict";
// Landmassen als Punkt-Raster (3°), erzeugt aus Natural Earth 110m
const LAND="103ffffffffffffffffffffffffff8,003ffffff800ffffffffffffffff80,01ffffffe008ffffffffffffffffe0,0003ff5ffe0003ffffffffffffffe0,000000201b0000ffffffeffffffff8,000000000e000000013fe3ffffff00,000000000200000000020002000000,000000000000000000000000000000,000000000000000000000000000000,000000000000000000000000000000,000000000c00000000000000000000,000000001800000000000000000000,000000001c00000000000000000000,000000001c00000000000000000008,000000001c00000000000000000804,000000000e00000000000000000002,000000000f80000000000000003c00,000000000fc0000038000000187e00,000000000fe000003c0000003ffe00,000000000ff000007e0000003ffe00,0000000007f800007f1000003ffe00,0000000007fc0000ff1000001ffc00,000000000ffe0000ff10000007f801,000000001ffe0000ffc80000039000,000000003ffe00007f80000000d000,000000003fff0000ff800000001400,000000007fff0000ff800001003800,000000007ffe0001ff80000268e200,000000007fe00001ffc00006e00000,000000003fe00001fff00008600000,000000003f8000f3fff00004000000,00000000df0000fffff80000000000,00000001000001ffffc00603000000,00000007000003ffffb80607080000,0000003e200001ffffbe0f1e080000,00000072200003ffff7f1f9f000000,000000e0000001ffff7e3fffe80000,000003f0000001fffefbfffff00000,000007fd8000007ffff7fffff80000,000007ffc000007f00fffffff10000,00001fffe000000f00fffffff26000,00001fffe000007057f3ffffe20000,00001ffff0000078b937fffffe0000,00001ffffe00000f7df7ffffffd000,00003ffffcc0001ffffffffffff000,00007fffff000037fffffffffff000,00007fffbf800051fffffffffff080,0180fffc3f0000209fffffffffc0c0,0fe7fff03a000003c3ffffffffff30,17fffffc081c0003dfffffffffffff,effffffe1a3f0e00ff3fffffffffff,07fdfb45b81fe0003f00d7fffffff7,00003fb3e03ff000000617fffe3c00,0000038f807ff8000001007fc03400,00000231cffff800d0000000000000,00000003fffffe0000000010000000,000000000000000000000000000000";
/* ---------- Lage-Zentrale (Globus) ---------- */
const Globe={rot:-10,tilt:22,sel:null,run:false,drag:null,spots:[]};
const LANDPTS=(()=>{const pts=[];LAND.split(",").forEach((row,r)=>{const la=-84+r*3;[...row].forEach((h,i)=>{const b=parseInt(h,16);for(let k=0;k<4;k++)if(b&(8>>k))pts.push([la,-180+(i*4+k)*3+1.5])})});return pts})();
const globeStart=(()=>{let cv,g,W,H,R,last=0;const RM=matchMedia("(prefers-reduced-motion: reduce)").matches,rad=Math.PI/180;
  function proj(la,lo){const p=la*rad,l=(lo-Globe.rot)*rad,t=Globe.tilt*rad,cp=Math.cos(p);
    return[W/2+R*cp*Math.sin(l),H/2-R*(Math.cos(t)*Math.sin(p)-Math.sin(t)*cp*Math.cos(l)),Math.sin(t)*Math.sin(p)+Math.cos(t)*cp*Math.cos(l)]}
  function resize(){const r=cv.parentElement.getBoundingClientRect();if(!r.width)return false;const d=devicePixelRatio||1;W=r.width;H=Math.min(W*.8,460);
    cv.width=W*d;cv.height=H*d;cv.style.height=H+"px";g.setTransform(d,0,0,d,0,0);R=Math.min(W,H)*.42;return true}
  function draw(t){g.clearRect(0,0,W,H);
    const gl=g.createRadialGradient(W/2-R*.3,H/2-R*.3,R*.1,W/2,H/2,R*1.05);gl.addColorStop(0,"#3a0f15");gl.addColorStop(1,"#120507");
    g.fillStyle=gl;g.beginPath();g.arc(W/2,H/2,R,0,7);g.fill();g.strokeStyle="#ff2e3a55";g.lineWidth=1.2;g.stroke();
    g.strokeStyle="#ff2e3a18";g.lineWidth=1;for(let lo=-180;lo<180;lo+=30){g.beginPath();let pen=false;for(let la=-90;la<=90;la+=5){const[x,y,z]=proj(la,lo);if(z>0){pen?g.lineTo(x,y):g.moveTo(x,y);pen=true}else pen=false}g.stroke()}
    for(let la=-60;la<=60;la+=30){g.beginPath();let pen=false;for(let lo=-180;lo<=180;lo+=5){const[x,y,z]=proj(la,lo);if(z>0){pen?g.lineTo(x,y):g.moveTo(x,y);pen=true}else pen=false}g.stroke()}
    for(const[la,lo]of LANDPTS){const[x,y,z]=proj(la,lo);if(z>0){g.fillStyle=`rgba(255,${120+z*60|0},${90+z*40|0},${.25+z*.6})`;g.fillRect(x-1.1,y-1.1,2.2,2.2)}}
    const home=proj(51.2,10.4);Globe.spots=[];
    for(const o of D.lage?.orte||[]){const[x,y,z]=proj(o.lat,o.lon);if(z<=0)continue;
      const r=4+Math.min(10,o.anzahl*1.5),hot=o.heiss>0,ph=(t/900+o.lat)%1;
      if(o.land!=="Deutschland"&&home[2]>0){g.strokeStyle=hot?"#ff2e3a88":"#ff7a4555";g.lineWidth=1.2;g.beginPath();g.moveTo(home[0],home[1]);
        const mx=(home[0]+x)/2,my=(home[1]+y)/2,dx=mx-W/2,dy=my-H/2,k=.35;g.quadraticCurveTo(mx+dx*k,my+dy*k,x,y);g.stroke()}
      if(!RM){g.strokeStyle=`rgba(255,46,58,${1-ph})`;g.lineWidth=2;g.beginPath();g.arc(x,y,r+ph*14,0,7);g.stroke()}
      g.fillStyle=hot?"#ff2e3a":"#ff9a5a";g.shadowColor=g.fillStyle;g.shadowBlur=14;g.beginPath();g.arc(x,y,r*.55,0,7);g.fill();g.shadowBlur=0;
      if(Globe.sel===o.land||o===D.lage.orte[0]){g.fillStyle="#fff";g.font="600 12px Chakra Petch,sans-serif";g.textAlign="center";g.fillText(o.land.toUpperCase(),x,y-r-8)}
      Globe.spots.push({o,x,y,r:r+8})}}
  function loop(t){if(!$("#t-lage").classList.contains("on")||document.hidden){Globe.run=false;return}
    const dt=Math.min(.05,(t-last)/1000||0);last=t;if(!Globe.drag&&!RM)Globe.rot+=dt*6;draw(t);requestAnimationFrame(loop)}
  return function(){if(!cv){cv=$("#globeCv");g=cv.getContext("2d");
      cv.addEventListener("pointerdown",e=>{Globe.drag={x:e.clientX,y:e.clientY,r:Globe.rot,tl:Globe.tilt,m:0};cv.setPointerCapture(e.pointerId)});
      cv.addEventListener("pointermove",e=>{const d=Globe.drag;if(!d)return;d.m=Math.max(d.m,Math.abs(e.clientX-d.x)+Math.abs(e.clientY-d.y));
        Globe.rot=d.r-(e.clientX-d.x)*.4;Globe.tilt=Math.max(-60,Math.min(70,d.tl+(e.clientY-d.y)*.3));if(RM)draw(0)});
      cv.addEventListener("pointerup",e=>{const d=Globe.drag;Globe.drag=null;if(d&&d.m<6){const r=cv.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;
        const s=Globe.spots.find(s=>Math.hypot(s.x-x,s.y-y)<s.r);if(s)pickLand(s.o.land)}});
      new ResizeObserver(()=>{if(resize()&&RM)draw(0)}).observe(cv.parentElement)}
    if(Globe.run||!$("#t-lage").classList.contains("on")||!resize())return;if(RM){draw(0);return}Globe.run=true;requestAnimationFrame(loop)}
})();
function pickLand(n){Globe.sel=n;const o=(D.lage?.orte||[]).find(x=>x.land===n);if(o)Globe.rot=o.lon;
  $$("#lands button").forEach(b=>b.classList.toggle("on",b.dataset.land===n));
  const list=o?o.meldungen:(D.lage?.ohne_land||[]);
  $("#news").innerHTML=`<h3 style="margin-top:14px">${esc(o?o.land:"Sonstige Meldungen")}</h3>`+list.map(m=>`<p><a href="${esc(m.url)}" target="_blank" rel="noopener">${esc(m.titel)}</a><br><span class="muted small">${esc(m.text||"")} · ${esc(m.quelle)}</span></p>`).join("")}
function renderLage(){const L=D.lage;
  if(!L){$("#lagebild").textContent="Agentin Ada meldet sich nach ihrer ersten Runde (alle 2 Stunden).";$("#mkt").innerHTML="";return}
  $("#lageInfo").textContent="Stand "+ago(L.updated);
  $("#lagebild").textContent=L.lagebild||(L.orte.length?`${L.orte.length} Länder in den Nachrichten. Am meisten los: ${L.orte.slice(0,3).map(o=>o.land).join(", ")}.`:"Gerade keine Meldungen geladen.");
  $("#lands").innerHTML=L.orte.map(o=>`<button class="chip" data-land="${esc(o.land)}">${o.heiss?"🔴":"🟠"} ${esc(o.land)} · ${o.anzahl}</button>`).join("")+(L.ohne_land?.length?`<button class="chip" data-land="">🌐 Sonstiges</button>`:"");
  $$("#lands button").forEach(b=>b.onclick=()=>pickLand(b.dataset.land));
  if(L.orte[0])pickLand(Globe.sel&&L.orte.some(o=>o.land===Globe.sel)?Globe.sel:L.orte[0].land);
  $("#mkt").innerHTML=(L.maerkte||[]).map(m=>`<div><span class="muted small">${esc(m.name)}</span><b>${m.einheit==="€"?eur(m.wert):m.wert.toLocaleString("de-DE",{maximumFractionDigits:4})}</b><span class="small ${m.pct>=0?"pos":"neg"}">${m.pct>=0?"▲ +":"▼ "}${m.pct.toLocaleString("de-DE")} %</span></div>`).join("")||`<p class="muted small">Keine Marktdaten.</p>`;
  const v=L.maerkte?.[0]?.verlauf;$("#btcSpark").innerHTML=v?.length>1?`<p class="muted small" style="margin:12px 0 0">Bitcoin, 7 Tage</p>`+spark(v.map((y,i)=>[i,y])):"";
  globeStart()}
