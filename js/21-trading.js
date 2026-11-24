"use strict";
/* ---------- Trading ---------- */
function spark(eq){if(!eq||eq.length<2)return"";const v=eq.map(e=>e[1]),mn=Math.min(...v),mx=Math.max(...v),w=600,h=90,
  p=v.map((y,i)=>`${(i/(v.length-1)*w).toFixed(1)},${(h-((y-mn)/((mx-mn)||1))*(h-8)-4).toFixed(1)}`).join(" ");
  return `<svg viewBox="0 0 ${w} ${h}" style="width:100%;height:90px;margin-top:10px" role="img" aria-label="Kontoverlauf"><polyline points="${p}" fill="none" stroke="var(--red)" stroke-width="2.5"/></svg>`}
function renderTrading(){
  const P=D.paper,A=D.agents;let h="";
  if(P){const g=P.gate||{},n=g.need||{wr:80,value:3500,trades:100},diff=P.value-P.start,open=Object.entries(P.open||{});
    h+=`<div class="panel"><h3>Trader Toni · Krypto (Kraken)</h3><div class="big">${eur(P.value)}</div>
     <span class="${diff>=0?"pos":"neg"}">${diff>=0?"+":""}${eur(diff)} seit Start</span> <span class="muted small">· aktualisiert ${ago(P.updated)}</span>
     ${spark(P.equity)}<p class="small muted">${esc(P.strategy)}</p>
     <h3 style="margin-top:14px">Weg zum Echtgeld</h3><div class="gate">
      <div><div class="row" style="justify-content:space-between"><span>Gewinn-Trades</span><span>${(g.wr||0).toFixed(0)} % von ${n.wr} %</span></div><div class="bar"><i style="width:${Math.min(100,(g.wr||0)/n.wr*100)}%"></i></div></div>
      <div><div class="row" style="justify-content:space-between"><span>Kontostand</span><span>${eur(P.value)} von ${eur(n.value)}</span></div><div class="bar"><i style="width:${Math.min(100,(P.value-P.start)/(n.value-P.start)*100)}%"></i></div></div>
      <div><div class="row" style="justify-content:space-between"><span>Trades</span><span>${g.trades||0} von ${n.trades}</span></div><div class="bar"><i style="width:${Math.min(100,(g.trades||0)/n.trades*100)}%"></i></div></div></div>
     <h3 style="margin-top:16px">Offen (${open.length})</h3>${open.length?`<table>${open.map(([k,o])=>`<tr><td>${esc(k)}</td><td class="r">${eur(o.cost)}</td><td class="r muted">${ago(o.t)}</td></tr>`).join("")}</table>`:`<p class="muted small">Toni wartet auf einen Kursrutsch zum Einsteigen.</p>`}
     ${(P.closed||[]).length?`<h3 style="margin-top:16px">Letzte Trades</h3><table>${P.closed.slice(-8).reverse().map(c=>`<tr><td>${esc(c.pair)}</td><td class="r ${c.pnl>=0?"pos":"neg"}">${c.pnl>=0?"+":""}${eur(c.pnl)}</td><td class="r muted">${esc(c.why)}</td></tr>`).join("")}</table>`:""}</div>`}
  if(A){const val=(A.equity?.at(-1)||[0,A.cash])[1],diff=val-A.start,cl=A.closed||[],wins=cl.filter(c=>c.pnl>0).length;
    h+=`<div class="panel"><h3>Meme-Makler Max · Solana-Memecoins</h3><div class="big">${eur(val)}</div>
     <span class="${diff>=0?"pos":"neg"}">${diff>=0?"+":""}${eur(diff)} seit Start</span> <span class="muted small">· ${cl.length} Trades, ${cl.length?Math.round(wins/cl.length*100):0} % Gewinner</span>
     ${spark(A.equity)}<table>${(A.activity||[]).slice(0,8).map(a=>`<tr><td>${esc(a.kind)} ${esc(a.sym)}</td><td class="r ${a.pnl>0?"pos":a.pnl<0?"neg":""}">${a.pnl!=null?(a.pnl>=0?"+":"")+eur(a.pnl):eur(a.eur)}</td><td class="r muted">${ago(a.t)}</td></tr>`).join("")}</table></div>`}
  h+=`<p class="muted small">Beide Bots handeln nur mit Spielgeld. Echtes Geld erst nach deinem ausdrücklichen Ja (≥ 80 % Gewinn-Trades und ≥ 3.500 €).</p>`;
  $("#trading").innerHTML=h;
}
