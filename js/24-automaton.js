"use strict";
/* ---------- Automaton: Jarvis' PayPal-Topf, Überlebens-Stufe, Kind-Bots ---------- */
const STUFE={normal:["🟢","Normal","volle KI, alle Bots"],sparsam:["🟡","Sparsam","kleineres KI-Modell"],kritisch:["🟠","Kritisch","nur noch Geld-Suche"],ruhe:["⚫","Ruhe","wartet auf Einnahmen"]};
function renderAutomaton(){const el=$("#automaton");if(!el)return;const A=D.auto;
  if(!A){el.innerHTML="";return}
  const [ic,name,info]=STUFE[A.modus]||STUFE.normal,v=A.vorschlag,kids=A.kinder||[],pct=Math.max(0,Math.min(100,A.topf/50*100));
  el.innerHTML=`<div class="panel"><div class="row" style="justify-content:space-between"><h3>🧬 Jarvis-Topf · PayPal</h3><span class="chip">${ic} ${name}</span></div>
   <div class="big">${eur(A.topf)}</div><span class="muted small">${esc(info)} · reicht ~${A.reichweite_tage||0} Tage · Server ${eur(A.kosten?.server_monat)}/Monat · ${A.updated?ago(A.updated):""}</span>
   <div class="bar" style="margin-top:8px"><i style="width:${pct}%"></i></div>
   <p class="small">Einnahmen 30 Tage: <b>${eur(A.einnahmen_30t)}</b> · gesamt ${eur(A.einnahmen_gesamt)}${A.paypal?.kontostand!=null?` · PayPal-Konto ${eur(A.paypal.kontostand)}`:""}</p>
   ${A.hinweis?`<p class="small muted">⚠️ ${esc(A.hinweis)}</p>`:""}
   ${v?`<div class="panel" id="klon"><b>Klonen? ${esc(v.name)} (${esc(v.rolle)}) · Budget ${eur(v.budget)}</b><p class="small">${esc(v.auftrag)}</p><p class="small muted">${esc(v.warum)}</p>
     <div class="row"><button class="btn" data-klon="ja">✅ Ja</button><button class="btn" data-klon="nein">❌ Nein</button></div></div>`:""}
   ${kids.length?`<h3 style="margin-top:14px">Kinder (${kids.filter(k=>k.status==="lebt").length} leben)</h3><table>${kids.slice(-8).reverse().map(k=>`<tr><td>${k.status==="lebt"?"👶":"💀"} ${esc(k.name)} <span class="muted small">${esc(k.id)} · ${esc(k.rolle)}</span><br><span class="small muted">${esc(k.schritte?.at(-1)?.text||k.auftrag)}</span></td><td class="r">${eur(k.einnahmen)}<br><span class="muted small">${eur(k.ausgegeben)} / ${eur(k.budget)}</span></td></tr>`).join("")}</table>`:""}
   ${(A.log||[]).length?`<details style="margin-top:10px"><summary class="small">Protokoll</summary>${A.log.slice(0,10).map(l=>`<p class="small">${esc(l.text)} <span class="muted">${ago(l.t)}</span></p>`).join("")}</details>`:""}
   <p class="muted small">Jarvis liest PayPal nur – er kann kein Geld senden oder ausgeben. Kinder entstehen nur mit deinem Ja.</p></div>`;
  $$("[data-klon]").forEach(b=>b.onclick=async()=>{const ja=b.dataset.klon==="ja";
    try{await gh("/actions/workflows/automaton.yml/dispatches",{ref:"main",inputs:{aktion:ja?"ja":"nein"}});$("#klon").innerHTML=`<b>${ja?"👶 Wird geklont …":"Abgelehnt."}</b> <span class="muted small">kommt in ein paar Minuten an</span>`;toast(ja?"🧬 Jarvis klont sich – Kind startet gleich.":"Klon abgelehnt.")}
    catch(e){toast("Ging nicht: "+e.message)}})}
